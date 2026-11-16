from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from weather_intelligence import __version__
from weather_intelligence.features import describe_feature_schema
from weather_intelligence.manifest import (
    VARIABLES,
    ArchiveValidationError,
    canonical_json_bytes,
    parse_source_document,
    verify_manifest_digest,
    verify_manifest_sources,
)
from weather_intelligence.runtime import software_versions

QUALITY_COLUMNS = (
    "qc_missing",
    "qc_sentinel",
    "qc_non_finite",
    "qc_negative_precipitation",
    "qc_tmin_gt_tmax",
    "qc_pass",
)


def config_digest(config: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(config)).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_lookup(
    manifest: dict[str, Any], source_root: Path, config: dict[str, Any]
) -> dict[tuple[str, int, str], dict[str, Any]]:
    return verify_manifest_sources(manifest, source_root, config)


def _verify_existing_sources(
    source_root: Path, lookup: dict[tuple[str, int, str], dict[str, Any]]
) -> None:
    for (_variable, _year, _region), entry in sorted(lookup.items()):
        source = source_root / str(entry["relative_path"])
        if _file_sha256(source) != entry["sha256"]:
            raise ArchiveValidationError(
                f"Source hash changed after manifest creation: {entry['relative_path']}"
            )


def _existing_dataset(
    output_dir: Path,
    *,
    manifest_sha256: str,
    config_sha256: str,
    source_root: Path,
    source_lookup: dict[tuple[str, int, str], dict[str, Any]],
) -> dict[str, Any] | None:
    if not output_dir.exists():
        return None
    metadata_path = output_dir / "dataset_metadata.json"
    if not metadata_path.is_file():
        raise ArchiveValidationError(
            f"Output directory already exists without dataset metadata: {output_dir}"
        )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if (
        metadata.get("manifest_sha256") != manifest_sha256
        or metadata.get("config_sha256") != config_sha256
    ):
        raise ArchiveValidationError(
            "Existing versioned dataset has a different source manifest/config; refusing overwrite."
        )
    _verify_existing_sources(source_root, source_lookup)
    for partition in metadata.get("partitions", []):
        part_path = output_dir / str(partition["relative_path"])
        if not part_path.is_file() or part_path.stat().st_size != int(partition["size_bytes"]):
            raise ArchiveValidationError(f"Existing partition is missing or changed: {part_path}")
        if _file_sha256(part_path) != partition["sha256"]:
            raise ArchiveValidationError(f"Existing partition hash mismatch: {part_path}")
    return metadata


def _schema_metadata(manifest: dict[str, Any], config: dict[str, Any]) -> dict[bytes, bytes]:
    metadata: dict[bytes, bytes] = {
        b"dataset_version": str(config["dataset_version"]).encode(),
        b"schema_version": str(config["schema_version"]).encode(),
        b"manifest_sha256": str(manifest["manifest_sha256"]).encode(),
        b"canonical_row_key": b"cell_id,date",
        b"date_semantics": b"UTC calendar date (date32); not a local timestamp",
    }
    for variable, variable_metadata in manifest["source_metadata_by_variable"].items():
        metadata[f"source_tags.{variable}".encode()] = json.dumps(
            variable_metadata["source_tags"], separators=(",", ":")
        ).encode()
        metadata[f"unit.{variable}".encode()] = str(variable_metadata["unit"]).encode()
        metadata[f"source_api.{variable}".encode()] = str(
            variable_metadata["api_name"]
        ).encode()
        metadata[f"source_api_version.{variable}".encode()] = str(
            variable_metadata["api_version"]
        ).encode()
    return metadata


