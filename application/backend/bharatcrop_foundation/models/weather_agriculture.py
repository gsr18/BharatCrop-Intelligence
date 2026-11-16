from __future__ import annotations

import hashlib
import json
import math
import threading
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bharatcrop_foundation.config import PROJECT_ROOT
from bharatcrop_foundation.models.apy_data import (
    NAMED_SEASONS,
    YIELD_UNIT,
    APYDataService,
)
from bharatcrop_foundation.models.weather_data import WeatherDataService

PHASE_ROOT = PROJECT_ROOT / "phase3b_weather_agriculture"
DEFAULT_FEATURES_PATH = PHASE_ROOT / "data" / "seasonal_weather_features.csv"
DEFAULT_CALENDAR_PATH = PHASE_ROOT / "data" / "crop_calendar_mappings_v1.json"
NASA_POWER_SOURCE = (
    "NASA POWER Daily API v2.10.1 (MERRA2 gridded meteorological estimates); "
    "daily PRECTOTCORR, T2M_MAX, and T2M_MIN values."
)
APY_RANKING_BASIS = "descending recent five-calendar-year median APY yield"
LIMITATIONS = [
    "District rankings describe historical APY crop performance; they do not establish future "
    "suitability, profitability, or guaranteed yield.",
    "Weather profiles are shown only for documented calendar mappings and complete daily windows; "
    "no partial season is summarized as complete.",
    "The current version has one statewide normal-calendar proxy mapping: Punjab Rice Kharif. "
    "Other crop-region combinations retain their APY ranking and have weather unavailable.",
    "The PAU calendar is applied retrospectively using the APY year-start as a "
    "calendar-year proxy; APY does not record actual sowing dates, variety, or growth stages.",
    "NASA POWER grid values are spatial estimates, not local station observations; "
    "distance and shared grid cells affect representativeness.",
    "Historical weather profiles and yield records are descriptive; they do not establish that "
    "weather caused a yield outcome or crop damage.",
    "Rainy-day, dry-spell, and extreme-temperature counts are unavailable because no sourced "
    "sourced thresholds applicable to unspecified APY varieties and growth stages.",
]
FEATURE_COLUMNS = (
    "State",
    "District",
    "calendar_year",
    "calendar_mapping_id",
    "calendar_version",
    "calendar_classification",
    "weather_source",
    "latitude",
    "longitude",
    "mapping_distance_km",
    "geography_confidence",
    "coordinate_source",
    "long_distance_flag",
    "shared_grid_district_count",
    "expected_days",
    "complete_days",
    "precipitation_valid_days",
    "tmax_valid_days",
    "tmin_valid_days",
    "complete_window",
    "seasonal_total_precipitation_mm",
    "mean_daily_precipitation_mm",
    "maximum_daily_precipitation_mm",
    "daily_precipitation_standard_deviation_mm",
    "mean_daily_tmax_c",
    "mean_daily_tmin_c",
    "monthly_precipitation_totals_json",
    "monthly_precipitation_share_json",
)


class WeatherAgricultureDataError(Exception):
    """Raised when Phase 3B research metadata or derived data are malformed."""


