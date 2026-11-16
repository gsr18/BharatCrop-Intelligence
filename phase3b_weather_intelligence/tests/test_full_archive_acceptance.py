from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pyarrow.parquet as pq

from weather_intelligence.archive import audit_archive
from weather_intelligence.dataset import build_canonical_dataset, config_digest
from weather_intelligence.features import describe_feature_schema
from weather_intelligence.manifest import canonical_json_bytes


def test_full_weather_archive_matches_locked_acceptance_contract(
    repository_root: Path, workspace_root: Path, config: dict[str, object]
) -> None:
    """Re-scan all 2,016 raw weather JSON files and verify the built output contract."""
    source_root = repository_root / "data" / "raw" / "weather_regional"
    audit = audit_archive(
        source_root,
        config,
        source_root_label=Path(config["source_root"]).as_posix(),
    )

    manifest_path = workspace_root / "manifests" / "source_manifest_v1.json"
    quality_path = workspace_root / "reports" / "source_quality_v1.json"
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == audit.manifest
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    assert quality == audit.quality_report
    assert audit.quality_report["source_files"] == 2016
    assert audit.quality_report["grid_cells"] == 2520
    assert audit.quality_report["dates_per_cell"] == 4383
    assert audit.quality_report["canonical_rows"] == 11_045_160
    assert audit.quality_report["measurements_total"] == 33_135_480
    assert audit.quality_report["measurements_by_variable"] == {
        "PRECTOTCORR": 11_045_160,
        "T2M_MAX": 11_045_160,
        "T2M_MIN": 11_045_160,
    }
    checks = quality["checks"]
    assert checks["expected_files"] == 2016
    assert all(
        checks[name] is True
        for name in (
            "all_source_headers_match",
            "variable_source_tags_preserved",
            "matching_grid_cells_across_variables_and_years",
            "complete_date_keys",
        )
    )
    assert all(
        checks[name] == 0
        for name in (
            "duplicate_json_keys",
            "duplicate_coordinates",
            "duplicate_cell_dates",
            "missing_expected_cell_dates",
            "unexpected_dates",
            "sentinel_values",
            "non_finite_values",
            "non_numeric_values",
            "negative_precipitation_values",
            "tmin_greater_than_tmax",
        )
    )
    assert audit.manifest["source_metadata_by_variable"]["T2M_MAX"]["source_tags"] == [
        "MERRA2",
        "POWER",
    ]
    assert audit.manifest["source_metadata_by_variable"]["T2M_MIN"]["source_tags"] == [
        "MERRA2",
        "POWER",
    ]
    assert audit.manifest["source_metadata_by_variable"]["PRECTOTCORR"]["source_tags"] == [
        "MERRA2"
    ]

    dataset_dir = workspace_root / "data" / "processed" / "weather_daily_v1"
    metadata = json.loads((dataset_dir / "dataset_metadata.json").read_text(encoding="utf-8"))
    schema_path = workspace_root / "schemas" / "weather_feature_schema_v1.json"
    feature_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert feature_schema == describe_feature_schema(config)
    assert hashlib.sha256(canonical_json_bytes(feature_schema)).hexdigest() == metadata[
        "feature_schema_sha256"
    ]
    assert metadata["manifest_sha256"] == audit.manifest["manifest_sha256"]
    assert metadata["config_sha256"] == config_digest(config)
    assert metadata["canonical_rows"] == 11_045_160
    assert metadata["cell_count"] == 2520
    assert metadata["quality_summary"]["qc_pass_rows"] == 11_045_160
    assert metadata["quality_summary"]["qc_missing_rows"] == 0
    assert metadata["quality_summary"]["qc_tmin_gt_tmax_rows"] == 0
    assert sum(int(part["row_count"]) for part in metadata["partitions"]) == 11_045_160
    assert sum(int(part["size_bytes"]) for part in metadata["partitions"]) == metadata["storage"]["parquet_bytes"]
    for partition in metadata["partitions"]:
        parquet_path = dataset_dir / partition["relative_path"]
        parquet = pq.ParquetFile(parquet_path)
        assert parquet.metadata.num_rows == partition["row_count"]
        names = parquet.schema_arrow.names
        assert {"cell_id", "date", "T2M_MAX", "T2M_MIN", "PRECTOTCORR"}.issubset(names)
        assert "T2M_MAX_source_region_id" in names
        assert "PRECTOTCORR_source_tags" in names
        assert "qc_pass" in names

    reused = build_canonical_dataset(source_root, audit.manifest, config, dataset_dir)
    assert reused["reused_existing"] is True
    assert reused["manifest_sha256"] == metadata["manifest_sha256"]

