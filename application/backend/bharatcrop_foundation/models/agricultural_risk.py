from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from bharatcrop_foundation.models.apy_data import (
    DATASET_LIMITATIONS,
    DATASET_SOURCE,
    INDIVIDUAL_CROP_CATEGORY,
    QUALITY_FLAGS,
    YIELD_UNIT,
)
from bharatcrop_foundation.models.weather_data import (
    WEATHER_FLAGS,
    WEATHER_METRICS,
    WeatherDataError,
    WeatherDataService,
)

NOTEBOOK_SEASONS: Final[tuple[str, ...]] = (
    "Kharif",
    "Rabi",
    "Summer",
    "Whole Year",
    "Autumn",
    "Winter",
)
GROUP_COLUMNS: Final[tuple[str, ...]] = ("State", "District", "Crop", "Season")
RISK_COLUMNS: Final[tuple[str, ...]] = (
    "State",
    "District",
    "Crop",
    "Season",
    "Crop_Category",
    "Year",
    "start_year",
    "Area",
    "Production",
    "Yield",
    "apy_geography_id",
    "weather_proxy_calendar_year",
    "weather_alignment_method",
    "weather_full_season_alignment_verified",
    "weather_available",
    "weather_match_status",
    *WEATHER_METRICS,
    *WEATHER_FLAGS,
    "QC_AreaZero-ProductionPositive",
    "QC_AreaPositive-ProductionZero",
    "QC_NegativeMeasurements",
    "QC_PositiveYieldWithoutPositiveAreaProduction",
)
ANOMALY_LIMITATIONS: Final[tuple[str, ...]] = (
    "Notebook 20 indicators are exploratory historical comparisons, not calibrated "
    "future-risk probabilities, crop-failure predictions, or official warnings.",
    "Notebook 20 uses up to three prior positive-yield observations and requires at "
    "least two; gaps between agricultural years are not imputed.",
    "MAD-based standardized deviations are not defined by Notebook 20 and are not "
    "calculated.",
    "Extreme yield deviations can reflect source errors, unit changes, or real "
    "observations and require review.",
    "Annual weather is a starting-calendar-year proxy with unverified crop-season "
    "alignment; weather does not alter the yield-based indicator.",
    "Missing weather is unavailable evidence, not evidence of high or low risk.",
)


class AgriculturalRiskDataError(Exception):
    """Raised when APY or Notebook 20 risk research cannot support the request."""


@dataclass(frozen=True)
class AgriculturalRiskReadiness:
    execution_available: bool
    availability: str
    quality_status: str
    evidence_quality: str
    production_approved: bool
    reason_codes: tuple[str, ...]
    limitations: tuple[str, ...]