class WeatherAgricultureService:
    """Historical APY crop-region evidence with separately reported daily weather."""

    def __init__(
        self,
        apy_service: APYDataService,
        weather_service: WeatherDataService,
        features_path: Path = DEFAULT_FEATURES_PATH,
        calendar_path: Path = DEFAULT_CALENDAR_PATH,
    ) -> None:
        self.apy_service = apy_service
        self.weather_service = weather_service
        self.features_path = features_path
        self.calendar_path = calendar_path
        self._features: pd.DataFrame | None = None
        self._feature_digest: str | None = None
        self._calendars: dict[tuple[str, str, str], dict[str, Any]] | None = None
        self._calendar_version: str | None = None
        self._lock = threading.Lock()

    def _load_calendars(self) -> dict[tuple[str, str, str], dict[str, Any]]:
        if self._calendars is not None:
            return self._calendars
        with self._lock:
            if self._calendars is not None:
                return self._calendars
            try:
                document = json.loads(self.calendar_path.read_text(encoding="utf-8"))
                mappings = document["mappings"]
                version = str(document["version"])
                if not version.strip():
                    raise ValueError("Calendar registry version cannot be empty.")
                if not isinstance(mappings, list):
                    raise ValueError("Calendar mappings must be a list.")
                parsed: dict[tuple[str, str, str], dict[str, Any]] = {}
                for mapping in mappings:
                    key = (
                        str(mapping["crop"]).casefold(),
                        str(mapping["season"]).casefold(),
                        str(mapping["state"]).casefold(),
                    )
                    if key in parsed:
                        raise ValueError("Calendar mapping keys must be unique.")
                    parsed[key] = mapping
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                raise WeatherAgricultureDataError(
                    "The versioned crop-calendar registry could not be loaded."
                ) from error
            self._calendars = parsed
            self._calendar_version = version
            return parsed

    def _load_features(self) -> pd.DataFrame:
        if self._features is not None:
            return self._features
        with self._lock:
            if self._features is not None:
                return self._features
            if not self.features_path.is_file():
                self._features = pd.DataFrame(columns=FEATURE_COLUMNS)
                return self._features
            try:
                frame = pd.read_csv(self.features_path, low_memory=False)
                if set(FEATURE_COLUMNS).difference(frame.columns):
                    raise ValueError("Derived feature schema is incomplete.")
                if frame.duplicated(
                    ["State", "District", "calendar_year", "calendar_mapping_id"]
                ).any():
                    raise ValueError("Derived district-year keys are duplicated.")
                frame["calendar_year"] = pd.to_numeric(
                    frame["calendar_year"], errors="raise"
                ).astype("int64")
                raw_complete = frame["complete_window"].astype("string").str.strip().str.casefold()
                complete_values = raw_complete.map(
                    {"true": True, "false": False, "1": True, "0": False}
                )
                if complete_values.isna().any():
                    raise ValueError("Derived completeness flags contain unsupported values.")
                frame["complete_window"] = complete_values.astype(bool)
                for column in (
                    "latitude",
                    "longitude",
                    "mapping_distance_km",
                    "expected_days",
                    "complete_days",
                    "precipitation_valid_days",
                    "tmax_valid_days",
                    "tmin_valid_days",
                    "shared_grid_district_count",
                    "seasonal_total_precipitation_mm",
                    "mean_daily_precipitation_mm",
                    "maximum_daily_precipitation_mm",
                    "daily_precipitation_standard_deviation_mm",
                    "mean_daily_tmax_c",
                    "mean_daily_tmin_c",
                ):
                    frame[column] = pd.to_numeric(frame[column], errors="coerce")
                if frame["calendar_classification"].ne("normal_calendar_proxy").any():
                    raise ValueError("Unsupported calendar classification is present.")
                if (
                    frame["expected_days"].isna().any()
                    or frame["expected_days"].le(0).any()
                    or frame[
                        [
                            "complete_days",
                            "precipitation_valid_days",
                            "tmax_valid_days",
                            "tmin_valid_days",
                        ]
                    ]
                    .isna()
                    .any(axis=None)
                ):
                    raise ValueError("Derived day coverage is incomplete.")
                count_columns = [
                    "complete_days",
                    "precipitation_valid_days",
                    "tmax_valid_days",
                    "tmin_valid_days",
                ]
                if frame[count_columns].lt(0).any(axis=None) or frame[count_columns].gt(
                    frame["expected_days"], axis=0
                ).any(axis=None):
                    raise ValueError("Derived day counts fall outside the expected weather window.")
                metric_columns = [
                    "seasonal_total_precipitation_mm",
                    "mean_daily_precipitation_mm",
                    "maximum_daily_precipitation_mm",
                    "daily_precipitation_standard_deviation_mm",
                    "mean_daily_tmax_c",
                    "mean_daily_tmin_c",
                ]
                complete_mask = frame["complete_window"]
                if complete_mask.any():
                    if (
                        frame.loc[complete_mask, count_columns]
                        .ne(frame.loc[complete_mask, ["expected_days"]].to_numpy())
                        .any(axis=None)
                        or frame.loc[complete_mask, metric_columns].isna().any(axis=None)
                        or frame.loc[complete_mask, "seasonal_total_precipitation_mm"].lt(0).any()
                        or not np.isfinite(
                            frame.loc[complete_mask, metric_columns].to_numpy(dtype=float)
                        ).all()
                    ):
                        raise ValueError(
                            "Complete windows contain incomplete coverage or missing metrics."
                        )
                if frame.loc[~complete_mask, metric_columns].notna().any(axis=None):
                    raise ValueError("Incomplete windows must not contain seasonal aggregates.")
                # The feature data must refer to a known mapping and the current registry version.
                registry = json.loads(self.calendar_path.read_text(encoding="utf-8"))
                valid_mapping_ids = {str(mapping["mapping_id"]) for mapping in registry["mappings"]}
                if frame["calendar_version"].astype(str).ne(
                    str(registry["version"])
                ).any() or not set(frame["calendar_mapping_id"].astype(str)).issubset(
                    valid_mapping_ids
                ):
                    raise ValueError(
                        "Derived weather data do not match the current calendar registry."
                    )
                with self.features_path.open("rb") as stream:
                    digest = hashlib.sha256()
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
                self._feature_digest = digest.hexdigest()
            except (OSError, ValueError, pd.errors.ParserError, UnicodeError) as error:
                raise WeatherAgricultureDataError(
                    "Derived seasonal weather data failed its schema checks."
                ) from error
            self._features = frame.sort_values(
                ["State", "District", "calendar_year"], kind="mergesort"
            )
            return self._features

    @staticmethod
    def _finite(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None or pd.isna(value):
            return None
        clean = str(value).strip()
        return clean or None

    @staticmethod
    def _bool(value: Any) -> bool | None:
        if value is None or pd.isna(value):
            return None
        if isinstance(value, bool):
            return value
        return str(value).strip().casefold() in {"true", "1"}

    def options(self) -> dict[str, Any]:
        frame = self.apy_service.valid_frame
        years = sorted(int(value) for value in frame["_year_start"].unique())
        calendar_rows = [
            {
                "crop": str(mapping["crop"]),
                "season": str(mapping["season"]),
                "state": str(mapping["state"]),
                "version": str(self._calendar_version),
            }
            for mapping in self._load_calendars().values()
        ]
        return {
            "crops": sorted(str(value) for value in frame["Crop"].unique()),
            "states": sorted(str(value) for value in frame["State"].unique()),
            "seasons": [season for season in NAMED_SEASONS if season in set(frame["Season"])],
            "apy_year_start": years[0],
            "latest_apy_year": years[-1],
            "weather_year_start": min(self.weather_service.years),
            "weather_year_end": max(self.weather_service.years),
            "weather_source": NASA_POWER_SOURCE,
            "available_calendar_mappings": calendar_rows,
            "limitations": LIMITATIONS,
        }

    def _calendar_payload(self, mapping: dict[str, Any], registry_version: str) -> dict[str, Any]:
        window_start = mapping["weather_window_start"]
        month_number, day_number = (int(value) for value in window_start.split("-"))
        from calendar import month_name

        transplant_text = str(mapping["recommended_transplanting_window"]).split("-")[-1].strip()
        transplant_month_name, transplant_day = transplant_text.split()
        transplant_month = next(
            index
            for index in range(1, 13)
            if month_name[index].casefold() == transplant_month_name.casefold()
        )
        from datetime import date, timedelta

        transplant_end = date(2025, transplant_month, int(transplant_day))
        maturity_end = transplant_end + timedelta(
            days=int(mapping["weather_window_end_rule"]["duration_days_after_transplant"])
        )
        return {
            "mapping_id": mapping["mapping_id"],
            "version": registry_version,
            "classification": mapping["classification"],
            "source": mapping["source"],
            "source_url": mapping["source_url"],
            "applicable_state": mapping["state"],
            "crop": mapping["crop"],
            "season": mapping["season"],
            "recommended_nursery_sowing_window": mapping["recommended_nursery_sowing_window"],
            "recommended_transplanting_window": mapping["recommended_transplanting_window"],
            "crop_duration_after_transplant_days": [
                int(mapping["crop_duration_after_transplant_days"]["minimum"]),
                int(mapping["crop_duration_after_transplant_days"]["maximum"]),
            ],
            "weather_window_start": f"{month_name[month_number]} {day_number} (inclusive)",
            "weather_window_end": (
                f"{maturity_end.strftime('%B')} {maturity_end.day} "
                "(inclusive; latest transplant date plus 117 days)"
            ),
            "assumptions": list(mapping["assumptions"]),
            "limitations": list(mapping["limitations"]),
        }

    def _grid_provenance(self, state: str, district: str) -> dict[str, Any]:
        locations = self.weather_service.locations
        selected = locations.loc[locations["State"].eq(state) & locations["District"].eq(district)]
        if selected.empty:
            return {
                "mapping_status": "unmatched",
                "apy_geography_id": None,
                "coordinate_source": None,
                "geography_confidence": None,
                "grid_latitude": None,
                "grid_longitude": None,
                "mapping_distance_km": None,
                "long_distance_flag": None,
                "shared_grid_district_count": None,
            }
        location = selected.iloc[0]
        latitude = self._finite(location.get("nearest_grid_latitude"))
        longitude = self._finite(location.get("nearest_grid_longitude"))
        if latitude is None or longitude is None:
            return {
                "mapping_status": "unmatched",
                "apy_geography_id": self._text(location.get("apy_geography_id")),
                "coordinate_source": self._text(location.get("coordinate_source")),
                "geography_confidence": self._text(location.get("geography_confidence")),
                "grid_latitude": latitude,
                "grid_longitude": longitude,
                "mapping_distance_km": self._finite(location.get("nearest_grid_distance_km")),
                "long_distance_flag": self._bool(location.get("QC_Long_District_Grid_Distance")),
                "shared_grid_district_count": None,
            }
        coordinates = locations[["nearest_grid_latitude", "nearest_grid_longitude"]].apply(
            pd.to_numeric, errors="coerce"
        )
        same_grid = coordinates["nearest_grid_latitude"].round(3).eq(
            round(latitude, 3)
        ) & coordinates["nearest_grid_longitude"].round(3).eq(round(longitude, 3))
        shared_count = int(
            locations.loc[same_grid, ["State", "District"]].drop_duplicates().shape[0]
        )
        return {
            "mapping_status": "matched",
            "apy_geography_id": self._text(location.get("apy_geography_id")),
            "coordinate_source": self._text(location.get("coordinate_source")),
            "geography_confidence": self._text(location.get("geography_confidence")),
            "grid_latitude": latitude,
            "grid_longitude": longitude,
            "mapping_distance_km": self._finite(location.get("nearest_grid_distance_km")),
            "long_distance_flag": self._bool(location.get("QC_Long_District_Grid_Distance")),
            "shared_grid_district_count": shared_count,
        }

    @staticmethod
    def _monthly_values(row: pd.Series, column: str) -> dict[int, float]:
        value = row.get(column)
        if value is None or pd.isna(value):
            return {}
        try:
            parsed = json.loads(str(value))
        except (TypeError, json.JSONDecodeError):
            return {}
        if not isinstance(parsed, dict):
            return {}
        result: dict[int, float] = {}
        for key, item in parsed.items():
            number = WeatherAgricultureService._finite(item)
            if number is not None:
                result[int(key)] = number
        return result

    def _weather_profile(
        self,
        *,
        state: str,
        district: str,
        crop: str,
        season: str,
        apy_years: list[int],
        registry_version: str,
        calendar_registry: dict[tuple[str, str, str], dict[str, Any]],
    ) -> dict[str, Any]:
        mapping = calendar_registry.get((crop.casefold(), season.casefold(), state.casefold()))
        grid = self._grid_provenance(state, district)
        features = self._load_features()
        base: dict[str, Any] = {
            "available": False,
            "status": "calendar_unavailable",
            "unavailable_reason": (
                "No documented crop-calendar mapping supports this crop, season, and state."
            ),
            "calendar": self._calendar_payload(mapping, registry_version) if mapping else None,
            "grid": grid,
            "source": NASA_POWER_SOURCE,
            "expected_year_count": len(apy_years),
            "complete_year_count": 0,
            "matched_apy_years": apy_years,
            "complete_weather_years": [],
            "median_seasonal_total_precipitation_mm": None,
            "median_mean_daily_precipitation_mm": None,
            "maximum_daily_precipitation_mm": None,
            "median_daily_precipitation_standard_deviation_mm": None,
            "interannual_seasonal_precipitation_standard_deviation_mm": None,
            "interannual_seasonal_precipitation_cv": None,
            "median_mean_daily_tmax_c": None,
            "median_mean_daily_tmin_c": None,
            "monthly_precipitation": [],
            "rainy_day_count": None,
            "dry_spell_count": None,
            "extreme_temperature_day_count": None,
            "threshold_status": (
                "Unavailable: no crop-stage-specific threshold mapping is configured."
            ),
            "year_profiles": [],
            "limitations": [
                "Only complete daily windows are included; incomplete years are listed with "
                "values left null.",
                "APY valid observation year is matched to the normal calendar's calendar year as a "
                "documented proxy.",
            ],
        }
        if mapping is None:
            return base
        if grid["mapping_status"] != "matched":
            base.update(
                status="geography_unmatched",
                unavailable_reason="No supported district-to-grid coordinate mapping is available.",
            )
            return base
        if features.empty:
            base.update(
                status="features_unavailable",
                unavailable_reason="The Phase 3B daily seasonal feature dataset is unavailable.",
            )
            return base
        district_rows = features.loc[
            features["State"].eq(state)
            & features["District"].eq(district)
            & features["calendar_mapping_id"].eq(mapping["mapping_id"])
            & features["calendar_year"].isin(apy_years)
        ].sort_values("calendar_year", kind="mergesort")
        year_profiles: list[dict[str, Any]] = []
        for _, row in district_rows.iterrows():
            complete = bool(row["complete_window"])
            monthly_totals = self._monthly_values(row, "monthly_precipitation_totals_json")
            monthly_shares = self._monthly_values(row, "monthly_precipitation_share_json")
            year_profiles.append(
                {
                    "year": int(row["calendar_year"]),
                    "complete_window": complete,
                    "expected_days": int(row["expected_days"]),
                    "complete_days": int(row["complete_days"]),
                    "precipitation_valid_days": int(row["precipitation_valid_days"]),
                    "tmax_valid_days": int(row["tmax_valid_days"]),
                    "tmin_valid_days": int(row["tmin_valid_days"]),
                    "seasonal_total_precipitation_mm": self._finite(
                        row["seasonal_total_precipitation_mm"]
                    )
                    if complete
                    else None,
                    "mean_daily_precipitation_mm": self._finite(row["mean_daily_precipitation_mm"])
                    if complete
                    else None,
                    "maximum_daily_precipitation_mm": self._finite(
                        row["maximum_daily_precipitation_mm"]
                    )
                    if complete
                    else None,
                    "daily_precipitation_standard_deviation_mm": self._finite(
                        row["daily_precipitation_standard_deviation_mm"]
                    )
                    if complete
                    else None,
                    "mean_daily_tmax_c": self._finite(row["mean_daily_tmax_c"])
                    if complete
                    else None,
                    "mean_daily_tmin_c": self._finite(row["mean_daily_tmin_c"])
                    if complete
                    else None,
                    "monthly_precipitation": [
                        {
                            "month": month,
                            "total_mm": monthly_totals.get(month) if complete else None,
                            "share_percent": monthly_shares.get(month) if complete else None,
                        }
                        for month in range(5, 12)
                    ],
                }
            )
        complete_rows = district_rows.loc[district_rows["complete_window"]]
        complete_years = [int(value) for value in complete_rows["calendar_year"].tolist()]
        base["year_profiles"] = year_profiles
        base["complete_year_count"] = len(complete_years)
        base["complete_weather_years"] = complete_years
        if not complete_years:
            base.update(
                status="no_complete_weather_year",
                unavailable_reason=(
                    "No APY observation year has a complete daily weather window for this district."
                ),
            )
            return base

        def median(column: str) -> float | None:
            values = pd.to_numeric(complete_rows[column], errors="coerce").dropna()
            return float(values.median()) if len(values) else None

        seasonal_totals = pd.to_numeric(
            complete_rows["seasonal_total_precipitation_mm"], errors="coerce"
        ).dropna()
        interannual_sd = float(seasonal_totals.std(ddof=1)) if len(seasonal_totals) >= 2 else None
        seasonal_mean = float(seasonal_totals.mean()) if len(seasonal_totals) else None
        base.update(
            available=True,
            status="available",
            unavailable_reason=None,
            median_seasonal_total_precipitation_mm=median("seasonal_total_precipitation_mm"),
            median_mean_daily_precipitation_mm=median("mean_daily_precipitation_mm"),
            maximum_daily_precipitation_mm=(
                float(
                    pd.to_numeric(
                        complete_rows["maximum_daily_precipitation_mm"], errors="coerce"
                    ).max()
                )
                if complete_rows["maximum_daily_precipitation_mm"].notna().any()
                else None
            ),
            median_daily_precipitation_standard_deviation_mm=median(
                "daily_precipitation_standard_deviation_mm"
            ),
            interannual_seasonal_precipitation_standard_deviation_mm=interannual_sd,
            interannual_seasonal_precipitation_cv=(
                interannual_sd / seasonal_mean
                if interannual_sd is not None and seasonal_mean is not None and seasonal_mean > 0
                else None
            ),
            median_mean_daily_tmax_c=median("mean_daily_tmax_c"),
            median_mean_daily_tmin_c=median("mean_daily_tmin_c"),
            monthly_precipitation=[
                {
                    "month": month,
                    "median_total_mm": (
                        float(
                            np.median(
                                [
                                    self._monthly_values(
                                        row, "monthly_precipitation_totals_json"
                                    ).get(month)
                                    for _, row in complete_rows.iterrows()
                                    if month
                                    in self._monthly_values(
                                        row, "monthly_precipitation_totals_json"
                                    )
                                ]
                            )
                        )
                        if any(
                            month in self._monthly_values(row, "monthly_precipitation_totals_json")
                            for _, row in complete_rows.iterrows()
                        )
                        else None
                    ),
                    "median_share_percent": (
                        float(
                            np.median(
                                [
                                    self._monthly_values(
                                        row, "monthly_precipitation_share_json"
                                    ).get(month)
                                    for _, row in complete_rows.iterrows()
                                    if month
                                    in self._monthly_values(row, "monthly_precipitation_share_json")
                                ]
                            )
                        )
                        if any(
                            month in self._monthly_values(row, "monthly_precipitation_share_json")
                            for _, row in complete_rows.iterrows()
                        )
                        else None
                    ),
                }
                for month in range(5, 12)
            ],
        )
        return base

    def rank(
        self,
        *,
        crop: str,
        season: str,
        state: str | None = None,
    ) -> dict[str, Any]:
        if season not in NAMED_SEASONS:
            raise ValueError("Season must be Kharif, Rabi, or Summer.")
        frame = self.apy_service.valid_frame
        selected = frame.loc[frame["Crop"].eq(crop) & frame["Season"].eq(season)]
        if state is not None:
            selected = selected.loc[selected["State"].eq(state)]
        if selected.empty:
            raise ValueError("No valid APY evidence supports the selected crop, season, and state.")
        latest_year = int(selected["_year_start"].max())
        earliest_data_year = int(frame["_year_start"].min())
        recent_start = max(earliest_data_year, latest_year - 4)
        calendars = self._load_calendars()
        registry_version = str(self._calendar_version)

        grouped: list[dict[str, Any]] = []
        for (candidate_state, district), records in selected.groupby(
            ["State", "District"], sort=False
        ):
            records = records.sort_values("_year_start", kind="mergesort")
            values = records["_yield"].to_numpy(dtype=float)
            years = [int(value) for value in records["_year_start"].tolist()]
            recent = records.loc[records["_year_start"].between(recent_start, latest_year)]
            recent_values = recent["_yield"].to_numpy(dtype=float)
            recent_years = [int(value) for value in recent["_year_start"].tolist()]
            standard_deviation = float(np.std(values, ddof=1)) if len(values) >= 2 else None
            mean = float(np.mean(values)) if len(values) else None
            cv = (
                standard_deviation / mean
                if standard_deviation is not None and mean and mean > 0
                else None
            )
            recent_median = float(np.median(recent_values)) if len(recent_values) else None
            evidence_quality = (
                "insufficient"
                if not recent_years
                else "limited"
                if len(recent_years) == 1
                else "moderate"
                if len(recent_years) <= 3
                else "strong"
            )
            grouped.append(
                {
                    "state": str(candidate_state),
                    "district": str(district),
                    "ranking_basis": APY_RANKING_BASIS,
                    "historical_median_yield": float(np.median(values)) if len(values) else None,
                    "historical_mean_yield": mean,
                    "recent_five_year_median_yield": recent_median,
                    "yield_standard_deviation": standard_deviation,
                    "coefficient_of_variation": cv,
                    "valid_observation_count": int(len(records)),
                    "valid_observation_year_count": int(len(years)),
                    "valid_observation_years": years,
                    "latest_observation_year": max(years) if years else None,
                    "recent_observation_year_count": len(recent_years),
                    "recent_window_year_start": recent_start,
                    "recent_window_year_end": latest_year,
                    "evidence_quality": evidence_quality,
                    "ranking_status": "ranked"
                    if recent_median is not None
                    else "no_recent_observation",
                    "evidence_explanation": (
                        f"{len(recent_years)} valid APY observation year(s) in the common "
                        f"{recent_start}-{latest_year} recent window; "
                        "evidence category reflects recent-year coverage, not yield level."
                    ),
                    "unit": YIELD_UNIT,
                }
            )
        ranked = [row for row in grouped if row["recent_five_year_median_yield"] is not None]
        unranked = [row for row in grouped if row["recent_five_year_median_yield"] is None]
        ranked.sort(
            key=lambda row: (
                -float(row["recent_five_year_median_yield"]),
                -float(row["historical_median_yield"]),
                row["state"].casefold(),
                row["district"].casefold(),
            )
        )
        unranked.sort(
            key=lambda row: (
                -(
                    float(row["historical_median_yield"])
                    if row["historical_median_yield"] is not None
                    else -math.inf
                ),
                row["state"].casefold(),
                row["district"].casefold(),
            )
        )
        ranking_available = len(ranked) >= 2
        if ranking_available:
            for position, candidate in enumerate(ranked, start=1):
                candidate["rank"] = position
        else:
            for candidate in ranked:
                candidate["rank"] = None
                candidate["ranking_status"] = "insufficient_comparison_set"
                candidate["evidence_explanation"] = (
                    f"{candidate['recent_observation_year_count']} valid recent APY observation "
                    "year(s) are available, "
                    "but fewer than two districts have recent evidence; "
                    "no comparative rank is assigned."
                )
        for candidate in unranked:
            candidate["rank"] = None
        candidates = ranked + unranked
        profiles = {
            f"{candidate['state']}::{candidate['district']}": self._weather_profile(
                state=candidate["state"],
                district=candidate["district"],
                crop=crop,
                season=season,
                apy_years=candidate["valid_observation_years"],
                registry_version=registry_version,
                calendar_registry=calendars,
            )
            for candidate in candidates
        }
        provenance = self.apy_service.provenance
        self._load_features()
        return {
            "crop": crop,
            "season": season,
            "state_filter": state,
            "ranking_basis": APY_RANKING_BASIS,
            "ranking_available": ranking_available,
            "data_period_start": int(selected["_year_start"].min()),
            "latest_available_apy_year": latest_year,
            "recent_window_year_start": recent_start,
            "recent_window_year_end": latest_year,
            "ranked_district_count": len(ranked) if ranking_available else 0,
            "unranked_district_count": len(unranked) + (0 if ranking_available else len(ranked)),
            "candidates": candidates,
            "weather_profiles": profiles,
            "data_source": str(provenance["dataset_source"]),
            "apy_source_file": str(provenance["source_file"]),
            "apy_sha256": str(provenance["sha256"]),
            "weather_source": NASA_POWER_SOURCE,
            "weather_feature_dataset": self.features_path.name,
            "weather_feature_sha256": self._feature_digest,
            "limitations": LIMITATIONS,
        }
