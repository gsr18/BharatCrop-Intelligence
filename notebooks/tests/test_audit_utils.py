from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from notebooks.audit_utils import (
    audit_apy_frame,
    audit_apy_source_exports,
    canonical_json_bytes,
    nearest_grid_diagnostics,
    verify_manifest_hash,
)


def _apy_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "State": "State A",
                "District": "District 1",
                "Crop": "Rice",
                "Season": "Kharif",
                "Crop_Category": "Individual Crop Candidate",
                "Year": "2020-21",
                "Area": 1.0,
                "Production": 2.0,
                "Yield": 2000.0,
            },
            {
                "State": "State A",
                "District": "District 1",
                "Crop": "Rice",
                "Season": "Kharif",
                "Crop_Category": "Individual Crop Candidate",
                "Year": "2020-21",
                "Area": 1.0,
                "Production": 2.0,
                "Yield": 2000.0,
            },
            {
                "State": "State A",
                "District": "District 2",
                "Crop": "Rice",
                "Season": "Rabi",
                "Crop_Category": "Grouping - Verify Source Definition",
                "Year": "2021-22",
                "Area": 0.0,
                "Production": -1.0,
                "Yield": None,
            },
        ]
    )


def test_apy_audit_reports_key_duplicates_missingness_and_measure_checks() -> None:
    frame = _apy_fixture()
    before = frame.copy(deep=True)
    summary = audit_apy_frame(frame)
    primary_key = "+".join(("State", "District", "Crop", "Season", "Year"))
    assert summary["row_count"] == 3
    assert summary["key_duplicate_counts"][primary_key] == {
        "duplicate_rows": 2,
        "duplicate_keys_after_first": 1,
    }
    assert summary["numeric_quality"]["Yield"]["missing_source_values"] == 1
    assert summary["numeric_quality"]["Production"]["negative_values"] == 1
    assert summary["yield_area_production_diagnostic"]["comparison_rows"] == 2
    assert summary["yield_area_production_diagnostic"]["relative_deviation_median"] == 0.0
    pd.testing.assert_frame_equal(frame, before)


def test_apy_audit_rejects_an_unrecognized_schema() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        audit_apy_frame(pd.DataFrame({"State": ["A"]}))


def test_nearest_grid_diagnostic_is_deterministic_and_not_mutating() -> None:
    crosswalk = pd.DataFrame(
        [
            {
                "apy_geography_id": "G1",
                "State": "State A",
                "District": "District 1",
                "latitude": 0.0,
                "longitude": 0.0,
                "geography_confidence": "PROVISIONAL",
            }
        ]
    )
    cells = pd.DataFrame(
        [
            {"cell_id": "cell_south", "latitude": -1.0, "longitude": 0.0},
            {"cell_id": "cell_north", "latitude": 1.0, "longitude": 0.0},
        ]
    )
    before = crosswalk.copy(deep=True)
    result = nearest_grid_diagnostics(crosswalk, cells)
    assert result.loc[0, "nearest_cell_id"] == "cell_south"
    assert result.loc[0, "nearest_grid_distance_km"] == pytest.approx(111.195, abs=0.01)
    pd.testing.assert_frame_equal(crosswalk, before)


def test_nearest_grid_diagnostic_rejects_missing_coordinates() -> None:
    crosswalk = pd.DataFrame(
        [{"apy_geography_id": "G1", "State": "S", "District": "D", "latitude": None, "longitude": 0.0}]
    )
    cells = pd.DataFrame([{"cell_id": "cell_0", "latitude": 0.0, "longitude": 0.0}])
    with pytest.raises(ValueError, match="Crosswalk coordinates contain missing"):
        nearest_grid_diagnostics(crosswalk, cells)


def test_manifest_hash_verification_uses_canonical_json() -> None:
    manifest = {"b": 2, "a": 1}
    expected = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    manifest["manifest_sha256"] = expected
    assert verify_manifest_hash(manifest) == expected
    manifest["a"] = 9
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_manifest_hash(manifest)