def _schema() -> pa.Schema:
    fields = [
        pa.field("cell_id", pa.string(), nullable=False),
        pa.field("latitude", pa.float64(), nullable=False),
        pa.field("longitude", pa.float64(), nullable=False),
        pa.field("date", pa.date32(), nullable=False),
        pa.field("T2M_MAX", pa.float64(), nullable=False),
        pa.field("T2M_MIN", pa.float64(), nullable=False),
        pa.field("PRECTOTCORR", pa.float64(), nullable=False),
        pa.field("T2M_MAX_source_region_id", pa.string(), nullable=False),
        pa.field("T2M_MAX_source_tags", pa.string(), nullable=False),
        pa.field("T2M_MAX_unit", pa.string(), nullable=False),
        pa.field("T2M_MIN_source_region_id", pa.string(), nullable=False),
        pa.field("T2M_MIN_source_tags", pa.string(), nullable=False),
        pa.field("T2M_MIN_unit", pa.string(), nullable=False),
        pa.field("PRECTOTCORR_source_region_id", pa.string(), nullable=False),
        pa.field("PRECTOTCORR_source_tags", pa.string(), nullable=False),
        pa.field("PRECTOTCORR_unit", pa.string(), nullable=False),
    ]
    fields.extend(pa.field(name, pa.bool_(), nullable=False) for name in QUALITY_COLUMNS)
    return pa.schema(fields)


def _write_partition(
    staging_dir: Path,
    year: int,
    manifest: dict[str, Any],
    config: dict[str, Any],
    cell_ids: list[str],
    cell_coordinates: list[tuple[float, float]],
    cell_source_regions: list[str],
    values: dict[str, np.ndarray],
) -> dict[str, Any]:
    days = [date.fromisoformat(key[:4] + "-" + key[4:6] + "-" + key[6:]) for key in _dates_for_year(year)]
    row_count = len(cell_ids) * len(days)
    for variable in VARIABLES:
        matrix = values[variable]
        if matrix.shape != (len(cell_ids), len(days)) or not np.isfinite(matrix).all():
            raise ArchiveValidationError(
                f"Incomplete or non-finite canonical values while writing {variable} {year}."
            )
    if np.any(values["PRECTOTCORR"] < 0):
        raise ArchiveValidationError(f"Negative precipitation remains in {year} panel values.")
    if np.any(values["T2M_MIN"] > values["T2M_MAX"]):
        raise ArchiveValidationError(f"T2M_MIN exceeds T2M_MAX in {year} panel values.")

    flattened_dates = [day for _cell_id in cell_ids for day in days]
    columns: dict[str, pa.Array] = {
        "cell_id": pa.array([cell_id for cell_id in cell_ids for _ in days], type=pa.string()),
        "latitude": pa.array(
            np.repeat(np.fromiter((coordinate[0] for coordinate in cell_coordinates), dtype=np.float64), len(days))
        ),
        "longitude": pa.array(
            np.repeat(np.fromiter((coordinate[1] for coordinate in cell_coordinates), dtype=np.float64), len(days))
        ),
        "date": pa.array(flattened_dates, type=pa.date32()),
    }
    for variable in VARIABLES:
        columns[variable] = pa.array(values[variable].reshape(-1), type=pa.float64())
        variable_metadata = manifest["source_metadata_by_variable"][variable]
        columns[f"{variable}_source_region_id"] = pa.array(
            [region for region in cell_source_regions for _ in days], type=pa.string()
        )
        columns[f"{variable}_source_tags"] = pa.array(
            [json.dumps(variable_metadata["source_tags"], separators=(",", ":"))] * row_count,
            type=pa.string(),
        )
        columns[f"{variable}_unit"] = pa.array(
            [str(variable_metadata["unit"])] * row_count, type=pa.string()
        )
    columns.update(
        {
            "qc_missing": pa.array(np.zeros(row_count, dtype=np.bool_)),
            "qc_sentinel": pa.array(np.zeros(row_count, dtype=np.bool_)),
            "qc_non_finite": pa.array(np.zeros(row_count, dtype=np.bool_)),
            "qc_negative_precipitation": pa.array(np.zeros(row_count, dtype=np.bool_)),
            "qc_tmin_gt_tmax": pa.array(np.zeros(row_count, dtype=np.bool_)),
            "qc_pass": pa.array(np.ones(row_count, dtype=np.bool_)),
        }
    )
    schema = _schema().with_metadata(_schema_metadata(manifest, config))
    table = pa.Table.from_pydict(columns, schema=schema)
    if table.num_rows != row_count or table.num_columns != len(schema):
        raise ArchiveValidationError(f"Arrow table shape differs from schema for {year}.")
    relative_path = Path(f"year={year}") / "part-00000.parquet"
    output_path = staging_dir / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        table,
        output_path,
        compression=str(config["canonical"]["compression"]),
        compression_level=int(config["canonical"]["compression_level"]),
        use_dictionary=[
            "cell_id",
            "T2M_MAX_source_region_id",
            "T2M_MAX_source_tags",
            "T2M_MAX_unit",
            "T2M_MIN_source_region_id",
            "T2M_MIN_source_tags",
            "T2M_MIN_unit",
            "PRECTOTCORR_source_region_id",
            "PRECTOTCORR_source_tags",
            "PRECTOTCORR_unit",
        ],
        row_group_size=int(config["canonical"]["row_group_size"]),
        version=str(config["canonical"]["parquet_version"]),
        data_page_version="1.0",
        write_statistics=True,
    )
    return {
        "year": year,
        "relative_path": relative_path.as_posix(),
        "row_count": table.num_rows,
        "size_bytes": output_path.stat().st_size,
        "sha256": _file_sha256(output_path),
    }