class AgriculturalRiskService:
    """Read-only implementation of Notebook 20 historical indicators and analytics."""

    def __init__(
        self,
        weather_service: WeatherDataService,
        research_metadata_path: Path,
    ) -> None:
        self.weather_service = weather_service
        self.research_metadata_path = research_metadata_path
        self._prepared: pd.DataFrame | None = None
        self._metadata: dict[str, Any] | None = None
        self._provenance: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def _load(self) -> None:
        if self._prepared is not None:
            return
        with self._lock:
            if self._prepared is not None:
                return
            try:
                source = self.weather_service.integration_frame
            except WeatherDataError as error:
                raise AgriculturalRiskDataError(
                    "The processed APY-weather source is unavailable."
                ) from error
            if not set(RISK_COLUMNS).issubset(source.columns):
                raise AgriculturalRiskDataError(
                    "The APY-weather source does not satisfy Notebook 20's schema."
                )
            if not self.research_metadata_path.is_file():
                raise AgriculturalRiskDataError(
                    "Notebook 20 agricultural-risk metadata is unavailable."
                )
            try:
                metadata_bytes = self.research_metadata_path.read_bytes()
                metadata = json.loads(metadata_bytes.decode("utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise AgriculturalRiskDataError(
                    "Notebook 20 agricultural-risk metadata could not be read."
                ) from error
            if not isinstance(metadata, dict) or not isinstance(
                metadata.get("risk_definition"), dict
            ):
                raise AgriculturalRiskDataError(
                    "Notebook 20 agricultural-risk metadata is malformed."
                )
            source_dataset = metadata.get("source_dataset")
            if isinstance(source_dataset, str):
                metadata["source_dataset"] = Path(source_dataset).name
            frame = source.loc[:, list(RISK_COLUMNS)].copy()
            keys = list(GROUP_COLUMNS)
            for column in keys:
                frame[column] = frame[column].astype("string").str.strip()
            frame["start_year"] = pd.to_numeric(frame["start_year"], errors="coerce")
            frame["Yield"] = pd.to_numeric(frame["Yield"], errors="coerce")
            frame["Area"] = pd.to_numeric(frame["Area"], errors="coerce")
            frame["Production"] = pd.to_numeric(frame["Production"], errors="coerce")
            valid = (
                frame["Crop_Category"].eq(INDIVIDUAL_CROP_CATEGORY)
                & frame["Season"].isin(NOTEBOOK_SEASONS)
                & frame["start_year"].notna()
                & frame["Yield"].notna()
                & np.isfinite(frame["Yield"])
                & frame["Yield"].gt(0)
                & frame[keys].notna().all(axis=1)
            )
            prepared = frame.loc[valid].copy()
            if prepared.empty:
                raise AgriculturalRiskDataError(
                    "No valid individual-crop observations remain."
                )
            prepared["start_year"] = prepared["start_year"].astype("int64")
            prepared.sort_values(
                [*GROUP_COLUMNS, "start_year"],
                inplace=True,
                kind="mergesort",
            )
            if prepared.duplicated([*GROUP_COLUMNS, "start_year"]).any():
                raise AgriculturalRiskDataError(
                    "Notebook 20 crop-district-season-year keys are duplicated."
                )
            groups = prepared.groupby(list(GROUP_COLUMNS), sort=False)["Yield"]
            prepared["historical_median_yield"] = groups.transform(
                lambda values: values.shift(1)
                .rolling(window=3, min_periods=2)
                .median()
            )
            prepared["historical_observation_count"] = groups.transform(
                lambda values: values.shift(1)
                .rolling(window=3, min_periods=2)
                .count()
            )
            prepared["prior_valid_observation_count"] = groups.transform(
                lambda values: values.shift(1)
                .rolling(window=3, min_periods=0)
                .count()
            )
            prepared["yield_to_baseline_ratio"] = (
                prepared["Yield"] / prepared["historical_median_yield"]
            )
            prepared["yield_vs_historical_pct"] = (
                (prepared["Yield"] - prepared["historical_median_yield"])
                / prepared["historical_median_yield"]
                * 100
            )
            ratio = prepared["yield_to_baseline_ratio"]
            prepared["extreme_yield_deviation_flag"] = (
                (ratio < 0.1) | (ratio > 5)
            ).fillna(False)
            prepared["yield_risk_indicator"] = np.select(
                [
                    prepared["historical_median_yield"].isna(),
                    (ratio < 0.1) | (ratio > 5),
                    ratio < 0.70,
                    ratio < 0.85,
                    ratio <= 1.15,
                    ratio <= 5,
                ],
                [
                    "Insufficient History",
                    "Extreme Deviation - Review Data",
                    "High Concern",
                    "Moderate Concern",
                    "Within Historical Range",
                    "Above Historical Range",
                ],
                default="Unclassified",
            )
            digest = hashlib.sha256(metadata_bytes).hexdigest()
            source_provenance = self.weather_service.integration_provenance
            self._prepared = prepared
            self._metadata = metadata
            self._provenance = {
                "dataset": source_provenance,
                "apy_source_description": DATASET_SOURCE,
                "apy_source_limitations": list(DATASET_LIMITATIONS),
                "research_notebook": "20_agricultural_risk_intelligence.ipynb",
                "research_metadata_file": self.research_metadata_path.name,
                "research_metadata_sha256": digest,
                "yield_unit": YIELD_UNIT,
                "prepared_rows": int(len(prepared)),
                "observations_with_notebook_baseline": int(
                    prepared["historical_median_yield"].notna().sum()
                ),
                "year_start": int(prepared["start_year"].min()),
                "year_end": int(prepared["start_year"].max()),
            }

    @property
    def prepared(self) -> pd.DataFrame:
        self._load()
        if self._prepared is None:
            raise AgriculturalRiskDataError("Agricultural risk data are unavailable.")
        return self._prepared

    @property
    def provenance(self) -> dict[str, Any]:
        self._load()
        if self._provenance is None:
            raise AgriculturalRiskDataError("Agricultural risk provenance is unavailable.")
        return dict(self._provenance)

    @property
    def metadata(self) -> dict[str, Any]:
        self._load()
        if self._metadata is None:
            raise AgriculturalRiskDataError("Notebook 20 metadata are unavailable.")
        return dict(self._metadata)

    @property
    def years(self) -> list[int]:
        return sorted(int(year) for year in self.prepared["start_year"].unique())

    def readiness(self) -> AgriculturalRiskReadiness:
        try:
            self._load()
        except AgriculturalRiskDataError:
            return AgriculturalRiskReadiness(
                False,
                "unavailable",
                "unavailable",
                "unavailable",
                False,
                ("apy_or_notebook_20_data_unavailable",),
                ANOMALY_LIMITATIONS,
            )
        return AgriculturalRiskReadiness(
            True,
            "available",
            "exploratory",
            "historical_evidence_varies_by_crop_location_season",
            False,
            (
                "notebook_20_historical_indicators_available",
                "notebook_20_is_exploratory_not_validated_for_warnings",
                "no_composite_risk_formula_defined",
            ),
            ANOMALY_LIMITATIONS,
        )

    def options(
        self,
        *,
        state: str | None = None,
    ) -> dict[str, Any]:
        frame = self.prepared
        if state is not None:
            if state not in set(frame["State"]):
                raise ValueError("State is not supported by the risk dataset.")
            frame = frame.loc[frame["State"].eq(state)]
        districts_by_state = {
            str(state_value): sorted(
                str(value) for value in group["District"].unique()
            )
            for state_value, group in self.prepared.groupby("State")
        }
        return {
            "states": sorted(str(value) for value in self.prepared["State"].unique()),
            "districts": sorted(str(value) for value in frame["District"].unique()),
            "districts_by_state": districts_by_state,
            "crops": sorted(str(value) for value in frame["Crop"].unique()),
            "seasons": sorted(str(value) for value in frame["Season"].unique()),
            "years": self.years,
            "year_start": min(self.years),
            "year_end": max(self.years),
            "selected_state": state,
            "dataset_provenance": self.provenance,
            "methodology": self._methodology_summary(),
            "limitations": list(ANOMALY_LIMITATIONS),
        }

    def _methodology_summary(self) -> dict[str, Any]:
        return {
            "notebook": "20_agricultural_risk_intelligence.ipynb",
            "individual_crop_category": INDIVIDUAL_CROP_CATEGORY,
            "eligible_seasons": list(NOTEBOOK_SEASONS),
            "yield_validity": "Finite, non-missing, strictly positive Yield.",
            "baseline": (
                "Median of up to the three preceding valid observations for the same "
                "state, district, crop, and season; at least two prior observations "
                "are required. The current observation and all future observations "
                "are excluded."
            ),
            "risk_indicator_definitions": self.metadata["risk_definition"],
            "mad_standardized_deviation": "Not defined or calculated by Notebook 20.",
            "composite_score": "Not defined by Notebook 20.",
            "production_approved": False,
        }

    def _filter(
        self,
        *,
        state: str | None = None,
        district: str | None = None,
        crop: str | None = None,
        season: str | None = None,
        year_start: int | None = None,
        year_end: int | None = None,
    ) -> pd.DataFrame:
        if district is not None and state is None:
            raise ValueError("State is required when filtering by district.")
        for value, label, column in (
            (state, "State", "State"),
            (crop, "Crop", "Crop"),
            (season, "Season", "Season"),
        ):
            if value is not None and value not in set(self.prepared[column]):
                raise ValueError(f"{label} is not supported by the risk dataset.")
        if season is not None and season not in NOTEBOOK_SEASONS:
            raise ValueError("Season is not included in Notebook 20's analysis.")
        if year_start is not None and year_start not in self.years:
            raise ValueError("Start agricultural year is outside dataset coverage.")
        if year_end is not None and year_end not in self.years:
            raise ValueError("End agricultural year is outside dataset coverage.")
        if year_start is not None and year_end is not None and year_start > year_end:
            raise ValueError("Start agricultural year must not exceed end year.")
        frame = self.prepared
        if state is not None:
            frame = frame.loc[frame["State"].eq(state)]
        if district is not None:
            if district not in set(frame["District"]):
                raise ValueError("District is not supported for the selected state.")
            frame = frame.loc[frame["District"].eq(district)]
        if crop is not None:
            frame = frame.loc[frame["Crop"].eq(crop)]
        if season is not None:
            frame = frame.loc[frame["Season"].eq(season)]
        if year_start is not None:
            frame = frame.loc[frame["start_year"].ge(year_start)]
        if year_end is not None:
            frame = frame.loc[frame["start_year"].le(year_end)]
        return frame

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        return float(value) if pd.notna(value) and np.isfinite(value) else None

    def overview(self) -> dict[str, Any]:
        frame = self.prepared
        baseline = frame.loc[frame["historical_median_yield"].notna()]
        groups = baseline.groupby(list(GROUP_COLUMNS), sort=False)
        return {
            "prepared_observation_count": int(len(frame)),
            "observations_with_historical_baseline": int(len(baseline)),
            "observations_without_sufficient_history": int(len(frame) - len(baseline)),
            "district_crop_season_group_count": int(groups.ngroups),
            "crop_count": int(frame["Crop"].nunique()),
            "state_count": int(frame["State"].nunique()),
            "district_count": int(frame[["State", "District"]].drop_duplicates().shape[0]),
            "year_start": min(self.years),
            "year_end": max(self.years),
            "indicator_counts": {
                str(key): int(value)
                for key, value in baseline["yield_risk_indicator"]
                .value_counts()
                .items()
            },
            "weather_context": {
                "available_observations": int(
                    baseline["weather_available"].fillna(False).sum()
                ),
                "unavailable_observations": int(
                    len(baseline) - baseline["weather_available"].fillna(False).sum()
                ),
                "alignment_method": "STARTING_CALENDAR_YEAR_PROXY",
                "full_season_alignment_verified": False,
                "weather_changes_yield_indicator": False,
            },
            "research_metadata": self.metadata,
            "dataset_provenance": self.provenance,
            "limitations": list(ANOMALY_LIMITATIONS),
        }

    def anomalies(
        self,
        *,
        state: str,
        district: str,
        crop: str,
        season: str,
        year_start: int | None = None,
        year_end: int | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        selected = self._filter(
            state=state,
            district=district,
            crop=crop,
            season=season,
            year_start=year_start,
            year_end=year_end,
        )
        total = len(selected)
        records: list[dict[str, Any]] = []
        grouped = self.prepared.groupby(list(GROUP_COLUMNS), sort=False)
        page_rows = selected.iloc[(page - 1) * page_size : page * page_size]
        for row in page_rows.to_dict("records"):
            key = (row["State"], row["District"], row["Crop"], row["Season"])
            prior = grouped.get_group(key)
            prior = prior.loc[prior["start_year"].lt(row["start_year"])].tail(3)
            baseline = self._optional_float(row["historical_median_yield"])
            ratio = self._optional_float(row["yield_to_baseline_ratio"])
            direction = (
                "unavailable"
                if ratio is None
                else "below_baseline"
                if ratio < 1
                else "above_baseline"
                if ratio > 1
                else "equal_to_baseline"
            )
            records.append(
                {
                    "state": str(row["State"]),
                    "district": str(row["District"]),
                    "crop": str(row["Crop"]),
                    "season": str(row["Season"]),
                    "agricultural_year": str(row["Year"]),
                    "year_start": int(row["start_year"]),
                    "yield_value": float(row["Yield"]),
                    "yield_unit": YIELD_UNIT,
                    "baseline_available": baseline is not None,
                    "historical_median_yield": baseline,
                    "historical_observation_count": (
                        int(row["prior_valid_observation_count"])
                    ),
                    "baseline_observations": [
                        {
                            "year_start": int(item["start_year"]),
                            "agricultural_year": str(item["Year"]),
                            "yield_value": float(item["Yield"]),
                        }
                        for item in prior.to_dict("records")
                    ],
                    "yield_difference_from_baseline": (
                        float(row["Yield"]) - baseline if baseline is not None else None
                    ),
                    "yield_vs_historical_pct": self._optional_float(
                        row["yield_vs_historical_pct"]
                    ),
                    "yield_to_baseline_ratio": ratio,
                    "anomaly_direction": direction,
                    "risk_indicator": str(row["yield_risk_indicator"]),
                    "extreme_deviation_review": bool(
                        row["extreme_yield_deviation_flag"]
                    ),
                    "standardized_deviation": None,
                    "standardized_deviation_status": (
                        "not_calculated_not_defined_in_notebook_20"
                    ),
                    "source_quality_flags": {
                        flag: bool(row[flag]) if pd.notna(row[flag]) else None
                        for flag in QUALITY_FLAGS
                    },
                }
            )
        return {
            "state": state,
            "district": district,
            "crop": crop,
            "season": season,
            "page": page,
            "page_size": page_size,
            "total": int(total),
            "records": records,
            "methodology": self._methodology_summary(),
            "dataset_provenance": self.provenance,
            "limitations": list(ANOMALY_LIMITATIONS),
        }

    def instability(
        self,
        *,
        state: str,
        district: str,
        crop: str,
        season: str,
        year_start: int | None = None,
        year_end: int | None = None,
    ) -> dict[str, Any]:
        frame = self._filter(
            state=state,
            district=district,
            crop=crop,
            season=season,
            year_start=year_start,
            year_end=year_end,
        )
        yields = frame["Yield"].astype(float)
        count = len(yields)
        mean = float(yields.mean()) if count else None
        standard_deviation = float(yields.std(ddof=1)) if count >= 2 else None
        return {
            "state": state,
            "district": district,
            "crop": crop,
            "season": season,
            "window_start_year": int(frame["start_year"].min()) if count else None,
            "window_end_year": int(frame["start_year"].max()) if count else None,
            "valid_observation_count": int(count),
            "observed_year_count": int(frame["start_year"].nunique()),
            "source_quality_flagged_observation_count": int(
                frame[list(QUALITY_FLAGS)].fillna(False).any(axis=1).sum()
            ),
            "years": [
                {
                    "year_start": int(row["start_year"]),
                    "agricultural_year": str(row["Year"]),
                    "yield_value": float(row["Yield"]),
                    "yield_unit": YIELD_UNIT,
                    "source_quality_flags": {
                        flag: bool(row[flag]) if pd.notna(row[flag]) else None
                        for flag in QUALITY_FLAGS
                    },
                }
                for row in frame.to_dict("records")
            ],
            "mean_yield": mean,
            "median_yield": float(yields.median()) if count else None,
            "sample_standard_deviation": standard_deviation,
            "coefficient_of_variation_pct": (
                standard_deviation / mean * 100
                if standard_deviation is not None and mean is not None and mean != 0
                else None
            ),
            "robust_variability": None,
            "robust_variability_status": "not_defined_in_notebook_20",
            "trend_slope": None,
            "trend_status": "not_defined_in_notebook_20",
            "calculation_method": (
                "Descriptive statistics over valid positive-yield observations in "
                "the requested window. Standard deviation is sample standard "
                "deviation (ddof=1); CV is sample standard deviation divided by "
                "mean times 100. These variability calculations are not a Notebook "
                "20 risk score."
            ),
            "dataset_provenance": self.provenance,
            "limitations": list(ANOMALY_LIMITATIONS),
        }

    def indicators(
        self,
        *,
        state: str,
        district: str,
        crop: str,
        season: str,
        year_start: int | None = None,
        year_end: int | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        anomalies = self.anomalies(
            state=state,
            district=district,
            crop=crop,
            season=season,
            year_start=year_start,
            year_end=year_end,
            page=page,
            page_size=page_size,
        )
        source = self._filter(
            state=state,
            district=district,
            crop=crop,
            season=season,
            year_start=year_start,
            year_end=year_end,
        ).iloc[(page - 1) * page_size : page * page_size]
        integration_provenance = self.weather_service.integration_provenance
        try:
            locations = self.weather_service.locations
            location_rows = locations.loc[
                locations["State"].eq(state) & locations["District"].eq(district)
            ]
            weather_provenance = self.weather_service.provenance
        except WeatherDataError:
            location_rows = pd.DataFrame()
            weather_provenance = {
                **integration_provenance,
                "weather_annual_dataset_status": "unavailable",
            }
        location = location_rows.iloc[0].to_dict() if not location_rows.empty else {}
        augmented = []
        for record, row in zip(anomalies["records"], source.to_dict("records"), strict=True):
            weather_available = bool(row["weather_available"])
            augmented.append(
                {
                    **record,
                    "weather_context": {
                        "available": weather_available,
                        "calendar_year": (
                            int(row["weather_proxy_calendar_year"])
                            if pd.notna(row["weather_proxy_calendar_year"])
                            else None
                        ),
                        "alignment_method": str(row["weather_alignment_method"]),
                        "full_season_alignment_verified": bool(
                            row["weather_full_season_alignment_verified"]
                        ),
                        "temporal_semantics": (
                            "Calendar-year weather for the agricultural year's "
                            "starting calendar year; not verified crop-stage exposure."
                        ),
                        "weather_values": {
                            metric: self._optional_float(row[metric])
                            if weather_available
                            else None
                            for metric in WEATHER_METRICS
                        },
                        "quality_flags": {
                            flag: bool(row[flag])
                            if pd.notna(row[flag])
                            else None
                            for flag in WEATHER_FLAGS
                        },
                        "weather_coverage_pct": self._optional_float(
                            location.get("weather_coverage_pct")
                        ),
                        "nearest_grid_distance_km": self._optional_float(
                            location.get("nearest_grid_distance_km")
                        ),
                        "mapping_quality": (
                            "unmapped"
                            if pd.isna(location.get("apy_geography_id"))
                            else "low"
                            if str(location.get("geography_confidence")).startswith("LOW")
                            else "recorded"
                        ),
                        "dataset_provenance": weather_provenance,
                        "apy_weather_integration_provenance": integration_provenance,
                    },
                    "data_quality": {
                        "these_flags_do_not_change_notebook_20_eligibility": True,
                    },
                }
            )
        history_group = self._filter(
            state=state,
            district=district,
            crop=crop,
            season=season,
            year_start=year_start,
            year_end=year_end,
        )
        baseline_rows = history_group.loc[
            history_group["historical_median_yield"].notna()
        ]
        high_concern = baseline_rows["yield_risk_indicator"].eq("High Concern")
        moderate_concern = baseline_rows["yield_risk_indicator"].eq(
            "Moderate Concern"
        )
        high_years = sorted(
            int(year)
            for year in baseline_rows.loc[high_concern, "start_year"].unique()
        )
        observation_count = len(baseline_rows)
        evidence_status = (
            "Insufficient History"
            if observation_count < 3
            else "Limited History"
            if observation_count < 5
            else "Historical Pattern Available"
        )
        persistence = (
            "Repeated in 3+ Years"
            if len(high_years) >= 3
            else "Repeated in 2 Years"
            if len(high_years) == 2
            else "Observed in 1 Year"
            if len(high_years) == 1
            else "No High-Concern Years"
        )
        return {
            **anomalies,
            "records": augmented,
            "historical_pattern_summary": {
                "window_start_year": (
                    int(baseline_rows["start_year"].min())
                    if observation_count
                    else None
                ),
                "window_end_year": (
                    int(baseline_rows["start_year"].max())
                    if observation_count
                    else None
                ),
                "observation_count": int(observation_count),
                "high_concern_count": int(high_concern.sum()),
                "moderate_concern_count": int(moderate_concern.sum()),
                "extreme_deviation_count": int(
                    baseline_rows["extreme_yield_deviation_flag"].sum()
                ),
                "high_concern_pct": (
                    float(high_concern.sum() / observation_count * 100)
                    if observation_count
                    else None
                ),
                "moderate_concern_pct": (
                    float(moderate_concern.sum() / observation_count * 100)
                    if observation_count
                    else None
                ),
                "high_concern_years": high_years,
                "persistence_indicator": persistence,
                "evidence_status": evidence_status,
                "definition": (
                    "Persistence counts distinct agricultural years classified High "
                    "Concern. Evidence status follows Notebook 20: fewer than 3 "
                    "baseline observations is Insufficient History; fewer than 5 is "
                    "Limited History."
                ),
            },
            "interpretation": (
                "Yield indicators and weather/data-quality evidence are shown as "
                "separate fields. Weather is not used to calculate the yield indicator."
            ),
        }

    def diversification(
        self,
        *,
        state: str,
        district: str,
        season: str,
        year_start: int,
    ) -> dict[str, Any]:
        if season not in self.options()["seasons"]:
            raise ValueError("Season is not included in Notebook 20's analysis.")
        if year_start not in self.years:
            raise ValueError("Agricultural year is outside dataset coverage.")
        source = self.weather_service.integration_frame
        state_rows = source.loc[
            source["Crop_Category"].eq(INDIVIDUAL_CROP_CATEGORY)
            & source["State"].eq(state)
        ]
        if state_rows.empty:
            raise ValueError("State is not supported by the APY source.")
        group = state_rows.loc[
            state_rows["District"].eq(district)
            & state_rows["Season"].eq(season)
            & state_rows["start_year"].eq(year_start)
        ].copy()
        if group.empty:
            raise ValueError("No individual-crop area records match this comparison group.")
        area = pd.to_numeric(group["Area"], errors="coerce")
        positive = area.notna() & np.isfinite(area) & area.gt(0)
        eligible = group.loc[positive].copy()
        eligible["_area"] = area.loc[positive].astype(float)
        grouped = (
            eligible.groupby("Crop", as_index=False, sort=True)["_area"]
            .sum()
            .sort_values(["_area", "Crop"], ascending=[False, True])
        )
        total_area = float(grouped["_area"].sum())
        crops: list[dict[str, Any]] = []
        shares: list[float] = []
        if total_area > 0:
            for row in grouped.to_dict("records"):
                share = float(row["_area"]) / total_area
                shares.append(share)
                crops.append(
                    {
                        "crop": str(row["Crop"]),
                        "area": float(row["_area"]),
                        "area_unit": "ha",
                        "share": share,
                        "share_pct": share * 100,
                    }
                )
        return {
            "state": state,
            "district": district,
            "season": season,
            "year_start": year_start,
            "agricultural_year": str(group["Year"].iloc[0]),
            "crop_category": INDIVIDUAL_CROP_CATEGORY,
            "source_record_count": int(len(group)),
            "source_quality_flagged_record_count": int(
                group[list(QUALITY_FLAGS)].fillna(False).any(axis=1).sum()
            ),
            "positive_area_crop_count": int(len(crops)),
            "positive_area_record_count": int(positive.sum()),
            "excluded_missing_zero_or_negative_area_record_count": int(
                len(group) - int(positive.sum())
            ),
            "total_comparable_area": total_area if crops else None,
            "area_unit": "ha",
            "crop_area_shares": crops,
            "herfindahl_hirschman_index": (
                float(sum(share * share for share in shares)) if shares else None
            ),
            "hhi_formula": "Sum of squared crop area shares (share fractions, 0-1 scale).",
            "methodology_source": (
                "The area-share and HHI calculation is the requested descriptive "
                "analysis; Notebook 20 does not define a diversification indicator."
            ),
            "interpretation": (
                "HHI describes concentration within this individual-crop area group; "
                "it is not a resilience measure or a risk classification."
            ),
            "dataset_provenance": self.provenance,
            "limitations": [
                "Aggregate categories and Total seasons are excluded.",
                "Missing, zero, negative, and non-finite area values do not enter the "
                "share denominator and are counted separately.",
                "Area is reported in hectares; no unit conversion is applied.",
                "A concentration statistic alone does not establish agricultural "
                "resilience or risk.",
            ],
        }

    def benchmarking(
        self,
        *,
        state: str,
        crop: str,
        season: str,
        year_start: int,
        through_year_start: int | None = None,
    ) -> dict[str, Any]:
        through_year = through_year_start if through_year_start is not None else year_start
        if through_year < year_start:
            raise ValueError("Through-year must be greater than or equal to benchmark year.")
        self._filter(
            state=state,
            crop=crop,
            season=season,
            year_start=year_start,
            year_end=through_year,
        )
        prepared = self.prepared
        current = prepared.loc[
            prepared["State"].eq(state)
            & prepared["Crop"].eq(crop)
            & prepared["Season"].eq(season)
            & prepared["start_year"].eq(year_start)
        ]
        if current.empty:
            raise ValueError("No comparable district yields are available for this year.")
        rows: list[dict[str, Any]] = []
        for district, district_rows in current.groupby("District", sort=True):
            history = prepared.loc[
                prepared["State"].eq(state)
                & prepared["District"].eq(district)
                & prepared["Crop"].eq(crop)
                & prepared["Season"].eq(season)
                & prepared["start_year"].le(through_year)
            ]
            values = history["Yield"].astype(float)
            count = len(values)
            deviation = float(values.std(ddof=1)) if count >= 2 else None
            mean = float(values.mean()) if count else None
            current_row = district_rows.iloc[0]
            rows.append(
                {
                    "district": str(district),
                    "benchmark_year": int(year_start),
                    "agricultural_year": str(current_row["Year"]),
                    "current_year_yield": float(current_row["Yield"]),
                    "yield_unit": YIELD_UNIT,
                    "historical_window_start": int(history["start_year"].min()),
                    "historical_window_end": int(history["start_year"].max()),
                    "valid_historical_observation_count": int(count),
                    "quality_flagged_historical_observation_count": int(
                        history[list(QUALITY_FLAGS)].fillna(False).any(axis=1).sum()
                    ),
                    "historical_mean_yield": mean,
                    "historical_median_yield": float(values.median()),
                    "sample_standard_deviation": deviation,
                    "coefficient_of_variation_pct": (
                        deviation / mean * 100
                        if deviation is not None and mean is not None and mean != 0
                        else None
                    ),
                    "historical_years": [
                        int(value) for value in history["start_year"].tolist()
                    ],
                    "coverage_pct_of_window": (
                        count / (through_year - min(self.years) + 1) * 100
                    ),
                }
            )
        return {
            "state": state,
            "crop": crop,
            "season": season,
            "benchmark_year_start": year_start,
            "through_year_start": through_year,
            "comparison_group": (
                "Same state, individual crop, named season, agricultural year, "
                "APY source, and kg/ha yield unit."
            ),
            "district_count": len(rows),
            "districts": rows,
            "districts_ranked": False,
            "historical_calculation": (
                "Descriptive yield statistics use valid positive-yield observations "
                "from each district through the selected year. Cross-district current "
                "yields are same-agricultural-year comparisons; no total-production "
                "ranking is performed."
            ),
            "dataset_provenance": self.provenance,
            "limitations": [
                "This endpoint compares districts only within the selected state and "
                "same crop-season-agricultural-year group.",
                "The descriptive benchmark statistics are not a Notebook 20 risk score.",
                "Unequal historical observation coverage is reported per district.",
                "No causal or future-yield interpretation is supported.",
            ],
        }

    def coverage(
        self,
        *,
        state: str | None = None,
        district: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        if district is not None and state is None:
            raise ValueError("State is required when filtering by district.")
        source = self.weather_service.integration_frame
        source = source.loc[
            source["Crop_Category"].eq(INDIVIDUAL_CROP_CATEGORY)
            & source["Season"].isin(NOTEBOOK_SEASONS)
        ]
        if state is not None:
            if state not in set(self.prepared["State"]):
                raise ValueError("State is not supported by the risk dataset.")
            source = source.loc[source["State"].eq(state)]
        if district is not None:
            source = source.loc[source["District"].eq(district)]
            if source.empty:
                raise ValueError("District is not supported for the selected state.")
        source = source.copy()
        source["_yield"] = pd.to_numeric(source["Yield"], errors="coerce")
        source["_area"] = pd.to_numeric(source["Area"], errors="coerce")
        source["_yield_valid"] = (
            source["_yield"].notna()
            & np.isfinite(source["_yield"])
            & source["_yield"].gt(0)
        )
        source["_area_valid"] = (
            source["_area"].notna()
            & np.isfinite(source["_area"])
            & source["_area"].gt(0)
        )
        grouped = source.groupby(["State", "District"], sort=True, dropna=False)
        output = grouped.agg(
            individual_crop_records=("Crop", "size"),
            valid_positive_yield_records=("_yield_valid", "sum"),
            positive_area_records=("_area_valid", "sum"),
            matched_weather_records=("weather_available", "sum"),
        ).reset_index()
        output["weather_unavailable_records"] = (
            output["individual_crop_records"] - output["matched_weather_records"]
        )
        total = len(output)
        locations = [
            {
                "state": str(row["State"]),
                "district": str(row["District"]),
                "individual_crop_records": int(row["individual_crop_records"]),
                "valid_positive_yield_records": int(row["valid_positive_yield_records"]),
                "positive_area_records": int(row["positive_area_records"]),
                "matched_weather_records": int(row["matched_weather_records"]),
                "weather_unavailable_records": int(row["weather_unavailable_records"]),
            }
            for row in output.iloc[(page - 1) * page_size : page * page_size].to_dict(
                "records"
            )
        ]
        return {
            "page": page,
            "page_size": page_size,
            "total_locations": int(total),
            "locations": locations,
            "year_start": min(self.years),
            "year_end": max(self.years),
            "dataset_provenance": self.provenance,
            "limitations": list(ANOMALY_LIMITATIONS),
        }


@lru_cache(maxsize=8)
def cached_agricultural_risk_service(
    weather_service: WeatherDataService,
    research_metadata_path: Path,
) -> AgriculturalRiskService:
    return AgriculturalRiskService(weather_service, research_metadata_path)