def test_repository_apy_table_has_the_audited_observation_key() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    source_path = (
        repository_root
        / "data"
        / "processed"
        / "historical_food_grains_apy_long_2013-14_to_2024-25.csv"
    )
    frame = pd.read_csv(source_path, low_memory=False)
    summary = audit_apy_frame(frame)
    primary_key = "+".join(("State", "District", "Crop", "Season", "Year"))
    assert summary["row_count"] == 376_272
    assert summary["unique_counts"]["Year"] == 12
    assert summary["unique_counts"]["State"] == 34
    assert summary["unique_counts"]["Crop"] == 19
    assert summary["key_duplicate_counts"][primary_key]["duplicate_rows"] == 0
    assert summary["missing_by_column"]["Yield"] == 95_033
    assert summary["yield_area_production_diagnostic"]["comparison_rows"] == 186_587
    assert summary["yield_area_production_diagnostic"]["over_25_percent_deviation_rows"] == 18_218


def test_repository_apy_long_table_reconciles_to_raw_period_exports() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    raw_paths = sorted((repository_root / "data" / "raw").glob("DES-District-Data-For-*.csv"))
    processed = pd.read_csv(
        repository_root
        / "data"
        / "processed"
        / "historical_food_grains_apy_long_2013-14_to_2024-25.csv",
        low_memory=False,
    )

    summary = audit_apy_source_exports(raw_paths, processed)

    assert summary["raw_file_count"] == 4
    assert summary["raw_rows_total_across_period_files"] == 102_995
    assert summary["raw_unique_union_key_count"] == 31_356
    assert len(summary["years"]) == 12
    assert all(year["unmatched_raw_keys"] == 0 for year in summary["years"].values())
    assert all(
        year["matched_raw_keys"] == year["raw_source_rows"]
        for year in summary["years"].values()
    )
    assert all(
        year["absent_source_keys_with_reported_values"] == 0
        for year in summary["years"].values()
    )
    assert all(
        all(mismatch_count == 0 for mismatch_count in year["measurement_value_mismatches"].values())
        for year in summary["years"].values()
    )


def test_repository_nearest_grid_reference_matches_recomputed_diagnostic() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    manifest = json.loads(
        (
            repository_root
            / "phase3b_weather_intelligence"
            / "manifests"
            / "source_manifest_v1.json"
        ).read_text(encoding="utf-8")
    )
    assert verify_manifest_hash(manifest) == (
        "52613b6b2f8a9c9ff8bdfb2e41bfa72ef5678eb751d186a9a17a370231d6d177"
    )
    crosswalk = pd.read_csv(repository_root / "metadata" / "apy_district_coordinate_crosswalk.csv")
    grid = pd.DataFrame(manifest["coordinates"])
    recalculated = nearest_grid_diagnostics(crosswalk, grid)
    existing_path = (
        repository_root
        / "data"
        / "processed"
        / "weather_regional"
        / "district_weather_annual_cleaned_flagged_2013_2024.csv"
    )
    existing = pd.read_csv(
        existing_path,
        usecols=[
            "apy_geography_id",
            "nearest_grid_latitude",
            "nearest_grid_longitude",
            "nearest_grid_distance_km",
        ],
    ).drop_duplicates("apy_geography_id")
    compared = existing.merge(
        recalculated[
            [
                "apy_geography_id",
                "nearest_grid_latitude",
                "nearest_grid_longitude",
                "nearest_grid_distance_km",
            ]
        ],
        on="apy_geography_id",
        suffixes=("_existing", "_recalculated"),
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    assert len(existing) == 640
    assert compared["_merge"].eq("both").sum() == 640
    matched = compared.loc[compared["_merge"].eq("both")]
    assert (
        matched["nearest_grid_latitude_existing"]
        == matched["nearest_grid_latitude_recalculated"]
    ).all()
    assert (
        matched["nearest_grid_longitude_existing"]
        == matched["nearest_grid_longitude_recalculated"]
    ).all()
    assert (
        matched["nearest_grid_distance_km_existing"]
        - matched["nearest_grid_distance_km_recalculated"]
    ).abs().max() < 1e-6
