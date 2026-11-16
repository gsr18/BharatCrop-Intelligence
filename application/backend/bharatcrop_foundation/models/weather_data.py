from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

import pandas as pd

from bharatcrop_foundation.models.apy_data import QUALITY_FLAGS, YIELD_UNIT

WEATHER_METRICS: Final[dict[str, tuple[str, str]]] = {
    "tmin_mean_c": ("Annual average minimum temperature", "degC"),
    "tmin_min_c": ("Annual minimum temperature extreme", "degC"),
    "tmax_mean_c": ("Annual average maximum temperature", "degC"),
    "tmax_max_c": ("Annual maximum temperature extreme", "degC"),
    "precipitation_total_mm": ("Annual precipitation total", "mm/year"),
    "precipitation_mean_mm_day": ("Mean daily precipitation", "mm/day"),
    "precipitation_max_mm_day": ("Maximum daily precipitation", "mm/day"),
}
VALID_DAY_COLUMNS: Final[tuple[str, ...]] = (
    "tmin_valid_days",
    "tmax_valid_days",
    "precipitation_valid_days",
)
WEATHER_FLAGS: Final[tuple[str, ...]] = (
    "QC_Extreme_Annual_Min_Temperature",
    "QC_Extreme_Annual_Max_Temperature",
    "QC_High_Annual_Precipitation",
    "QC_Extreme_Daily_Precipitation",
    "QC_Long_District_Grid_Distance",
)
WEATHER_COLUMNS: Final[tuple[str, ...]] = (
    "apy_geography_id",
    "State",
    "District",
    "district_latitude",
    "district_longitude",
    "coordinate_source",
    "geography_confidence",
    "nearest_grid_latitude",
    "nearest_grid_longitude",
    "nearest_grid_elevation_m",
    "nearest_grid_distance_km",
    "latitude",
    "longitude",
    "calendar_year",
    *WEATHER_METRICS,
    *VALID_DAY_COLUMNS,
    *WEATHER_FLAGS,
)
REFERENCE_COLUMNS: Final[tuple[str, ...]] = (
    "State",
    "District",
    "weather_years",
    "tmin_mean_c_historical_median",
    "tmax_mean_c_historical_median",
    "precipitation_total_mm_historical_median",
    "tmin_mean_c_historical_p10",
    "tmax_mean_c_historical_p10",
    "precipitation_total_mm_historical_p10",
    "tmin_mean_c_historical_p90",
    "tmax_mean_c_historical_p90",
    "precipitation_total_mm_historical_p90",
    "weather_coverage_pct",
    "coverage_status",
)
INTEGRATION_COLUMNS: Final[tuple[str, ...]] = (
    "State",
    "District",
    "Crop",
    "Season",
    "Crop_Category",
    "Year",
    "Area",
    "Production",
    "Yield",
    *QUALITY_FLAGS,
    "apy_geography_id",
    "start_year",
    "weather_proxy_calendar_year",
    "tmin_mean_c",
    "tmin_min_c",
    "tmax_mean_c",
    "tmax_max_c",
    "precipitation_total_mm",
    "precipitation_mean_mm_day",
    "precipitation_max_mm_day",
    "tmin_valid_days",
    "tmax_valid_days",
    "precipitation_valid_days",
    "QC_Extreme_Annual_Min_Temperature",
    "QC_Extreme_Annual_Max_Temperature",
    "QC_High_Annual_Precipitation",
    "QC_Extreme_Daily_Precipitation",
    "QC_Long_District_Grid_Distance",
    "weather_proxy_available",
    "_merge",
    "weather_alignment_method",
    "weather_full_season_alignment_verified",
    "weather_available",
    "weather_match_status",
)

WEATHER_SOURCE: Final[str] = (
    "NASA POWER gridded meteorological estimates mapped to representative APY "
    "district geography identifiers; see the project weather acquisition audit."
)
WEATHER_TRANSFORMATIONS: Final[str] = (
    "Notebook 10 cleaning and QC, Notebook 11 preprocessing, and Notebook 14 "
    "district-year integration; annual summaries are calendar-year proxies."
)
WEATHER_LIMITATIONS: Final[tuple[str, ...]] = (
    "Values are representative-grid estimates, not district-wide station measurements.",
    "Grid-to-district distance and geography confidence affect representativeness.",
    "Annual calendar-year values are not aligned to crop seasons or growth stages.",
    "Descriptive associations do not demonstrate weather-caused yield changes.",
)
ANOMALY_METRICS: Final[tuple[str, ...]] = (
    "tmin_mean_c",
    "tmax_mean_c",
    "precipitation_total_mm",
)
AGGREGATE_COLUMNS: Final[tuple[str, ...]] = (
    "State",
    "District",
    "apy_geography_id",
    "calendar_year",
)


class WeatherDataError(Exception):
    """Raised when a configured research dataset is unavailable or invalid."""


@dataclass(frozen=True)
class WeatherReadiness:
    execution_available: bool
    availability: str
    quality_status: str
    evidence_quality: str
    production_approved: bool
    reason_codes: tuple[str, ...]
    limitations: tuple[str, ...]


