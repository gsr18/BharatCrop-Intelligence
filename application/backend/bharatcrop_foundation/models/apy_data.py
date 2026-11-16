from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from bharatcrop_foundation.models.yield_prediction import (
    ModelArtifactError,
    ModelNotReadyError,
    YieldFeatures,
    YieldPredictionService,
)

NAMED_SEASONS: Final[tuple[str, ...]] = ("Kharif", "Rabi", "Summer")
INDIVIDUAL_CROP_CATEGORY: Final[str] = "Individual Crop Candidate"
YIELD_UNIT: Final[str] = "kg/ha"
QUALITY_FLAGS: Final[tuple[str, ...]] = (
    "QC_AreaZero-ProductionPositive",
    "QC_AreaPositive-ProductionZero",
    "QC_NegativeMeasurements",
    "QC_PositiveYieldWithoutPositiveAreaProduction",
)
REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    "State",
    "District",
    "Crop",
    "Season",
    "Crop_Category",
    "Year",
    "Area",
    "Production",
    "Yield",
    "start_year",
    *QUALITY_FLAGS,
)

DATASET_NAME: Final[str] = "apy_weather_integrated_exploratory.csv"
DATASET_SOURCE: Final[str] = (
    "Historical district-level APY Food Grains, recorded by the project audit "
    "manifest as UPAg / Department of Agriculture and Farmers Welfare, integrated "
    "for exploratory analysis in Notebook 18."
)
DATASET_LIMITATIONS: Final[tuple[str, ...]] = (
    "Historical APY yields describe recorded outcomes, not expected future yields.",
    "Historical yield rankings are not planting recommendations or guarantees.",
    "Soil suitability, irrigation, costs, profitability, and market returns are not assessed.",
    "Weather features are excluded because crop-season alignment is not verified.",
    "Evidence coverage varies by crop, district, season, and agricultural year.",
    "The APY source remains DISCOVERED in the project registry; official source "
    "verification and integration checks remain open.",
)


class APYDataError(Exception):
    """Raised when the configured APY source cannot support reliable analysis."""


@dataclass(frozen=True)
class APYReadiness:
    execution_available: bool
    availability: str
    quality_status: str
    evidence_quality: str
    production_approved: bool
    reason_codes: tuple[str, ...]
    limitations: tuple[str, ...]
    comparison_group_count: int


