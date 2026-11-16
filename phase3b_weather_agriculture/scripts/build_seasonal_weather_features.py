#!/usr/bin/env python3
"""Build isolated, complete-window seasonal NASA POWER features for supported calendars."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE_ROOT = PROJECT_ROOT / "phase3b_weather_agriculture"
DEFAULT_RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "weather_regional"
DEFAULT_GRID_REFERENCE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "weather_regional"
    / "district_weather_annual_cleaned_flagged_2013_2024.csv"
)
DEFAULT_CALENDAR_PATH = PHASE_ROOT / "data" / "crop_calendar_mappings_v1.json"
DEFAULT_OUTPUT = PHASE_ROOT / "data" / "seasonal_weather_features.csv"
VARIABLES = ("PRECTOTCORR", "T2M_MAX", "T2M_MIN")

def _date_for_year(year: int, month_day: str) -> date:
    month, day = (int(part) for part in month_day.split("-"))
    return date(year, month, day)


def _calendar_window(mapping: dict[str, Any], year: int) -> tuple[date, date]:
    start = _date_for_year(year, str(mapping["weather_window_start"]))
    end_rule = mapping["weather_window_end_rule"]
    # The source date is the final day in "June 20-July 10"; parse it explicitly.
    transplant_end_text = str(mapping["recommended_transplanting_window"]).split("-")[-1].strip()
    transplant_month_name, transplant_day_text = transplant_end_text.split()
    transplant_month = datetime.strptime(transplant_month_name, "%B").month
    transplant_end = date(year, transplant_month, int(transplant_day_text))
    end_inclusive = transplant_end + timedelta(days=int(end_rule["duration_days_after_transplant"]))
    end_exclusive = (
        end_inclusive + timedelta(days=1) if end_rule["inclusive_end_date"] else end_inclusive
    )
    return start, end_exclusive


def _coordinate_key(coordinates: list[float]) -> tuple[float, float]:
    longitude, latitude = coordinates[:2]
    return round(float(latitude), 3), round(float(longitude), 3)


def _find_grid_files(
    raw_root: Path, needed: set[tuple[float, float]], grid_year: int
) -> dict[tuple[float, float], str]:
    found: dict[tuple[float, float], list[str]] = defaultdict(list)
    for path in sorted(
        (raw_root / "PRECTOTCORR" / str(grid_year)).glob(
            f"R*_PRECTOTCORR_{grid_year}.json"
        )
    ):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Unable to read NASA POWER grid index file {path}") from error
        for feature in document.get("features", []):
            geometry = feature.get("geometry", {})
            coordinates = geometry.get("coordinates")
            if geometry.get("type") == "Point" and isinstance(coordinates, list):
                key = _coordinate_key(coordinates)
                if key in needed:
                    found[key].append(path.stem.split("_")[0])
    return {key: sorted(tile_ids)[0] for key, tile_ids in found.items()}


def _available_years(raw_root: Path) -> list[int]:
    years: set[int] = set()
    for variable in VARIABLES:
        variable_root = raw_root / variable
        if not variable_root.is_dir():
            continue
        for path in variable_root.iterdir():
            if path.is_dir() and path.name.isdigit() and len(path.name) == 4:
                years.add(int(path.name))
    if not years:
        raise RuntimeError(f"No daily NASA POWER year folders were found under {raw_root}.")
    return sorted(years)


def _grid_index_year(raw_root: Path) -> int:
    root = raw_root / "PRECTOTCORR"
    years = sorted(
        int(path.name)
        for path in root.iterdir()
        if path.is_dir() and path.name.isdigit() and len(path.name) == 4
    ) if root.is_dir() else []
    if not years:
        raise RuntimeError(f"No precipitation grid folders were found under {root}.")
    return years[0]


def _read_parameter(
    raw_root: Path,
    variable: str,
    year: int,
    tile_id: str,
    coordinate: tuple[float, float],
) -> dict[str, float | None]:
    path = raw_root / variable / str(year) / f"{tile_id}_{variable}_{year}.json"
    if not path.is_file():
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Unable to read NASA POWER daily source {path}") from error
    for feature in document.get("features", []):
        geometry = feature.get("geometry", {})
        coordinates = geometry.get("coordinates")
        if geometry.get("type") != "Point" or not isinstance(coordinates, list):
            continue
        if _coordinate_key(coordinates) != coordinate:
            continue
        parameters = feature.get("properties", {}).get("parameter", {})
        values = parameters.get(variable, {})
        if not isinstance(values, dict):
            return {}
        parsed: dict[str, float | None] = {}
        for day, value in values.items():
            try:
                parsed[str(day)] = float(value) if value is not None else None
            except (TypeError, ValueError):
                parsed[str(day)] = None
        return parsed
    return {}


def _valid_value(value: float | None, *, precipitation: bool) -> bool:
    if value is None or not math.isfinite(value) or value == -999:
        return False
    return not precipitation or value >= 0


def _safe_number(value: float | None) -> float | None:
    return float(value) if value is not None and math.isfinite(float(value)) else None


def build_features(
    *,
    raw_root: Path = DEFAULT_RAW_ROOT,
    grid_reference_path: Path = DEFAULT_GRID_REFERENCE,
    calendar_path: Path = DEFAULT_CALENDAR_PATH,
    output_path: Path = DEFAULT_OUTPUT,
) -> pd.DataFrame:
    calendar_document = json.loads(calendar_path.read_text(encoding="utf-8"))
    mappings = calendar_document["mappings"]
    if not mappings:
        raise ValueError("At least one documented calendar mapping is required.")
    locations = pd.read_csv(grid_reference_path, low_memory=False)
    required = {
        "State",
        "District",
        "apy_geography_id",
        "nearest_grid_latitude",
        "nearest_grid_longitude",
        "nearest_grid_distance_km",
        "geography_confidence",
        "coordinate_source",
        "QC_Long_District_Grid_Distance",
    }
    missing = required.difference(locations.columns)
    if missing:
        raise ValueError(f"Weather grid reference is missing columns: {sorted(missing)}")
    locations = locations.drop_duplicates(["State", "District"], keep="first")
    available_years = _available_years(raw_root)

    region_locations: dict[tuple[str, str], pd.Series] = {}
    for mapping in mappings:
        selected = locations.loc[
            locations["State"].eq(mapping["state"])
            & locations["nearest_grid_latitude"].notna()
            & locations["nearest_grid_longitude"].notna()
        ]
        for _, row in selected.iterrows():
            region_locations[(str(row["State"]), str(row["District"]))] = row

    needed_coordinates = {
        (
            round(float(row["nearest_grid_latitude"]), 3),
            round(float(row["nearest_grid_longitude"]), 3),
        )
        for row in region_locations.values()
    }
    coordinate_tiles = _find_grid_files(
        raw_root, needed_coordinates, _grid_index_year(raw_root)
    )
    shared_grid_counts = Counter(
        (
            round(float(row["nearest_grid_latitude"]), 3),
            round(float(row["nearest_grid_longitude"]), 3),
        )
        for _, row in locations.loc[
            locations["nearest_grid_latitude"].notna() & locations["nearest_grid_longitude"].notna()
        ]
        .drop_duplicates(["State", "District"])
        .iterrows()
    )
    parameter_cache: dict[
        tuple[str, int, str, tuple[float, float]], dict[str, float | None]
    ] = {}

    def values(
        variable: str, year: int, tile_id: str, coordinate: tuple[float, float]
    ) -> dict[str, float | None]:
        key = (variable, year, tile_id, coordinate)
        if key not in parameter_cache:
            parameter_cache[key] = _read_parameter(raw_root, variable, year, tile_id, coordinate)
        return parameter_cache[key]

    rows: list[dict[str, Any]] = []
    for mapping in mappings:
        for (state, district), location in sorted(region_locations.items()):
            if state != mapping["state"]:
                continue
            coordinate = (
                round(float(location["nearest_grid_latitude"]), 3),
                round(float(location["nearest_grid_longitude"]), 3),
            )
            tile_id = coordinate_tiles.get(coordinate)
            for year in available_years:
                start, end = _calendar_window(mapping, year)
                dates = [start + timedelta(days=offset) for offset in range((end - start).days)]
                day_keys = [day.strftime("%Y%m%d") for day in dates]
                expected_days = len(day_keys)
                if tile_id is None:
                    precip, tmax, tmin = {}, {}, {}
                else:
                    precip = values("PRECTOTCORR", year, tile_id, coordinate)
                    tmax = values("T2M_MAX", year, tile_id, coordinate)
                    tmin = values("T2M_MIN", year, tile_id, coordinate)
                precip_values = [precip.get(key) for key in day_keys]
                tmax_values = [tmax.get(key) for key in day_keys]
                tmin_values = [tmin.get(key) for key in day_keys]
                precip_valid = [
                    value for value in precip_values if _valid_value(value, precipitation=True)
                ]
                tmax_valid = [
                    value for value in tmax_values if _valid_value(value, precipitation=False)
                ]
                tmin_valid = [
                    value for value in tmin_values if _valid_value(value, precipitation=False)
                ]
                complete_days = sum(
                    _valid_value(p, precipitation=True)
                    and _valid_value(high, precipitation=False)
                    and _valid_value(low, precipitation=False)
                    for p, high, low in zip(precip_values, tmax_values, tmin_values, strict=True)
                )
                complete_window = bool(tile_id and complete_days == expected_days)
                monthly_totals: dict[int, float] | None = None
                monthly_shares: dict[int, float | None] | None = None
                seasonal_total = mean_daily = max_daily = daily_sd = mean_tmax = mean_tmin = None
                if complete_window:
                    seasonal_total = float(sum(precip_values))
                    mean_daily = float(np.mean(precip_values))
                    max_daily = float(max(precip_values))
                    daily_sd = float(np.std(precip_values, ddof=1))
                    mean_tmax = float(np.mean(tmax_values))
                    mean_tmin = float(np.mean(tmin_values))
                    month_values: dict[int, list[float]] = defaultdict(list)
                    for day, amount in zip(dates, precip_values, strict=True):
                        month_values[day.month].append(float(amount))
                    monthly_totals = {
                        month: float(sum(amounts))
                        for month, amounts in sorted(month_values.items())
                    }
                    monthly_shares = {
                        month: (total / seasonal_total * 100.0 if seasonal_total > 0 else None)
                        for month, total in monthly_totals.items()
                    }
                rows.append(
                    {
                        "State": state,
                        "District": district,
                        "apy_geography_id": location["apy_geography_id"],
                        "calendar_year": year,
                        "calendar_mapping_id": mapping["mapping_id"],
                        "calendar_version": calendar_document["version"],
                        "calendar_classification": mapping["classification"],
                        "weather_source": "NASA POWER Daily API v2.10.1 (MERRA2 gridded estimates)",
                        "latitude": coordinate[0],
                        "longitude": coordinate[1],
                        "mapping_distance_km": _safe_number(location["nearest_grid_distance_km"]),
                        "geography_confidence": location["geography_confidence"],
                        "coordinate_source": location["coordinate_source"],
                        "long_distance_flag": str(location["QC_Long_District_Grid_Distance"])
                        .strip()
                        .casefold()
                        in {"true", "1"},
                        "shared_grid_district_count": int(shared_grid_counts[coordinate]),
                        "tile_id": tile_id,
                        "window_start": start.isoformat(),
                        "window_end_exclusive": end.isoformat(),
                        "expected_days": expected_days,
                        "complete_days": complete_days,
                        "precipitation_valid_days": len(precip_valid),
                        "tmax_valid_days": len(tmax_valid),
                        "tmin_valid_days": len(tmin_valid),
                        "complete_window": complete_window,
                        "seasonal_total_precipitation_mm": seasonal_total,
                        "mean_daily_precipitation_mm": mean_daily,
                        "maximum_daily_precipitation_mm": max_daily,
                        "daily_precipitation_standard_deviation_mm": daily_sd,
                        "mean_daily_tmax_c": mean_tmax,
                        "mean_daily_tmin_c": mean_tmin,
                        "monthly_precipitation_totals_json": (
                            json.dumps(monthly_totals, sort_keys=True)
                            if monthly_totals is not None
                            else None
                        ),
                        "monthly_precipitation_share_json": (
                            json.dumps(monthly_shares, sort_keys=True)
                            if monthly_shares is not None
                            else None
                        ),
                    }
                )
    output = pd.DataFrame(rows)
    if output.duplicated(["State", "District", "calendar_year", "calendar_mapping_id"]).any():
        raise ValueError("Derived seasonal weather output contains duplicate district-year keys.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--grid-reference", type=Path, default=DEFAULT_GRID_REFERENCE)
    parser.add_argument("--calendar", type=Path, default=DEFAULT_CALENDAR_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_features(
        raw_root=args.raw_root,
        grid_reference_path=args.grid_reference,
        calendar_path=args.calendar,
        output_path=args.output,
    )
    complete_count = int(result["complete_window"].astype(bool).sum())
    print(
        f"Wrote {len(result)} district-year rows to {args.output}; "
        f"complete windows: {complete_count}; incomplete or unmatched: {len(result) - complete_count}."
    )


if __name__ == "__main__":
    main()