def _dates_for_year(year: int) -> tuple[str, ...]:
    from weather_intelligence.manifest import expected_date_keys

    return expected_date_keys(year)


def build_canonical_dataset(
    source_root: Path,
    manifest: dict[str, Any],
    config: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    """Create one deterministic Zstandard Parquet partition per calendar year."""
    manifest_sha = verify_manifest_digest(manifest)
    config_sha = config_digest(config)
    source_root = source_root.resolve()
    output_dir = output_dir.resolve()
    source_lookup = _source_lookup(manifest, source_root, config)
    existing = _existing_dataset(
        output_dir,
        manifest_sha256=manifest_sha,
        config_sha256=config_sha,
        source_root=source_root,
        source_lookup=source_lookup,
    )
    if existing is not None:
        return {**existing, "reused_existing": True}

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = output_dir.parent / f".staging-{output_dir.name}-{uuid.uuid4().hex[:12]}"
    staging_dir.mkdir()
    try:
        coordinate_entries = manifest["coordinates"]
        cell_ids = [str(item["cell_id"]) for item in coordinate_entries]
        cell_coordinates = [
            (float(item["latitude"]), float(item["longitude"])) for item in coordinate_entries
        ]
        cell_source_regions = [str(item["source_region_id"]) for item in coordinate_entries]
        coordinate_to_index = {
            coordinate: index for index, coordinate in enumerate(cell_coordinates)
        }
        partitions: list[dict[str, Any]] = []
        canonical_rows = 0
        for year in (int(value) for value in config["years"]):
            date_keys = _dates_for_year(year)
            day_index = {day: index for index, day in enumerate(date_keys)}
            matrices = {
                variable: np.full((len(cell_ids), len(date_keys)), np.nan, dtype=np.float64)
                for variable in VARIABLES
            }
            seen = {variable: set() for variable in VARIABLES}
            for region in config["region_ids"]:
                group_features: dict[str, dict[tuple[float, float], dict[str, float]]] = {}
                for variable in VARIABLES:
                    entry = source_lookup[(variable, year, str(region))]
                    source_path = source_root / str(entry["relative_path"])
                    try:
                        raw = source_path.read_bytes()
                    except OSError as error:
                        raise ArchiveValidationError(
                            f"Cannot read source file while building panel: {source_path}: {error}"
                        ) from error
                    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                        raise ArchiveValidationError(
                            f"Source hash changed after validation: {entry['relative_path']}"
                        )
                    document = parse_source_document(
                        source_path,
                        raw,
                        variable=variable,
                        year=year,
                        expected_sources=list(config["variables"][variable]["source_tags"]),
                        expected_unit=str(config["variables"][variable]["unit"]),
                        fill_value=float(config["source_api"]["fill_value"]),
                    )
                    group_features[variable] = document.features
                base_coordinates = set(group_features[VARIABLES[0]])
                if any(set(group_features[variable]) != base_coordinates for variable in VARIABLES[1:]):
                    raise ArchiveValidationError(
                        f"Variable cell keys changed in {region} {year} while building panel."
                    )
                for coordinate in base_coordinates:
                    if coordinate not in coordinate_to_index:
                        raise ArchiveValidationError(f"Unexpected grid coordinate {coordinate}.")
                    row_index = coordinate_to_index[coordinate]
                    for variable in VARIABLES:
                        if row_index in seen[variable]:
                            raise ArchiveValidationError(
                                f"Duplicate canonical cell-date records for {cell_ids[row_index]} {year}."
                            )
                        values_map = group_features[variable][coordinate]
                        if set(values_map) != set(date_keys):
                            raise ArchiveValidationError(
                                f"Date keys changed for {variable} {cell_ids[row_index]} {year}."
                            )
                        matrices[variable][row_index, :] = np.fromiter(
                            (values_map[day] for day in date_keys),
                            dtype=np.float64,
                            count=len(date_keys),
                        )
                        seen[variable].add(row_index)
            for variable in VARIABLES:
                if len(seen[variable]) != len(cell_ids):
                    raise ArchiveValidationError(
                        f"Incomplete canonical grid for {variable} {year}: "
                        f"{len(seen[variable])} of {len(cell_ids)} cells."
                    )
            partition = _write_partition(
                staging_dir,
                year,
                manifest,
                config,
                cell_ids,
                cell_coordinates,
                cell_source_regions,
                matrices,
            )
            partitions.append(partition)
            canonical_rows += int(partition["row_count"])

        expected_rows = len(cell_ids) * sum(len(_dates_for_year(int(y))) for y in config["years"])
        if canonical_rows != expected_rows or expected_rows != 11_045_160:
            raise ArchiveValidationError(
                f"Canonical row count differs from the audited result: {canonical_rows}."
            )
        parquet_bytes = sum(int(partition["size_bytes"]) for partition in partitions)
        feature_schema = describe_feature_schema(config)
        feature_schema_sha = hashlib.sha256(canonical_json_bytes(feature_schema)).hexdigest()
        metadata: dict[str, Any] = {
            "metadata_schema_version": "1.0.0",
            "dataset_version": str(config["dataset_version"]),
            "pipeline_version": __version__,
            "manifest_sha256": manifest_sha,
            "config_sha256": config_sha,
            "feature_schema_sha256": feature_schema_sha,
            "feature_schema": feature_schema,
            "source_file_count": len(manifest["files"]),
            "cell_count": len(cell_ids),
            "date_start": str(manifest["date_start"]),
            "date_end": str(manifest["date_end"]),
            "canonical_rows": canonical_rows,
            "row_key": config["canonical"]["row_key"],
            "partitioning": "year derived from UTC date, one Parquet file per year",
            "schema": [
                {"name": field.name, "type": str(field.type), "nullable": field.nullable}
                for field in _schema()
            ],
            "source_metadata_by_variable": manifest["source_metadata_by_variable"],
            "quality_flags": {
                "qc_missing": "True means at least one source variable was absent; expected False for every row.",
                "qc_sentinel": "True means a declared source fill value was found; expected False.",
                "qc_non_finite": "True means a non-finite numeric value was found; expected False.",
                "qc_negative_precipitation": "True means precipitation is below zero; expected False.",
                "qc_tmin_gt_tmax": "True means minimum temperature exceeds maximum; expected False.",
                "qc_pass": "True means all preceding quality checks passed.",
            },
            "quality_summary": {
                "qc_missing_rows": 0,
                "qc_sentinel_rows": 0,
                "qc_non_finite_rows": 0,
                "qc_negative_precipitation_rows": 0,
                "qc_tmin_gt_tmax_rows": 0,
                "qc_pass_rows": canonical_rows,
            },
            "storage": {
                "format": "Apache Parquet",
                "engine": f"pyarrow {pa.__version__}",
                "compression": config["canonical"]["compression"],
                "compression_level": config["canonical"]["compression_level"],
                "partition_count": len(partitions),
                "parquet_bytes": parquet_bytes,
                "parquet_mib": round(parquet_bytes / (1024 * 1024), 2),
            },
            "partitions": partitions,
            "software_versions": software_versions(),
        }
        (staging_dir / "dataset_metadata.json").write_bytes(canonical_json_bytes(metadata))
        if output_dir.exists():
            raise ArchiveValidationError(f"Dataset output appeared during build: {output_dir}")
        os.replace(staging_dir, output_dir)
        return {**metadata, "reused_existing": False}
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