class APYDataService:
    """Read-only, cached access to the validated APY evidence used in Notebook 18."""

    def __init__(
        self,
        dataset_path: Path,
        yield_service: YieldPredictionService | None = None,
    ) -> None:
        self.dataset_path = dataset_path
        self.yield_service = yield_service
        self._frame: pd.DataFrame | None = None
        self._all_individual: pd.DataFrame | None = None
        self._valid: pd.DataFrame | None = None
        self._provenance: dict[str, object] | None = None
        self._lock = threading.Lock()

    def _load(self) -> None:
        if self._frame is not None:
            return
        with self._lock:
            if self._frame is not None:
                return
            if not self.dataset_path.is_file():
                raise APYDataError("The configured APY dataset is unavailable.")
            try:
                frame = pd.read_csv(
                    self.dataset_path,
                    usecols=list(REQUIRED_COLUMNS),
                    low_memory=False,
                )
            except (OSError, ValueError, pd.errors.ParserError, UnicodeError) as error:
                raise APYDataError("The APY dataset could not be read.") from error

            if frame.empty:
                raise APYDataError("The APY dataset contains no records.")
            try:
                year_from_label = pd.to_numeric(
                    frame["Year"].astype("string").str.extract(r"^(\d{4})", expand=False),
                    errors="coerce",
                )
                start_year = pd.to_numeric(frame["start_year"], errors="coerce")
                if year_from_label.isna().any() or start_year.isna().any():
                    raise ValueError("Agricultural year fields are incomplete.")
                if not year_from_label.astype("int64").equals(start_year.astype("int64")):
                    raise ValueError("Agricultural year fields are inconsistent.")

                normalized_flags: dict[str, pd.Series] = {}
                for column in QUALITY_FLAGS:
                    flag = (
                        frame[column]
                        .astype("string")
                        .str.strip()
                        .str.casefold()
                        .map({"true": True, "false": False, "1": True, "0": False})
                    )
                    if flag.isna().any():
                        raise ValueError("Quality flag values are incomplete.")
                    normalized_flags[column] = flag.astype(bool)

                numeric = frame[["Area", "Production", "Yield"]].apply(
                    pd.to_numeric,
                    errors="coerce",
                )
                finite_numeric = np.isfinite(numeric).all(axis=1)
                individual_mask = frame["Crop_Category"].eq(INDIVIDUAL_CROP_CATEGORY)
                individual = frame.loc[individual_mask].copy()
                individual["_year_start"] = year_from_label.loc[individual_mask].astype("int64")
                key_frame = individual[
                    ["State", "District", "Crop", "Season", "Year"]
                ]
                if key_frame.isna().any(axis=None) or key_frame.duplicated().any():
                    raise ValueError("Individual-crop APY keys are incomplete or duplicated.")

                flags_frame = pd.DataFrame(normalized_flags, index=frame.index)
                valid_mask = (
                    individual_mask
                    & frame["Season"].isin(NAMED_SEASONS)
                    & frame[["State", "District", "Crop"]].notna().all(axis=1)
                    & finite_numeric
                    & numeric["Area"].gt(0)
                    & numeric["Production"].gt(0)
                    & numeric["Yield"].gt(0)
                    & ~flags_frame.any(axis=1)
                )
                valid = frame.loc[valid_mask].copy()
                valid["_year_start"] = year_from_label.loc[valid_mask].astype("int64")
                valid["_area"] = numeric.loc[valid_mask, "Area"].astype(float)
                valid["_production"] = numeric.loc[valid_mask, "Production"].astype(float)
                valid["_yield"] = numeric.loc[valid_mask, "Yield"].astype(float)
                valid.sort_values(
                    ["State", "District", "Season", "Crop", "_year_start"],
                    inplace=True,
                    kind="mergesort",
                )
                if valid.empty:
                    raise ValueError("No quality-controlled individual-crop records remain.")
            except (KeyError, TypeError, ValueError) as error:
                raise APYDataError(
                    "The APY dataset failed its documented quality checks."
                ) from error

            digest = hashlib.sha256()
            try:
                with self.dataset_path.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
            except OSError as error:
                raise APYDataError("The APY dataset provenance could not be read.") from error

            self._frame = frame
            self._all_individual = individual
            self._valid = valid
            self._provenance = {
                "dataset_name": DATASET_NAME,
                "dataset_source": DATASET_SOURCE,
                "source_file": self.dataset_path.name,
                "sha256": digest.hexdigest(),
                "record_count": int(len(frame)),
                "valid_record_count": int(len(valid)),
                "year_start": int(valid["_year_start"].min()),
                "year_end": int(valid["_year_start"].max()),
                "yield_unit": YIELD_UNIT,
            }

    @property
    def valid_frame(self) -> pd.DataFrame:
        self._load()
        if self._valid is None:
            raise APYDataError("The APY dataset is unavailable.")
        return self._valid

    @property
    def provenance(self) -> dict[str, object]:
        self._load()
        if self._provenance is None:
            raise APYDataError("The APY dataset provenance is unavailable.")
        return dict(self._provenance)

    @property
    def years(self) -> list[int]:
        frame = self.valid_frame
        return sorted(int(value) for value in frame["_year_start"].unique())

    def readiness(self) -> APYReadiness:
        try:
            frame = self.valid_frame
        except APYDataError:
            return APYReadiness(
                execution_available=False,
                availability="unavailable",
                quality_status="unavailable",
                evidence_quality="unavailable",
                production_approved=False,
                reason_codes=("apy_dataset_unavailable_or_invalid",),
                limitations=DATASET_LIMITATIONS,
                comparison_group_count=0,
            )
        comparison_groups = frame.groupby(
            ["State", "District", "Season", "_year_start"],
            sort=False,
        )["Crop"].nunique()
        comparison_group_count = int(comparison_groups.ge(2).sum())
        if comparison_group_count == 0:
            return APYReadiness(
                execution_available=False,
                availability="unavailable",
                quality_status="unavailable",
                evidence_quality="insufficient",
                production_approved=False,
                reason_codes=("no_multi_crop_comparison_groups",),
                limitations=DATASET_LIMITATIONS,
                comparison_group_count=0,
            )
        if self.yield_service is None or not self.yield_service.readiness().execution_available:
            return APYReadiness(
                execution_available=False,
                availability="unavailable",
                quality_status="unavailable",
                evidence_quality="insufficient",
                production_approved=False,
                reason_codes=("yield_ranking_model_unavailable",),
                limitations=DATASET_LIMITATIONS,
                comparison_group_count=comparison_group_count,
            )
        return APYReadiness(
            execution_available=True,
            availability="available",
            quality_status="experimental",
            evidence_quality="varies_by_comparison_group",
            production_approved=False,
            reason_codes=(
                "historical_comparisons_available",
                "evidence_coverage_varies_by_group",
                "production_approval_not_granted",
            ),
            limitations=DATASET_LIMITATIONS,
            comparison_group_count=comparison_group_count,
        )

    def options(
        self,
        *,
        state: str | None = None,
        district: str | None = None,
        season: str | None = None,
        year_start: int | None = None,
    ) -> dict[str, Any]:
        frame = self.valid_frame
        subset = frame
        if district is not None and state is None:
            raise ValueError("State is required when filtering by district.")
        if state is not None:
            if state not in set(frame["State"]):
                raise ValueError("State is not supported by the APY dataset.")
            subset = subset.loc[subset["State"].eq(state)]
        if district is not None:
            if district not in set(subset["District"]):
                raise ValueError("District is not supported for the selected state.")
            subset = subset.loc[subset["District"].eq(district)]
        if season is not None:
            self.validate_season(season)
            subset = subset.loc[subset["Season"].eq(season)]
        if year_start is not None:
            self.validate_year(year_start)
            subset = subset.loc[subset["_year_start"].eq(year_start)]
        if subset.empty:
            raise ValueError("No APY evidence supports the selected filters.")
        districts = sorted(str(value) for value in subset["District"].unique())
        states = sorted(str(value) for value in subset["State"].unique())
        crops = sorted(str(value) for value in subset["Crop"].unique())
        seasons = sorted(str(value) for value in subset["Season"].unique())
        return {
            "crops": crops,
            "states": states,
            "districts": districts,
            "seasons": seasons,
            "agricultural_years": self.years,
            "selected_state": state,
            "selected_district": district,
            "selected_season": season,
            "data_provenance": self.provenance,
            "limitations": list(DATASET_LIMITATIONS),
        }

    @staticmethod
    def validate_season(season: str) -> None:
        if season not in NAMED_SEASONS:
            raise ValueError("Season must be Kharif, Rabi, or Summer.")

    def validate_year(self, year_start: int) -> None:
        if year_start not in self.years:
            raise ValueError("Agricultural year is not supported by the APY dataset.")

    def validate_location(self, state: str, district: str) -> None:
        frame = self.valid_frame
        if state not in set(frame["State"]):
            raise ValueError("State is not supported by the APY dataset.")
        if district not in set(frame.loc[frame["State"].eq(state), "District"]):
            raise ValueError("District is not supported for the selected state.")

    def resolve_location(
        self,
        district: str,
        state: str | None = None,
    ) -> tuple[str, str] | None:
        frame = self.valid_frame
        district_key = district.strip().casefold()
        if state is not None:
            state_key = state.strip().casefold()
            candidate_states = [
                str(value)
                for value in frame["State"].unique()
                if str(value).strip().casefold() == state_key
            ]
        else:
            candidate_states = sorted(str(value) for value in frame["State"].unique())
        for candidate_state in candidate_states:
            districts = frame.loc[frame["State"].eq(candidate_state), "District"].tolist()
            for value in districts:
                if str(value).strip().casefold() == district_key:
                    return candidate_state, str(value)
        return None

    def _context(
        self,
        state: str,
        district: str,
        season: str,
        through_year: int,
    ) -> pd.DataFrame:
        self.validate_location(state, district)
        self.validate_season(season)
        self.validate_year(through_year)
        frame = self.valid_frame
        return frame.loc[
            frame["State"].eq(state)
            & frame["District"].eq(district)
            & frame["Season"].eq(season)
            & frame["_year_start"].le(through_year)
        ]

    def _statistics(
        self,
        rows: pd.DataFrame,
        *,
        crop: str,
        through_year: int,
    ) -> dict[str, Any]:
        crop_rows = rows.loc[rows["Crop"].eq(crop)].sort_values("_year_start")
        window_start = max(self.years[0], through_year - 4)
        recent = crop_rows.loc[crop_rows["_year_start"].ge(window_start)]
        years = [int(value) for value in crop_rows["_year_start"].tolist()]
        recent_years = [int(value) for value in recent["_year_start"].tolist()]
        yields = crop_rows["_yield"].to_numpy(dtype=float)
        recent_yields = recent["_yield"].to_numpy(dtype=float)
        trend: float | None = None
        if len(crop_rows) >= 2:
            x_values = crop_rows["_year_start"].to_numpy(dtype=float)
            centered_x = x_values - x_values.mean()
            denominator = float(np.dot(centered_x, centered_x))
            if denominator > 0:
                centered_y = yields - yields.mean()
                trend = float(np.dot(centered_x, centered_y) / denominator)
        variability: float | None = None
        coefficient_of_variation: float | None = None
        if len(recent_yields) >= 2:
            variability = float(np.std(recent_yields, ddof=1))
            recent_mean = float(np.mean(recent_yields))
            coefficient_of_variation = (
                variability / recent_mean if recent_mean > 0 else None
            )
        window_year_count = through_year - window_start + 1
        recent_year_count = len(recent_years)
        if recent_year_count == 0:
            evidence_quality = "insufficient"
        elif recent_year_count == 1:
            evidence_quality = "limited"
        elif recent_year_count <= 3:
            evidence_quality = "moderate"
        else:
            evidence_quality = "strong"
        return {
            "crop": crop,
            "historical_median_yield": float(np.median(yields)) if len(yields) else None,
            "historical_mean_yield": float(np.mean(yields)) if len(yields) else None,
            "recent_median_yield": (
                float(np.median(recent_yields)) if len(recent_yields) else None
            ),
            "recent_window_year_start": window_start,
            "recent_window_year_end": through_year,
            "yield_standard_deviation": variability,
            "coefficient_of_variation": coefficient_of_variation,
            "historical_trend_yield_per_year": trend,
            "valid_observation_count": int(len(crop_rows)),
            "valid_year_count": int(len(years)),
            "latest_observation_year": int(max(years)) if years else None,
            "valid_years": years,
            "recent_valid_year_count": recent_year_count,
            "recent_year_coverage": (
                recent_year_count / window_year_count if window_year_count else 0.0
            ),
            "evidence_quality": evidence_quality,
            "unit": YIELD_UNIT,
        }

    def comparison(
        self,
        *,
        state: str,
        district: str,
        season: str,
        through_year: int,
    ) -> list[dict[str, Any]]:
        rows = self._context(state, district, season, through_year)
        crops = sorted(str(value) for value in rows["Crop"].unique())
        return [
            self._statistics(rows, crop=crop, through_year=through_year)
            for crop in crops
        ]

    def comparison_group_coverage(
        self,
        *,
        state: str,
        district: str,
        season: str,
        through_year: int,
    ) -> list[dict[str, Any]]:
        rows = self._context(state, district, season, through_year)
        coverage = (
            rows.groupby(["_year_start", "Year"], sort=True)
            .agg(
                valid_observation_count=("_yield", "size"),
                candidate_count=("Crop", "nunique"),
            )
            .reset_index()
        )
        return [
            {
                "year_start": int(row["_year_start"]),
                "year_label": str(row["Year"]),
                "valid_observation_count": int(row["valid_observation_count"]),
                "candidate_count": int(row["candidate_count"]),
                "comparable": int(row["candidate_count"]) >= 2,
            }
            for row in coverage.to_dict("records")
        ]

    def trends(
        self,
        *,
        state: str,
        district: str,
        season: str,
        crop: str,
        through_year: int,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        rows = self._context(state, district, season, through_year)
        if crop not in set(self.valid_frame["Crop"]):
            raise ValueError("Crop is not supported by the APY dataset.")
        crop_rows = rows.loc[rows["Crop"].eq(crop)]
        summary = self._statistics(rows, crop=crop, through_year=through_year)
        observations = [
            {
                "year_start": int(row["_year_start"]),
                "year_label": str(row["Year"]),
                "area": float(row["_area"]),
                "production": float(row["_production"]),
                "yield_value": float(row["_yield"]),
                "unit": YIELD_UNIT,
            }
            for row in crop_rows[
                ["_year_start", "Year", "_area", "_production", "_yield"]
            ].to_dict("records")
        ]
        return summary, observations

    def evidence(
        self,
        *,
        state: str,
        district: str,
        season: str,
        crop: str,
        through_year: int,
    ) -> dict[str, Any]:
        summary, observations = self.trends(
            state=state,
            district=district,
            season=season,
            crop=crop,
            through_year=through_year,
        )
        self._load()
        if self._all_individual is None:
            raise APYDataError("The APY dataset is unavailable.")
        source = self._all_individual
        source_rows = source.loc[
            source["State"].eq(state)
            & source["District"].eq(district)
            & source["Season"].eq(season)
            & source["Crop"].eq(crop)
            & source["_year_start"].le(through_year)
        ]
        return {
            "statistics": summary,
            "source_observation_count": int(len(source_rows)),
            "valid_observation_count": int(summary["valid_observation_count"]),
            "excluded_observation_count": int(
                len(source_rows) - int(summary["valid_observation_count"])
            ),
            "observations": observations,
            "data_provenance": self.provenance,
            "limitations": list(DATASET_LIMITATIONS),
        }


    def rank(
        self,
        *,
        state: str,
        district: str,
        season: str,
        top_n: int = 5,
        ranking_basis: str = "recent_median",
    ) -> dict[str, Any]:
        if ranking_basis not in {"recent_median", "historical_median"}:
            raise ValueError("Ranking basis must be recent_median or historical_median.")
        candidate_limit = max(1, min(int(top_n), 5))
        if self.yield_service is None:
            raise APYDataError("The crop ranking model is unavailable.")
        model_readiness = self.yield_service.readiness()
        if not model_readiness.execution_available:
            raise APYDataError("The crop ranking model is unavailable.")
        self.validate_location(state, district)
        self.validate_season(season)
        frame = self.valid_frame
        context = frame.loc[
            frame["State"].eq(state)
            & frame["District"].eq(district)
            & frame["Season"].eq(season)
        ]
        if context.empty:
            raise ValueError("No APY evidence supports the selected location and season.")
        data_period_start = int(context["_year_start"].min())
        latest_data_year = int(context["_year_start"].max())

        training_start = model_readiness.training_year_start
        training_end = model_readiness.training_year_end
        reference_year = latest_data_year
        if training_end is not None:
            reference_year = min(latest_data_year, training_end)
        if training_start is not None and reference_year < training_start:
            reference_year = training_start

        crops = sorted(str(value) for value in context["Crop"].unique())
        evidence_tier = {"strong": 0, "moderate": 1, "limited": 2, "insufficient": 3}

        per_crop: dict[str, dict[str, Any]] = {}
        for crop in crops:
            stats = self._statistics(context, crop=crop, through_year=latest_data_year)
            eligible = int(stats["valid_observation_count"]) >= 1
            basis_key = (
                "recent_median_yield"
                if ranking_basis == "recent_median"
                else "historical_median_yield"
            )
            basis_value = stats[basis_key]
            if basis_value is None:
                basis_value = stats["historical_median_yield"]
            observed = context.loc[
                context["Crop"].eq(crop) & context["_year_start"].eq(latest_data_year)
            ]
            observed_yield = (
                float(observed.iloc[0]["_yield"]) if not observed.empty else None
            )
            predicted_yield: float | None = None
            model_status: str | None = None
            model_reason: str | None = None
            if not eligible:
                eligibility_reason = "no_valid_historical_observation"
            else:
                try:
                    prediction = self.yield_service.predict(
                        YieldFeatures(
                            Crop=crop,
                            Season=season,
                            Crop_Category=INDIVIDUAL_CROP_CATEGORY,
                            State=state,
                            District=district,
                            FE_YearStart=reference_year,
                        )
                    )
                except ValueError:
                    model_reason = "model_combination_not_supported"
                    eligibility_reason = "historical_evidence_only_model_unsupported"
                except (ModelArtifactError, ModelNotReadyError) as error:
                    raise APYDataError("The crop ranking model could not run.") from error
                else:
                    predicted_yield = prediction.value
                    model_status = prediction.prediction_period_status
                    eligibility_reason = "historical_evidence_and_model_supported"
            median = stats["historical_median_yield"]
            difference = (
                float(predicted_yield - median)
                if predicted_yield is not None and median is not None
                else None
            )
            warnings: list[str] = []
            if not eligible:
                warnings.append(
                    "No valid historical APY observation supports this crop for the "
                    "selected district and season."
                )
            if model_reason == "model_combination_not_supported":
                warnings.append(
                    "The served yield model does not support this crop-location "
                    "combination, so no model estimate is shown; the historical "
                    "ranking still applies."
                )
            per_crop[crop] = {
                "stats": stats,
                "eligible": eligible,
                "basis_value": basis_value,
                "observed_yield": observed_yield,
                "has_observation_in_latest_year": not observed.empty,
                "predicted_yield": predicted_yield,
                "model_status": model_status,
                "model_reason": model_reason,
                "eligibility_reason": eligibility_reason,
                "difference": difference,
                "warnings": warnings,
            }

        rankable = [
            (crop, float(entry["basis_value"]))
            for crop, entry in per_crop.items()
            if entry["eligible"] and entry["basis_value"] is not None
        ]
        rankable.sort(key=lambda item: (-item[1], item[0].casefold()))
        rank_by_crop = {
            crop: index for index, (crop, _) in enumerate(rankable, start=1)
        }
        evidence_sorted = sorted(
            [crop for crop, entry in per_crop.items() if entry["eligible"]],
            key=lambda crop: (
                evidence_tier.get(str(per_crop[crop]["stats"]["evidence_quality"]), 3),
                -int(per_crop[crop]["stats"]["valid_year_count"]),
                -float(per_crop[crop]["stats"]["recent_year_coverage"]),
                -(per_crop[crop]["stats"]["historical_median_yield"] or 0.0),
                crop.casefold(),
            ),
        )
        evidence_rank_by_crop = {
            crop: index for index, crop in enumerate(evidence_sorted, start=1)
        }

        ranking_available = len(rankable) >= 2
        top_crops = [crop for crop, _ in rankable[:candidate_limit]]
        candidates: list[dict[str, Any]] = []
        for crop in top_crops:
            entry = per_crop[crop]
            stats = entry["stats"]
            basis_value = entry["basis_value"]
            candidates.append(
                {
                    "crop": crop,
                    "rank": rank_by_crop.get(crop) if ranking_available else None,
                    "observed_yield": entry["observed_yield"],
                    "predicted_yield": entry["predicted_yield"],
                    "unit": YIELD_UNIT,
                    "ranking_value": float(basis_value) if basis_value is not None else None,
                    "ranking_basis": ranking_basis,
                    "evidence_rank": evidence_rank_by_crop.get(crop),
                    "model_reference_year": reference_year
                    if entry["predicted_yield"] is not None
                    else None,
                    "model_prediction_period_status": entry["model_status"],
                    "model_difference_from_median": entry["difference"],
                    "has_observation_in_latest_year": bool(
                        entry["has_observation_in_latest_year"]
                    ),
                    "warnings": list(entry["warnings"]),
                    "candidate_eligibility": {
                        "eligible": bool(entry["eligible"]),
                        "reason_code": entry["eligibility_reason"],
                        "evidence_quality": stats["evidence_quality"],
                        "valid_observation_count": stats["valid_observation_count"],
                        "valid_year_count": stats["valid_year_count"],
                    },
                    "historical_statistics": stats,
                }
            )

        year_row = context.loc[context["_year_start"].eq(latest_data_year), "Year"]
        year_label = str(year_row.iloc[0]) if not year_row.empty else None
        reference_year_policy = (
            "Model estimates use one internal reference year applied identically to "
            f"every candidate: min(latest APY year {latest_data_year}, model training "
            f"end {training_end}) = {reference_year}. It is an internal model input, "
            "not a user selection, and it is not a multi-year average."
        )
        return {
            "state": state,
            "district": district,
            "season": season,
            "crop_category": INDIVIDUAL_CROP_CATEGORY,
            "data_period_start": data_period_start,
            "latest_data_year": latest_data_year,
            "ranking_basis": ranking_basis,
            "top_n": candidate_limit,
            "reference_year": reference_year,
            "agricultural_year_start": latest_data_year,
            "agricultural_year_label": year_label,
            "ranking_available": ranking_available,
            "ranked_candidate_count": len(candidates) if ranking_available else 0,
            "eligible_candidate_count": len(rankable),
            "candidates": candidates,
            "ranking_methodology": (
                "Yield-based ranking sorts eligible individual crops by their recent "
                f"five-year median observed yield through APY year {latest_data_year} "
                "(historical median fallback), descending, with case-insensitive "
                "crop-name tie-breaking. A separate evidence-quality ranking orders "
                "candidates by evidence tier, valid-year count, recent coverage, then "
                "historical median. Eligibility requires at least one quality-controlled "
                "APY observation in this district and season (missing years are not "
                "interpolated or zero-filled). Model-estimated yield is supplementary "
                f"only, taken at one common internal reference year ({reference_year}) "
                "within the served model's training period, and never determines the "
                "order. This is historical yield evidence, not a guarantee of agronomic "
                "suitability, profitability, or future yield."
            ),
            "ranking_model": {
                "model_name": model_readiness.model_name or "unavailable",
                "model_version": model_readiness.model_version,
                "artifact_sha256": model_readiness.artifact_sha256 or "",
                "target": model_readiness.target or "Yield",
                "unit": YIELD_UNIT,
                "training_year_start": model_readiness.training_year_start or 0,
                "training_year_end": model_readiness.training_year_end or 0,
                "prediction_period_status": (
                    "in_training_range"
                    if training_start is not None
                    and training_end is not None
                    and training_start <= reference_year <= training_end
                    else "out_of_training_range_extrapolation"
                ),
                "reference_year": reference_year,
                "reference_year_policy": reference_year_policy,
                "quality_status": "experimental",
                "production_approved": False,
                "limitations": list(model_readiness.limitations),
            },
            "data_provenance": self.provenance,
            "limitations": list(DATASET_LIMITATIONS),
        }


@lru_cache(maxsize=8)
def cached_apy_data_service(
    dataset_path: Path,
    yield_service: YieldPredictionService,
) -> APYDataService:
    return APYDataService(dataset_path, yield_service)
