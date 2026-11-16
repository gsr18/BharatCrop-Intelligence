"""Read-only audit helpers for the next agricultural/weather alignment stage."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

APY_REQUIRED_COLUMNS = (
    "State",
    "District",
    "Crop",
    "Season",
    "Crop_Category",
    "Year",
    "Area",
    "Production",
    "Yield",
)
APY_KEY_WITH_CATEGORY = (
    "State",
    "District",
    "Crop",
    "Season",
    "Crop_Category",
    "Year",
)
APY_KEY = ("State", "District", "Crop", "Season", "Year")
EARTH_MEAN_RADIUS_KM = 6371.0088


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def verify_manifest_hash(manifest: Mapping[str, Any]) -> str:
    """Verify the immutable Stage 2 manifest using its canonical JSON contract."""
    declared = manifest.get("manifest_sha256")
    payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    actual = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    if declared != actual:
        raise ValueError(f"Weather manifest hash mismatch: declared={declared!r}, actual={actual}.")
    return actual


def audit_apy_frame(frame: pd.DataFrame) -> dict[str, Any]:
    """Summarize the APY long-table schema, keys, missingness, and reported measures."""
    missing_columns = sorted(set(APY_REQUIRED_COLUMNS).difference(frame.columns))
    if missing_columns:
        raise ValueError(f"APY table is missing required columns: {missing_columns}.")

    key_duplicate_counts: dict[str, dict[str, int]] = {}
    for key in (APY_KEY, APY_KEY_WITH_CATEGORY):
        duplicated = frame.duplicated(list(key), keep=False)
        key_duplicate_counts["+".join(key)] = {
            "duplicate_rows": int(duplicated.sum()),
            "duplicate_keys_after_first": int(frame.duplicated(list(key)).sum()),
        }

    result: dict[str, Any] = {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "columns": [str(column) for column in frame.columns],
        "dtypes": {str(column): str(dtype) for column, dtype in frame.dtypes.items()},
        "missing_by_column": {
            str(column): int(value) for column, value in frame.isna().sum().items()
        },
        "key_duplicate_counts": key_duplicate_counts,
        "unique_counts": {
            column: int(frame[column].nunique(dropna=True))
            for column in ("State", "District", "Crop", "Season", "Crop_Category", "Year")
        },
        "category_counts": {
            column: {
                str(category): int(count)
                for category, count in frame[column].value_counts(dropna=False, sort=True).items()
            }
            for column in ("Season", "Crop_Category")
        },
        "rows_by_year": {
            str(year): int(count)
            for year, count in frame["Year"].astype("string").value_counts().sort_index().items()
        },
        "numeric_quality": {},
    }

    numeric_arrays: dict[str, np.ndarray] = {}
    for column in ("Area", "Production", "Yield"):
        converted = pd.to_numeric(frame[column], errors="coerce")
        values = converted.to_numpy(dtype=np.float64, na_value=np.nan)
        finite_mask = np.isfinite(values)
        numeric_arrays[column] = values
        finite_values = values[finite_mask]
        result["numeric_quality"][column] = {
            "missing_source_values": int(frame[column].isna().sum()),
            "non_numeric_source_values": int((frame[column].notna().to_numpy() & converted.isna().to_numpy()).sum()),
            "non_finite_values": int((converted.notna().to_numpy() & ~finite_mask).sum()),
            "finite_values": int(finite_mask.sum()),
            "zero_values": int((finite_mask & (values == 0)).sum()),
            "negative_values": int((finite_mask & (values < 0)).sum()),
            "positive_values": int((finite_mask & (values > 0)).sum()),
            "minimum_finite": float(finite_values.min()) if finite_values.size else None,
            "maximum_finite": float(finite_values.max()) if finite_values.size else None,
        }

    area = numeric_arrays["Area"]
    production = numeric_arrays["Production"]
    reported_yield = numeric_arrays["Yield"]
    positive_complete = (
        np.isfinite(area)
        & np.isfinite(production)
        & np.isfinite(reported_yield)
        & (area > 0)
        & (production > 0)
        & (reported_yield > 0)
    )
    implied = production[positive_complete] / area[positive_complete] * 1000.0
    relative_deviation = np.abs(reported_yield[positive_complete] - implied) / implied
    result["yield_area_production_diagnostic"] = {
        "comparison_rows": int(positive_complete.sum()),
        "candidate_formula": "(Production / Area) * 1000; units and conversion remain unverified",
        "relative_deviation_median": float(np.median(relative_deviation))
        if relative_deviation.size
        else None,
        "within_10_percent_rows": int((relative_deviation <= 0.10).sum()),
        "over_25_percent_deviation_rows": int((relative_deviation > 0.25).sum()),
    }
    return result


def audit_apy_source_exports(
    raw_paths: Iterable[str | Path],
    processed_long: pd.DataFrame,
) -> dict[str, Any]:
    """Reconcile raw three-year DES exports against the processed long APY table.

    Values are compared without unit conversion. Keys absent from a particular raw
    period export are checked to remain missing in the processed period slice.
    """
    keys = ["State", "District", "Crop", "Season"]
    measures = ("Area", "Production", "Yield")
    required_processed = set(keys + ["Year", *measures])
    missing_processed = sorted(required_processed.difference(processed_long.columns))
    if missing_processed:
        raise ValueError(f"Processed APY table is missing columns: {missing_processed}.")

    ordered_paths = sorted(Path(path) for path in raw_paths)
    if not ordered_paths:
        raise ValueError("No raw APY source export files were provided.")

    yearly: dict[str, dict[str, Any]] = {}
    file_summaries: list[dict[str, Any]] = []
    all_raw_keys: list[pd.DataFrame] = []

    for path in ordered_paths:
        raw = pd.read_csv(path, low_memory=False)
        missing_keys = sorted(set(keys).difference(raw.columns))
        if missing_keys:
            raise ValueError(f"Raw APY export {path.name} is missing keys: {missing_keys}.")
        years = sorted(
            column.removeprefix("Yield-")
            for column in raw.columns
            if column.startswith("Yield-")
        )
        if not years:
            raise ValueError(f"Raw APY export {path.name} has no Yield-YYYY-YY columns.")
        if raw.duplicated(keys).any():
            raise ValueError(f"Raw APY export {path.name} contains duplicate source keys.")

        file_summaries.append(
            {
                "file": path.name,
                "rows": int(len(raw)),
                "columns": [str(column) for column in raw.columns],
                "years": years,
                "duplicate_source_keys": 0,
            }
        )
        all_raw_keys.append(raw[keys].drop_duplicates())

        for year in years:
            if year in yearly:
                raise ValueError(f"More than one raw APY export supplies year {year}.")
            expected_columns = [f"{measure}-{year}" for measure in measures]
            missing_columns = sorted(set(expected_columns).difference(raw.columns))
            if missing_columns:
                raise ValueError(
                    f"Raw APY export {path.name} is missing {year} measures: {missing_columns}."
                )

            raw_year = raw[keys + expected_columns].rename(
                columns={f"{measure}-{year}": f"{measure}_raw" for measure in measures}
            )
            processed_year = processed_long.loc[
                processed_long["Year"].astype("string").eq(year), keys + list(measures)
            ]
            if processed_year.duplicated(keys).any():
                raise ValueError(f"Processed APY table has duplicate keys for {year}.")

            raw_match = raw_year.merge(
                processed_year,
                on=keys,
                how="left",
                validate="one_to_one",
                indicator=True,
            )
            value_mismatches: dict[str, int] = {}
            for measure in measures:
                source_values = raw_match[f"{measure}_raw"]
                processed_values = raw_match[measure]
                equal_or_missing = source_values.eq(processed_values) | (
                    source_values.isna() & processed_values.isna()
                )
                value_mismatches[measure] = int((~equal_or_missing).sum())

            reverse_match = processed_year.merge(
                raw_year[keys],
                on=keys,
                how="left",
                validate="one_to_one",
                indicator=True,
            )
            source_absent = reverse_match["_merge"].eq("left_only")
            source_absent_has_values = reverse_match.loc[
                source_absent, list(measures)
            ].notna().any(axis=1)
            yearly[year] = {
                "source_file": path.name,
                "raw_source_rows": int(len(raw_year)),
                "matched_raw_keys": int(raw_match["_merge"].eq("both").sum()),
                "unmatched_raw_keys": int(raw_match["_merge"].eq("left_only").sum()),
                "processed_rows": int(len(processed_year)),
                "processed_keys_absent_from_source": int(source_absent.sum()),
                "absent_source_keys_with_reported_values": int(source_absent_has_values.sum()),
                "measurement_value_mismatches": value_mismatches,
            }

    raw_key_union = pd.concat(all_raw_keys, ignore_index=True).drop_duplicates()
    return {
        "raw_file_count": int(len(file_summaries)),
        "raw_rows_total_across_period_files": int(sum(item["rows"] for item in file_summaries)),
        "raw_unique_union_key_count": int(len(raw_key_union)),
        "files": file_summaries,
        "years": yearly,
    }


def nearest_grid_diagnostics(
    crosswalk: pd.DataFrame,
    grid_coordinates: pd.DataFrame,
) -> pd.DataFrame:
    """Compute spherical nearest-center distances as a diagnostic, never an areal mapping."""
    crosswalk_columns = {"apy_geography_id", "State", "District", "latitude", "longitude"}
    grid_columns = {"cell_id", "latitude", "longitude"}
    missing_crosswalk = sorted(crosswalk_columns.difference(crosswalk.columns))
    missing_grid = sorted(grid_columns.difference(grid_coordinates.columns))
    if missing_crosswalk or missing_grid:
        raise ValueError(
            f"Coordinate schema mismatch: crosswalk_missing={missing_crosswalk}, "
            f"grid_missing={missing_grid}."
        )
    if crosswalk[["latitude", "longitude"]].isna().any(axis=None):
        raise ValueError("Crosswalk coordinates contain missing values; do not invent locations.")
    if grid_coordinates[["latitude", "longitude"]].isna().any(axis=None):
        raise ValueError("Weather grid coordinates contain missing values.")
    if crosswalk["apy_geography_id"].duplicated().any():
        raise ValueError("Crosswalk geography IDs must be unique for this diagnostic.")
    if grid_coordinates["cell_id"].duplicated().any():
        raise ValueError("Weather cell IDs must be unique.")

    ordered_grid = grid_coordinates.sort_values(
        ["latitude", "longitude", "cell_id"], kind="mergesort"
    ).reset_index(drop=True)
    lat1 = np.radians(crosswalk["latitude"].to_numpy(dtype=np.float64))[:, None]
    lon1 = np.radians(crosswalk["longitude"].to_numpy(dtype=np.float64))[:, None]
    lat2 = np.radians(ordered_grid["latitude"].to_numpy(dtype=np.float64))[None, :]
    lon2 = np.radians(ordered_grid["longitude"].to_numpy(dtype=np.float64))[None, :]
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    haversine = (
        np.sin(delta_lat / 2.0) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(delta_lon / 2.0) ** 2
    )
    distances = 2.0 * EARTH_MEAN_RADIUS_KM * np.arcsin(
        np.sqrt(np.clip(haversine, 0.0, 1.0))
    )
    nearest_indices = distances.argmin(axis=1)
    row_indices = np.arange(len(crosswalk))
    output = crosswalk[
        [column for column in crosswalk.columns if column in {
            "apy_geography_id",
            "State",
            "District",
            "coordinate_source",
            "geography_confidence",
            "is_synthetic",
            "latitude",
            "longitude",
        }]
    ].copy()
    nearest = ordered_grid.iloc[nearest_indices].reset_index(drop=True)
    output["nearest_cell_id"] = nearest["cell_id"].to_numpy()
    output["nearest_grid_latitude"] = nearest["latitude"].to_numpy(dtype=np.float64)
    output["nearest_grid_longitude"] = nearest["longitude"].to_numpy(dtype=np.float64)
    output["nearest_grid_distance_km"] = distances[row_indices, nearest_indices]
    return output.reset_index(drop=True)