class WeatherDataService:
    """Cached read-only access to the project's processed weather research."""

    def __init__(
        self,
        annual_path: Path,
        reference_path: Path,
        history_path: Path,
        unmatched_path: Path,
        integration_path: Path,
        integration_summary_path: Path,
        classifier_evaluation_path: Path,
        intelligence_metadata_path: Path,
    ) -> None:
        self.annual_path = annual_path
        self.reference_path = reference_path
        self.history_path = history_path
        self.unmatched_path = unmatched_path
        self.integration_path = integration_path
        self.integration_summary_path = integration_summary_path
        self.classifier_evaluation_path = classifier_evaluation_path
        self.intelligence_metadata_path = intelligence_metadata_path
        self._annual: pd.DataFrame | None = None
        self._reference: pd.DataFrame | None = None
        self._history: pd.DataFrame | None = None
        self._unmatched: pd.DataFrame | None = None
        self._integration: pd.DataFrame | None = None
        self._integration_summary: dict[str, Any] | None = None
        self._integration_provenance: dict[str, Any] | None = None
        self._metadata: dict[str, Any] | None = None
        self._classifier_evaluation: dict[str, Any] | None = None
        self._provenance: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def _load_weather(self) -> None:
        if self._annual is not None:
            return
        with self._lock:
            if self._annual is not None:
                return
            for path in (self.annual_path, self.reference_path, self.history_path):
                if not path.is_file():
                    raise WeatherDataError("A required processed weather dataset is unavailable.")
            try:
                annual = pd.read_csv(
                    self.annual_path,
                    usecols=list(WEATHER_COLUMNS),
                    low_memory=False,
                )
                reference = pd.read_csv(
                    self.reference_path,
                    usecols=list(REFERENCE_COLUMNS),
                    low_memory=False,
                )
                history = pd.read_csv(self.history_path, low_memory=False)
                unmatched = (
                    pd.read_csv(self.unmatched_path, low_memory=False)
                    if self.unmatched_path.is_file()
                    else pd.DataFrame()
                )
            except (OSError, ValueError, pd.errors.ParserError, UnicodeError) as error:
                raise WeatherDataError("A processed weather dataset failed to load.") from error

            if annual.empty or reference.empty:
                raise WeatherDataError("Processed weather datasets contain no records.")
            if annual.duplicated(["apy_geography_id", "calendar_year"]).any():
                raise WeatherDataError("Weather district-year keys are duplicated.")
            year_values = pd.to_numeric(annual["calendar_year"], errors="coerce")
            if year_values.isna().any() or not year_values.between(2013, 2024).all():
                raise WeatherDataError("Weather calendar years fall outside audited coverage.")
            annual["calendar_year"] = year_values.astype("int64")
            for column in (*WEATHER_METRICS, *VALID_DAY_COLUMNS, "nearest_grid_distance_km"):
                annual[column] = pd.to_numeric(annual[column], errors="coerce")
            for column in WEATHER_FLAGS:
                values = (
                    annual[column]
                    .astype("string")
                    .str.strip()
                    .str.casefold()
                    .map({"true": True, "false": False, "1": True, "0": False})
                )
                if values.isna().any():
                    raise WeatherDataError("Weather quality flags contain invalid values.")
                annual[column] = values.astype(bool)
            if annual[["apy_geography_id", "State", "District"]].isna().any(axis=None):
                raise WeatherDataError("Weather geography keys are incomplete.")
            if reference.duplicated(["State", "District"]).any():
                raise WeatherDataError("Weather reference keys are duplicated.")
            if not set(annual["calendar_year"].unique()).issubset(set(range(2013, 2025))):
                raise WeatherDataError("Weather year coverage is inconsistent.")

            digest = hashlib.sha256()
            try:
                with self.annual_path.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
            except OSError as error:
                raise WeatherDataError("Weather dataset provenance cannot be read.") from error
            self._annual = annual.sort_values(
                ["State", "District", "calendar_year"],
                kind="mergesort",
            )
            self._reference = reference
            self._history = history
            self._unmatched = unmatched
            self._provenance = {
                "dataset_name": self.annual_path.name,
                "dataset_source": WEATHER_SOURCE,
                "source_file": self.annual_path.name,
                "sha256": digest.hexdigest(),
                "record_count": int(len(annual)),
                "district_geography_count": int(annual["apy_geography_id"].nunique()),
                "year_start": int(annual["calendar_year"].min()),
                "year_end": int(annual["calendar_year"].max()),
                "weather_metrics": [
                    {"name": name, "label": spec[0], "unit": spec[1]}
                    for name, spec in WEATHER_METRICS.items()
                ],
                "transformation": WEATHER_TRANSFORMATIONS,
            }

    @property
    def annual(self) -> pd.DataFrame:
        self._load_weather()
        if self._annual is None:
            raise WeatherDataError("Processed weather data are unavailable.")
        return self._annual

    @property
    def reference(self) -> pd.DataFrame:
        self._load_weather()
        if self._reference is None:
            raise WeatherDataError("Weather reference data are unavailable.")
        return self._reference

    @property
    def provenance(self) -> dict[str, Any]:
        self._load_weather()
        if self._provenance is None:
            raise WeatherDataError("Weather provenance is unavailable.")
        return dict(self._provenance)

    @property
    def integration_frame(self) -> pd.DataFrame:
        """Return the shared cached APY-weather rows; callers must treat it as read-only."""
        return self._load_integration()

    @property
    def integration_provenance(self) -> dict[str, Any]:
        self._load_integration()
        if self._integration_provenance is None:
            raise WeatherDataError("APY-weather integration provenance is unavailable.")
        return dict(self._integration_provenance)

    @property
    def years(self) -> list[int]:
        return sorted(int(value) for value in self.annual["calendar_year"].unique())

    @property
    def locations(self) -> pd.DataFrame:
        self._load_weather()
        if self._reference is None:
            raise WeatherDataError("Weather reference data are unavailable.")
        location_cols = [
            "apy_geography_id",
            "State",
            "District",
            "district_latitude",
            "district_longitude",
            "coordinate_source",
            "geography_confidence",
            "nearest_grid_latitude",
            "nearest_grid_longitude",
            "nearest_grid_elevation_m",
            "nearest_grid_distance_km",
            "QC_Long_District_Grid_Distance",
        ]
        locations = self.annual[location_cols].drop_duplicates(
            ["State", "District"]
        )
        locations = self._reference.merge(
            locations,
            on=["State", "District"],
            how="left",
            validate="one_to_one",
        )
        if self._unmatched is not None and not self._unmatched.empty:
            unmatched_cols = [
                column
                for column in (
                    "State",
                    "District",
                    "apy_geography_id",
                    "geography_confidence",
                    "coordinate_source",
                    "is_synthetic",
                )
                if column in self._unmatched.columns
            ]
            unmatched = self._unmatched[unmatched_cols].drop_duplicates(
                ["State", "District"]
            )
            locations = locations.merge(
                unmatched,
                on=["State", "District"],
                how="left",
                suffixes=("", "_unmatched"),
                validate="one_to_one",
            )
            for column in ("apy_geography_id", "geography_confidence", "coordinate_source"):
                fallback = f"{column}_unmatched"
                if fallback in locations:
                    locations[column] = locations[column].fillna(locations[fallback])
                    locations.drop(columns=fallback, inplace=True)
        return locations

    def _filtered(
        self,
        *,
        state: str | None = None,
        district: str | None = None,
        year_start: int | None = None,
        year_end: int | None = None,
    ) -> pd.DataFrame:
        if district is not None and state is None:
            raise ValueError("State is required when filtering by district.")
        if year_start is not None and year_start not in self.years:
            raise ValueError("Start year is outside weather dataset coverage.")
        if year_end is not None and year_end not in self.years:
            raise ValueError("End year is outside weather dataset coverage.")
        if year_start is not None and year_end is not None and year_start > year_end:
            raise ValueError("Start year must not exceed end year.")
        frame = self.annual
        if state is not None:
            if state not in set(self.locations["State"]):
                raise ValueError("State is not supported by the weather reference.")
            selected_state = state
            frame = frame.loc[frame["State"].eq(selected_state)]
        if district is not None:
            if state is None:
                raise ValueError("State is required when filtering by district.")
            location_rows = self.locations.loc[
                self.locations["State"].eq(state)
                & self.locations["District"].eq(district)
            ]
            if location_rows.empty:
                raise ValueError("District is not supported for the selected state.")
            frame = frame.loc[frame["District"].eq(district)]
        if year_start is not None:
            frame = frame.loc[frame["calendar_year"].ge(year_start)]
        if year_end is not None:
            frame = frame.loc[frame["calendar_year"].le(year_end)]
        return frame

    def readiness(self) -> WeatherReadiness:
        try:
            frame = self.annual
        except WeatherDataError:
            return WeatherReadiness(
                False,
                "unavailable",
                "unavailable",
                "unavailable",
                False,
                ("processed_weather_dataset_unavailable",),
                WEATHER_LIMITATIONS,
            )
        if frame.empty:
            return WeatherReadiness(
                False,
                "unavailable",
                "unavailable",
                "unavailable",
                False,
                ("processed_weather_dataset_empty",),
                WEATHER_LIMITATIONS,
            )
        return WeatherReadiness(
            True,
            "available",
            "experimental",
            "district_year_grid_estimates_with_variable_coverage",
            False,
            ("historical_weather_dataset_available", "representative_grid_estimates"),
            WEATHER_LIMITATIONS,
        )

    def options(self, *, state: str | None = None) -> dict[str, Any]:
        locations = self.locations
        if state is not None:
            if state not in set(locations["State"]):
                raise ValueError("State is not supported by the weather reference.")
            locations = locations.loc[locations["State"].eq(state)]
        districts = sorted(str(value) for value in locations["District"].unique())
        states = sorted(str(value) for value in self.locations["State"].unique())
        districts_by_state = {
            str(state_value): sorted(
                str(value) for value in group["District"].unique()
            )
            for state_value, group in self.locations.groupby("State")
        }
        return {
            "years": self.years,
            "year_start": min(self.years),
            "year_end": max(self.years),
            "states": states,
            "districts": districts,
            "districts_by_state": districts_by_state,
            "selected_state": state,
            "weather_metrics": self.provenance["weather_metrics"],
            "dataset_provenance": self.provenance,
            "limitations": list(WEATHER_LIMITATIONS),
        }

    def overview(
        self,
        *,
        state: str | None = None,
        district: str | None = None,
        year: int | None = None,
    ) -> dict[str, Any]:
        frame = self._filtered(
            state=state,
            district=district,
            year_start=year,
            year_end=year,
        )
        available = frame.loc[frame[list(WEATHER_METRICS)].notna().any(axis=1)]
        valid_days = {
            column: {
                "valid_day_total": int(frame[column].sum()),
                "expected_day_total": int(
                    frame["calendar_year"].map(
                        lambda value: 366
                        if pd.Timestamp(year=int(value), month=12, day=31).is_leap_year
                        else 365
                    ).sum()
                ),
                "coverage_pct": (
                    float(
                        frame[column].sum()
                        / frame["calendar_year"]
                        .map(
                            lambda value: 366
                            if pd.Timestamp(year=int(value), month=12, day=31).is_leap_year
                            else 365
                        )
                        .sum()
                        * 100
                    )
                    if len(frame)
                    else None
                ),
            }
            for column in VALID_DAY_COLUMNS
        }
        missingness = {
            column: {
                "missing_count": int(frame[column].isna().sum()),
                "record_count": int(len(frame)),
                "missing_pct": (
                    float(frame[column].isna().mean() * 100) if len(frame) else None
                ),
            }
            for column in WEATHER_METRICS
        }
        flag_counts = {
            column: int(frame[column].sum())
            for column in WEATHER_FLAGS
        }
        return {
            "record_count": int(len(frame)),
            "weather_available_record_count": int(len(available)),
            "geography_count": int(frame["apy_geography_id"].nunique()),
            "state_count": int(frame["State"].nunique()),
            "district_count": int(frame[["State", "District"]].drop_duplicates().shape[0]),
            "years": sorted(int(value) for value in frame["calendar_year"].unique()),
            "calendar_year_semantics": "Calendar-year annual summaries",
            "valid_day_coverage": valid_days,
            "missingness": missingness,
            "quality_flag_counts": flag_counts,
            "geography_coverage": self.coverage_summary(state=state, district=district),
            "dataset_provenance": self.provenance,
            "limitations": list(WEATHER_LIMITATIONS),
        }

    def _metric_rows(
        self,
        *,
        metric: str,
        state: str | None,
        district: str | None,
        year_start: int | None,
        year_end: int | None,
    ) -> pd.DataFrame:
        if metric not in WEATHER_METRICS:
            raise ValueError("Weather metric is not supported.")
        return self._filtered(
            state=state,
            district=district,
            year_start=year_start,
            year_end=year_end,
        )

    def series(
        self,
        *,
        metric: str,
        state: str | None = None,
        district: str | None = None,
        year_start: int | None = None,
        year_end: int | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        frame = self._metric_rows(
            metric=metric,
            state=state,
            district=district,
            year_start=year_start,
            year_end=year_end,
        )
        name, unit = WEATHER_METRICS[metric]
        selected = frame[
            [
                "apy_geography_id",
                "State",
                "District",
                "calendar_year",
                metric,
                *VALID_DAY_COLUMNS,
                *WEATHER_FLAGS,
            ]
        ].copy()
        selected.rename(columns={metric: "value"}, inplace=True)
        total = len(selected)
        start = (page - 1) * page_size
        points = [
            {
                "year": int(row["calendar_year"]),
                "date_semantics": "Calendar year",
                "state": str(row["State"]),
                "district": str(row["District"]),
                "geography_id": str(row["apy_geography_id"]),
                "value": float(row["value"]) if pd.notna(row["value"]) else None,
                "unit": unit,
                "valid_days": {
                    column: int(row[column]) if pd.notna(row[column]) else None
                    for column in VALID_DAY_COLUMNS
                },
                "quality_flags": {
                    column: bool(row[column]) for column in WEATHER_FLAGS
                },
            }
            for row in selected.iloc[start : start + page_size].to_dict("records")
        ]
        return {
            "metric": metric,
            "label": name,
            "unit": unit,
            "date_semantics": "Calendar year; annual district representative-grid summary",
            "page": page,
            "page_size": page_size,
            "total": int(total),
            "points": points,
            "dataset_provenance": self.provenance,
            "limitations": list(WEATHER_LIMITATIONS),
        }

    def trends(
        self,
        *,
        metric: str,
        state: str | None = None,
        district: str | None = None,
        year_start: int | None = None,
        year_end: int | None = None,
    ) -> dict[str, Any]:
        frame = self._metric_rows(
            metric=metric,
            state=state,
            district=district,
            year_start=year_start,
            year_end=year_end,
        )
        name, unit = WEATHER_METRICS[metric]
        groups: dict[str, pd.DataFrame]
        if district is not None:
            groups = {f"{state} / {district}": frame}
            spatial_aggregation = "single district representative-grid series"
        elif state is not None:
            groups = {state: frame}
            spatial_aggregation = (
                "Year-wise distribution across available district representative-grid "
                "annual estimates for the selected state; not area weighted."
            )
        else:
            groups = {"India (covered district estimates)": frame}
            spatial_aggregation = (
                "Year-wise distribution across available district representative-grid "
                "annual estimates; not area weighted."
            )
        points: list[dict[str, Any]] = []
        for label, group in groups.items():
            yearly_values: list[dict[str, Any]] = []
            total_observations = 0
            for year, year_rows in group.groupby("calendar_year", sort=True):
                values = year_rows[metric].dropna()
                if values.empty:
                    continue
                mean = float(values.mean())
                median = float(values.median())
                p95 = float(values.quantile(0.95))
                maximum = float(values.max())
                yearly_values.append(
                    {
                        "year": int(str(year)),
                        "date_semantics": "Calendar year",
                        "value": (
                            float(values.iloc[0]) if district is not None else mean
                        ),
                        "unit": unit,
                        "mean": mean,
                        "median": median,
                        "p95": p95,
                        "maximum": maximum,
                        "observation_count": int(len(values)),
                    }
                )
                total_observations += len(values)
            points.append(
                {
                    "location": label,
                    "yearly_values": yearly_values,
                    "observation_count": total_observations,
                }
            )
        return {
            "metric": metric,
            "label": name,
            "unit": unit,
            "aggregation": spatial_aggregation,
            "trend_method": (
                "Notebook 12/13 year-wise district summaries: mean, median, 95th "
                "percentile, and maximum of available district-year values. The "
                "default plotted value is the annual mean; these descriptive annual "
                "patterns are not long-term climate trends."
            ),
            "series": points,
            "dataset_provenance": self.provenance,
            "limitations": list(WEATHER_LIMITATIONS),
        }

    def anomalies(
        self,
        *,
        metric: str | None = None,
        state: str | None = None,
        district: str | None = None,
        year_start: int | None = None,
        year_end: int | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        if metric is not None and metric not in ANOMALY_METRICS:
            raise ValueError(
                "Anomaly metric must be tmin_mean_c, tmax_mean_c, or "
                "precipitation_total_mm."
            )
        frame = self._filtered(
            state=state,
            district=district,
            year_start=year_start,
            year_end=year_end,
        ).copy()
        references = self.reference
        metric_names = [metric] if metric else list(ANOMALY_METRICS)
        frame = frame.merge(
            references[
                [
                    "State",
                    "District",
                    *[
                        col
                        for item in metric_names
                        for col in (
                            f"{item}_historical_p10",
                            f"{item}_historical_p90",
                        )
                    ],
                ]
            ],
            on=["State", "District"],
            how="left",
            validate="many_to_one",
        )
        start = (page - 1) * page_size
        records: list[dict[str, Any]] = []
        total = len(frame)
        for row in frame.iloc[start : start + page_size].to_dict("records"):
            statuses: dict[str, Any] = {}
            for item in metric_names:
                value = row[item]
                lower = row[f"{item}_historical_p10"]
                upper = row[f"{item}_historical_p90"]
                if pd.isna(value) or pd.isna(lower) or pd.isna(upper):
                    status = "Unavailable"
                elif value < lower:
                    status = "Below historical range"
                elif value > upper:
                    status = "Above historical range"
                else:
                    status = "Within historical range"
                statuses[item] = {
                    "value": float(value) if pd.notna(value) else None,
                    "historical_p10": float(lower) if pd.notna(lower) else None,
                    "historical_p90": float(upper) if pd.notna(upper) else None,
                    "status": status,
                    "unit": WEATHER_METRICS[item][1],
                }
            district_mean = float(
                self.annual.loc[
                    self.annual["apy_geography_id"].eq(row["apy_geography_id"]),
                    "tmax_mean_c",
                ].mean()
            )
            tmax_mean = row["tmax_mean_c"]
            records.append(
                {
                    "state": str(row["State"]),
                    "district": str(row["District"]),
                    "geography_id": str(row["apy_geography_id"]),
                    "calendar_year": int(row["calendar_year"]),
                    "historical_percentile_status": statuses,
                    "tmax_mean_same_period_deviation_c": (
                        float(tmax_mean - district_mean) if pd.notna(tmax_mean) else None
                    ),
                    "temperature_deviation_baseline": (
                        "District's own 2013-2024 mean tmax_mean_c, as in Notebook 13."
                    ),
                    "quality_flags": {
                        flag: bool(row[flag]) for flag in WEATHER_FLAGS
                    },
                }
            )
        return {
            "method": {
                "district_percentiles": (
                    "Notebook 19: district-specific historical 10th and 90th "
                    "percentiles over available 2013-2024 district-year observations; "
                    "strictly below p10 or above p90 is outside the historical range."
                ),
                "temperature_deviation": (
                    "Notebook 13: annual tmax_mean_c minus that APY geography "
                    "identifier's 2013-2024 mean; same-period descriptive baseline."
                ),
                "interpretation": (
                    "Descriptive historical departures only; not forecasts, verified "
                    "extreme-event declarations, or crop-risk warnings."
                ),
            },
            "page": page,
            "page_size": page_size,
            "total": int(total),
            "records": records,
            "dataset_provenance": self.provenance,
            "limitations": list(WEATHER_LIMITATIONS),
        }

    def coverage_summary(
        self,
        *,
        state: str | None = None,
        district: str | None = None,
    ) -> dict[str, Any]:
        if district is not None and state is None:
            raise ValueError("State is required when filtering by district.")
        locations = self.locations
        if state is not None:
            locations = locations.loc[locations["State"].eq(state)]
        if district is not None:
            selected_district = district
            locations = locations.loc[
                locations["District"].eq(selected_district)
            ]
        return {
            "reference_location_count": int(len(locations)),
            "locations_with_weather": int(locations["weather_coverage_pct"].gt(0).sum()),
            "locations_without_weather": int(locations["weather_coverage_pct"].eq(0).sum()),
            "district_year_observations": int(
                self._filtered(state=state, district=district).shape[0]
            ),
            "year_start": min(self.years),
            "year_end": max(self.years),
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
        locations = self.locations
        if state is not None:
            if state not in set(locations["State"]):
                raise ValueError("State is not supported by the weather reference.")
            locations = locations.loc[locations["State"].eq(state)]
        if district is not None:
            locations = locations.loc[locations["District"].eq(district)]
            if locations.empty:
                raise ValueError("District is not supported for the selected state.")
        total = len(locations)
        rows: list[dict[str, Any]] = []
        for row in locations.iloc[(page - 1) * page_size : page * page_size].to_dict(
            "records"
        ):
            geography_id = row.get("apy_geography_id")
            years = (
                self.annual.iloc[0:0]
                if pd.isna(geography_id)
                else self.annual.loc[
                    self.annual["apy_geography_id"].eq(geography_id)
                ]
            )
            row_flags = {
                flag: int(years[flag].sum()) for flag in WEATHER_FLAGS
            }
            grid_distance = row.get("nearest_grid_distance_km")
            confidence = row.get("geography_confidence")
            rows.append(
                {
                    "state": str(row["State"]),
                    "district": str(row["District"]),
                    "geography_id": row.get("apy_geography_id"),
                    "weather_year_count": (
                        int(row["weather_years"])
                        if pd.notna(row["weather_years"])
                        else 0
                    ),
                    "weather_coverage_pct": float(row["weather_coverage_pct"]),
                    "coverage_status": str(row["coverage_status"]),
                    "available_years": [
                        int(value) for value in years["calendar_year"].tolist()
                    ],
                    "valid_day_coverage": {
                        column: (
                            float(years[column].mean())
                            if len(years)
                            else None
                        )
                        for column in VALID_DAY_COLUMNS
                    },
                    "quality_flag_counts": row_flags,
                    "district_latitude": self._optional_float(row.get("district_latitude")),
                    "district_longitude": self._optional_float(row.get("district_longitude")),
                    "coordinate_source": row.get("coordinate_source"),
                    "geography_confidence": confidence,
                    "representative_grid_latitude": self._optional_float(
                        row.get("nearest_grid_latitude")
                    ),
                    "representative_grid_longitude": self._optional_float(
                        row.get("nearest_grid_longitude")
                    ),
                    "representative_grid_elevation_m": self._optional_float(
                        row.get("nearest_grid_elevation_m")
                    ),
                    "nearest_grid_distance_km": self._optional_float(grid_distance),
                    "mapping_quality": (
                        "unmapped"
                        if pd.isna(row.get("apy_geography_id"))
                        else "low"
                        if str(confidence).startswith("LOW")
                        else "provisional"
                        if str(confidence).startswith("PROVISIONAL")
                        else "recorded"
                    ),
                }
            )
        return {
            "page": page,
            "page_size": page_size,
            "total": int(total),
            "locations": rows,
            "coverage_summary": self.coverage_summary(state=state, district=district),
            "dataset_provenance": self.provenance,
            "limitations": list(WEATHER_LIMITATIONS),
        }

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        return float(value) if pd.notna(value) else None

    def crop_context(
        self,
        *,
        state: str,
        district: str,
        crop: str | None = None,
        season: str | None = None,
        year_start: int | None = None,
        year_end: int | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        frame = self._load_integration()
        if state not in set(self.locations["State"]):
            raise ValueError("State or district is not supported by the APY integration.")
        state_rows = frame.loc[frame["State"].eq(state)]
        if district not in set(state_rows["District"]):
            raise ValueError("District is not supported for the selected state.")
        if season is not None and season not in set(frame["Season"].dropna()):
            raise ValueError("Season is not present in the APY integration.")
        if year_start is not None and year_start not in self.years:
            raise ValueError("Start year is outside weather dataset coverage.")
        if year_end is not None and year_end not in self.years:
            raise ValueError("End year is outside weather dataset coverage.")
        if year_start is not None and year_end is not None and year_start > year_end:
            raise ValueError("Start year must not exceed end year.")
        selected = frame.loc[frame["State"].eq(state) & frame["District"].eq(district)]
        if crop is not None:
            selected = selected.loc[selected["Crop"].eq(crop)]
        if season is not None:
            selected = selected.loc[selected["Season"].eq(season)]
        if year_start is not None:
            selected = selected.loc[selected["start_year"].ge(year_start)]
        if year_end is not None:
            selected = selected.loc[selected["start_year"].le(year_end)]
        total = len(selected)
        if total == 0:
            raise ValueError("No APY crop-weather records match the selected filters.")
        points = [
            {
                "crop": str(row["Crop"]),
                "season": str(row["Season"]),
                "crop_category": str(row["Crop_Category"]),
                "agricultural_year": str(row["Year"]),
                "agricultural_year_start": int(row["start_year"]),
                "weather_proxy_calendar_year": (
                    int(row["weather_proxy_calendar_year"])
                    if pd.notna(row["weather_proxy_calendar_year"])
                    else None
                ),
                "area": self._optional_float(row["Area"]),
                "production": self._optional_float(row["Production"]),
                "yield": self._optional_float(row["Yield"]),
                "yield_unit": YIELD_UNIT,
                "weather_available": bool(row["weather_available"]),
                "weather_match_status": str(row["weather_match_status"]),
                "weather_alignment_method": str(row["weather_alignment_method"]),
                "full_season_alignment_verified": bool(
                    row["weather_full_season_alignment_verified"]
                ),
                "weather_values": {
                    column: self._optional_float(row[column])
                    for column in WEATHER_METRICS
                },
                "valid_days": {
                    column: int(row[column]) if pd.notna(row[column]) else None
                    for column in VALID_DAY_COLUMNS
                },
                "weather_quality_flags": {
                    column: bool(row[column]) if pd.notna(row[column]) else None
                    for column in WEATHER_FLAGS
                },
            }
            for row in selected.iloc[(page - 1) * page_size : page * page_size].to_dict(
                "records"
            )
        ]
        summary = self._integration_summary or {}
        return {
            "state": state,
            "district": district,
            "page": page,
            "page_size": page_size,
            "total": int(total),
            "matched_count": int(selected["weather_available"].sum()),
            "unmatched_count": int((~selected["weather_available"]).sum()),
            "points": points,
            "alignment_method": "STARTING_CALENDAR_YEAR_PROXY",
            "temporal_semantics": (
                "Weather for agricultural year YYYY-YY is joined to calendar year "
                "YYYY (the agricultural-year starting calendar year). This is an "
                "annual proxy, not verified crop-season or growth-stage exposure."
            ),
            "full_season_alignment_verified": False,
            "project_integration_totals": summary,
            "interpretation": (
                "Exploratory paired APY and annual weather records only. Associations "
                "do not demonstrate that weather caused observed yield changes."
            ),
            "crop_data_provenance": dict(self._integration_provenance or {}),
            "dataset_provenance": self.provenance,
            "limitations": list(WEATHER_LIMITATIONS),
        }

    def _load_integration(self) -> pd.DataFrame:
        if self._integration is not None:
            return self._integration
        with self._lock:
            if self._integration is not None:
                return self._integration
            if not self.integration_path.is_file():
                raise WeatherDataError("The APY-weather integration dataset is unavailable.")
            try:
                frame = pd.read_csv(
                    self.integration_path,
                    usecols=list(INTEGRATION_COLUMNS),
                    low_memory=False,
                )
            except (OSError, ValueError, pd.errors.ParserError, UnicodeError) as error:
                raise WeatherDataError(
                    "The APY-weather integration dataset failed to load."
                ) from error
            for column in (
                "Area",
                "Production",
                "Yield",
                "start_year",
                "weather_proxy_calendar_year",
                *WEATHER_METRICS,
                *VALID_DAY_COLUMNS,
            ):
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
            for column in (
                "weather_proxy_available",
                "weather_full_season_alignment_verified",
                "weather_available",
                *QUALITY_FLAGS,
                *WEATHER_FLAGS,
            ):
                values = (
                    frame[column]
                    .astype("string")
                    .str.strip()
                    .str.casefold()
                    .map({"true": True, "false": False, "1": True, "0": False})
                )
                if column in {
                    "weather_full_season_alignment_verified",
                    "weather_available",
                } and values.isna().any():
                    raise WeatherDataError(
                        "APY-weather integration availability flags are incomplete."
                    )
                frame[column] = values.astype("boolean")
            frame["start_year"] = frame["start_year"].astype("Int64")
            digest = hashlib.sha256()
            try:
                with self.integration_path.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
            except OSError as error:
                raise WeatherDataError(
                    "APY-weather integration provenance cannot be read."
                ) from error
            self._integration = frame
            self._integration_provenance = {
                "dataset_name": self.integration_path.name,
                "dataset_source": (
                    "Processed APY crop observations joined to representative-grid "
                    "calendar-year weather proxies."
                ),
                "source_file": self.integration_path.name,
                "sha256": digest.hexdigest(),
                "record_count": int(len(frame)),
                "alignment_method": "STARTING_CALENDAR_YEAR_PROXY",
            }
            if self.integration_summary_path.is_file():
                try:
                    summary = pd.read_csv(self.integration_summary_path)
                    self._integration_summary = (
                        {
                            str(key): value
                            for key, value in summary.iloc[0].to_dict().items()
                        }
                        if not summary.empty
                        else {}
                    )
                except (OSError, ValueError, pd.errors.ParserError) as error:
                    raise WeatherDataError(
                        "The APY-weather integration summary could not be read."
                    ) from error
            return frame

    def classifier_status(self) -> dict[str, Any]:
        if (
            self._classifier_evaluation is None
            and self.classifier_evaluation_path.is_file()
        ):
            try:
                raw = json.loads(self.classifier_evaluation_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise WeatherDataError("Classifier research metadata could not be read.") from error
            if isinstance(raw, dict):
                self._classifier_evaluation = raw
        evaluation = self._classifier_evaluation or {}
        if (
            self._metadata is None
            and self.intelligence_metadata_path.is_file()
        ):
            try:
                metadata = json.loads(
                    self.intelligence_metadata_path.read_text(encoding="utf-8")
                )
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise WeatherDataError(
                    "Weather intelligence metadata could not be read."
                ) from error
            if isinstance(metadata, dict):
                self._metadata = metadata
        metrics = evaluation.get("metrics")
        metric_names = metrics.keys() if isinstance(metrics, dict) else ()
        algorithms = [
            label
            for prefix, label in (
                ("logistic_", "Logistic regression"),
                ("random_forest_", "Random forest classifier"),
            )
            if any(str(key).startswith(prefix) for key in metric_names)
        ]
        train_years = evaluation.get("train_years")
        test_years = evaluation.get("test_years")
        evaluation_method = (
            "Chronological year holdout; training years "
            f"{train_years[0]}-{train_years[-1]}, test years "
            f"{test_years[0]}-{test_years[-1]}."
            if isinstance(train_years, list)
            and train_years
            and isinstance(test_years, list)
            and test_years
            else "Temporal holdout as documented in Notebook 19."
        )
        artifact_exists = False
        return {
            "task": evaluation.get("model_task", "Experimental low-yield classification"),
            "execution_available": False,
            "availability": "unavailable",
            "artifact_available": artifact_exists,
            "artifact_path": None,
            "status": "experimental_not_executable",
            "reason_code": (
                "classifier_artifact_not_saved"
                if not artifact_exists
                else "classifier_artifact_not_approved_for_loading"
            ),
            "target_definition": evaluation.get("target_definition"),
            "algorithms_evaluated": algorithms,
            "features_evaluated": [
                "State",
                "District",
                "Crop",
                "Season",
                "start_year",
                "tmin_mean_c",
                "tmax_mean_c",
                "precipitation_total_mm",
            ],
            "baseline_features": [
                "State",
                "District",
                "Crop",
                "Season",
                "start_year",
            ],
            "weather_feature_additions": [
                "tmin_mean_c",
                "tmax_mean_c",
                "precipitation_total_mm",
            ],
            "evaluation_method": evaluation_method,
            "training_years": train_years,
            "test_years": test_years,
            "train_rows": evaluation.get("train_rows"),
            "test_rows": evaluation.get("test_rows"),
            "recorded_experimental_metrics": evaluation.get("metrics"),
            "weather_added_predictive_value": evaluation.get(
                "weather_added_predictive_value"
            ),
            "deployment_status": evaluation.get("deployment_status", "NOT READY"),
            "production_approved": False,
            "limitations": evaluation.get("limitations", []),
            "notebook": "19_weather_intelligence.ipynb",
            "dataset_provenance": self.provenance,
        }

    @staticmethod
    def classifier_readiness() -> WeatherReadiness:
        return WeatherReadiness(
            False,
            "unavailable",
            "experimental",
            "recorded_experimental_holdout_metrics",
            False,
            ("classifier_artifact_not_saved", "deployment_status_not_ready"),
            (
                "Notebook 19 trained experimental models but saved no classifier artifact.",
                "No classifier inference is available; recorded evaluation metrics are not "
                "validated farmer risk estimates.",
                "The experiment found no weather-added predictive value.",
            ),
        )

    def integration_readiness(self) -> WeatherReadiness:
        if not self.integration_path.is_file() or not self.integration_summary_path.is_file():
            return WeatherReadiness(
                False,
                "unavailable",
                "unavailable",
                "unavailable",
                False,
                ("apy_weather_integration_unavailable",),
                WEATHER_LIMITATIONS,
            )
        try:
            if self._integration_summary is None:
                summary = pd.read_csv(self.integration_summary_path)
                self._integration_summary = (
                    {
                        str(key): value
                        for key, value in summary.iloc[0].to_dict().items()
                    }
                    if not summary.empty
                    else {}
                )
        except (OSError, ValueError, pd.errors.ParserError) as error:
            raise WeatherDataError(
                "The APY-weather integration summary could not be read."
            ) from error
        return WeatherReadiness(
            True,
            "available",
            "exploratory",
            "calendar_year_proxy_with_unmatched_records",
            False,
            (
                "apy_weather_proxy_dataset_available",
                "full_season_alignment_unverified",
                "associations_are_exploratory",
            ),
            WEATHER_LIMITATIONS,
        )


@lru_cache(maxsize=8)
def cached_weather_service(
    annual_path: Path,
    reference_path: Path,
    history_path: Path,
    unmatched_path: Path,
    integration_path: Path,
    integration_summary_path: Path,
    classifier_evaluation_path: Path,
    intelligence_metadata_path: Path,
) -> WeatherDataService:
    return WeatherDataService(
        annual_path,
        reference_path,
        history_path,
        unmatched_path,
        integration_path,
        integration_summary_path,
        classifier_evaluation_path,
        intelligence_metadata_path,
    )
