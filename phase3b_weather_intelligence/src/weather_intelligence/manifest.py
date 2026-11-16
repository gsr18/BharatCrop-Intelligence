from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REGIONAL_FILE = re.compile(
    r"(?P<region>R\d{3})_(?P<variable>[A-Z0-9_]+)_(?P<year>\d{4})\.json$"
)
VARIABLES = ("T2M_MAX", "T2M_MIN", "PRECTOTCORR")
SOURCE_ROOT_LABEL = "data/raw/weather_regional"


class ArchiveValidationError(RuntimeError):
    """Raised when source data differ from the audited archive contract."""


class DuplicateJsonKeyError(ValueError):
    """Raised for a repeated key in a JSON object, including a daily date key."""


@dataclass(frozen=True)
class SourceDocument:
    path: Path
    relative_path: str
    sha256: str
    size_bytes: int
    region_id: str
    year: int
    variable: str
    header: dict[str, Any]
    parameter: dict[str, Any]
    features: dict[tuple[float, float], dict[str, float]]


@dataclass(frozen=True)
class ArchiveAudit:
    manifest: dict[str, Any]
    quality_report: dict[str, Any]


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def manifest_digest(manifest: dict[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return sha256_bytes(canonical_json_bytes(payload))


def verify_manifest_digest(manifest: dict[str, Any]) -> str:
    declared = manifest.get("manifest_sha256")
    actual = manifest_digest(manifest)
    if declared != actual:
        raise ArchiveValidationError(
            f"Manifest digest mismatch: declared={declared!r}, actual={actual}."
        )
    return actual


def write_immutable_json(path: Path, value: Any) -> None:
    """Create a deterministic JSON record once; refuse to replace different bytes."""
    payload = canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_bytes()
        if existing != payload:
            raise ArchiveValidationError(
                f"Refusing to overwrite immutable file with different content: {path}"
            )
        return
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
    except FileExistsError:
        if path.read_bytes() != payload:
            raise ArchiveValidationError(
                f"Concurrent immutable-file conflict at {path}."
            ) from None


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ArchiveValidationError(f"Cannot read JSON file {path}: {error}") from error
    if not isinstance(value, dict):
        raise ArchiveValidationError(f"Expected a JSON object in {path}.")
    return value


def expected_date_keys(year: int) -> tuple[str, ...]:
    current = date(year, 1, 1)
    result: list[str] = []
    while current.year == year:
        result.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return tuple(result)


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def parse_source_bytes(raw: bytes, path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=lambda token: float("nan")
            if token in {"NaN", "Infinity", "-Infinity"}
            else token,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, DuplicateJsonKeyError) as error:
        raise ArchiveValidationError(f"Malformed or duplicate-key JSON in {path}: {error}") from error
    if not isinstance(value, dict):
        raise ArchiveValidationError(f"Expected a JSON object in {path}.")
    return value


def _expected_contract(config: dict[str, Any]) -> tuple[dict[str, int], tuple[str, ...]]:
    years = {int(value): 1 for value in config["years"]}
    regions = tuple(str(value) for value in config["region_ids"])
    return years, regions


def _parse_filename(path: Path, expected_variable: str, expected_year: int) -> tuple[str, int, str]:
    match = REGIONAL_FILE.fullmatch(path.name)
    if match is None:
        raise ArchiveValidationError(f"Unexpected regional filename: {path.name}")
    variable = match.group("variable")
    year = int(match.group("year"))
    region = match.group("region")
    if variable != expected_variable or year != expected_year:
        raise ArchiveValidationError(
            f"Filename contract mismatch at {path}: variable={variable}, year={year}."
        )
    return region, year, variable


def parse_source_document(
    path: Path,
    raw: bytes,
    *,
    variable: str,
    year: int,
    expected_sources: list[str],
    expected_unit: str,
    fill_value: float = -999.0,
) -> SourceDocument:
    region, _, _ = _parse_filename(path, variable, year)
    document = parse_source_bytes(raw, path)
    header = document.get("header")
    parameters = document.get("parameters")
    features = document.get("features")
    if not isinstance(header, dict) or not isinstance(parameters, dict) or not isinstance(features, list):
        raise ArchiveValidationError(f"Missing header, parameters, or features in {path}.")

    api = header.get("api")
    expected_header = {
        "name": "POWER Daily API",
        "version": "v2.10.1",
        "time_standard": "UTC",
        "fill_value": fill_value,
        "start": f"{year}0101",
        "end": f"{year}1231",
    }
    if not isinstance(api, dict):
        raise ArchiveValidationError(f"Missing API metadata in {path}.")
    actual_header = {
        "name": api.get("name"),
        "version": api.get("version"),
        "time_standard": header.get("time_standard"),
        "fill_value": header.get("fill_value"),
        "start": header.get("start"),
        "end": header.get("end"),
    }
    if actual_header != expected_header:
        raise ArchiveValidationError(
            f"Source header differs from the audited contract in {path}: {actual_header}."
        )
    source_tags = header.get("sources")
    if source_tags != expected_sources:
        raise ArchiveValidationError(
            f"Variable-specific source tags differ in {path}: {source_tags!r}; "
            f"expected {expected_sources!r}."
        )
    if set(parameters) != {variable}:
        raise ArchiveValidationError(f"Unexpected parameter names in {path}: {sorted(parameters)}")
    parameter = parameters[variable]
    if not isinstance(parameter, dict) or parameter.get("units") != expected_unit:
        raise ArchiveValidationError(
            f"Unit metadata differs for {variable} in {path}: {parameter!r}."
        )

    expected_dates = set(expected_date_keys(year))
    parsed_features: dict[tuple[float, float], dict[str, float]] = {}
    for feature in features:
        if not isinstance(feature, dict):
            raise ArchiveValidationError(f"Malformed feature object in {path}.")
        geometry = feature.get("geometry")
        properties = feature.get("properties")
        coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            raise ArchiveValidationError(f"Missing point coordinates in {path}.")
        try:
            longitude, latitude = float(coordinates[0]), float(coordinates[1])
        except (TypeError, ValueError) as error:
            raise ArchiveValidationError(f"Invalid coordinates in {path}.") from error
        if not math.isfinite(latitude) or not math.isfinite(longitude):
            raise ArchiveValidationError(f"Non-finite coordinates in {path}.")
        coordinate = (round(latitude, 3), round(longitude, 3))
        if coordinate in parsed_features:
            raise ArchiveValidationError(f"Duplicate coordinate {coordinate} in {path}.")
        parameter_map = properties.get("parameter") if isinstance(properties, dict) else None
        if not isinstance(parameter_map, dict) or set(parameter_map) != {variable}:
            raise ArchiveValidationError(f"Unexpected variable keys in a feature in {path}.")
        values = parameter_map[variable]
        if not isinstance(values, dict):
            raise ArchiveValidationError(f"Daily values are not an object in {path} at {coordinate}.")
        keys = set(values)
        missing = expected_dates - keys
        extra = keys - expected_dates
        if missing or extra:
            raise ArchiveValidationError(
                f"Date coverage differs in {path} at {coordinate}: "
                f"missing={len(missing)}, unexpected={len(extra)}."
            )
        parsed_values: dict[str, float] = {}
        for day_key in sorted(expected_dates):
            raw_value = values[day_key]
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                raise ArchiveValidationError(
                    f"Non-numeric {variable} value at {coordinate} {day_key} in {path}."
                )
            numeric = float(raw_value)
            if numeric == fill_value:
                raise ArchiveValidationError(
                    f"Declared fill sentinel {fill_value} present for {variable} "
                    f"at {coordinate} {day_key} in {path}."
                )
            if not math.isfinite(numeric):
                raise ArchiveValidationError(
                    f"Non-finite {variable} value at {coordinate} {day_key} in {path}."
                )
            if variable == "PRECTOTCORR" and numeric < 0:
                raise ArchiveValidationError(
                    f"Negative precipitation at {coordinate} {day_key} in {path}."
                )
            parsed_values[day_key] = numeric
        parsed_features[coordinate] = parsed_values

    if not parsed_features:
        raise ArchiveValidationError(f"No grid cells found in {path}.")
    relative_path = path.as_posix()
    return SourceDocument(
        path=path,
        relative_path=relative_path,
        sha256=sha256_bytes(raw),
        size_bytes=len(raw),
        region_id=region,
        year=year,
        variable=variable,
        header=header,
        parameter=parameter,
        features=parsed_features,
    )


def _expected_source_files(source_root: Path, config: dict[str, Any]) -> dict[tuple[str, int, str], Path]:
    expected: dict[tuple[str, int, str], Path] = {}
    for variable in VARIABLES:
        for year in config["years"]:
            for region in config["region_ids"]:
                key = (variable, int(year), str(region))
                expected[key] = source_root / variable / str(year) / f"{region}_{variable}_{year}.json"
    actual = {
        path.resolve()
        for path in source_root.rglob("*.json")
        if path.is_file()
    }
    expected_paths = {path.resolve() for path in expected.values()}
    missing_paths = sorted(str(path) for path in expected_paths - actual)
    extra_paths = sorted(str(path) for path in actual - expected_paths)
    if missing_paths or extra_paths:
        raise ArchiveValidationError(
            f"Expected 2,016 regional JSON files; missing={len(missing_paths)}, "
            f"extra={len(extra_paths)}. First missing={missing_paths[:2]}, "
            f"first extra={extra_paths[:2]}."
        )
    return expected


def audit_archive(
    source_root: Path,
    config: dict[str, Any],
    *,
    source_root_label: str = SOURCE_ROOT_LABEL,
) -> ArchiveAudit:
    """Load the bounded-memory full-corpus validator."""
    from weather_intelligence.archive import audit_archive as bounded_audit_archive

    return bounded_audit_archive(
        source_root, config, source_root_label=source_root_label
    )

def verify_manifest_sources(
    manifest: dict[str, Any], source_root: Path, config: dict[str, Any]
) -> dict[tuple[str, int, str], dict[str, Any]]:
    verify_manifest_digest(manifest)
    lookup: dict[tuple[str, int, str], dict[str, Any]] = {}
    for entry in manifest.get("files", []):
        key = (
            str(entry["parameter_name"]),
            int(entry["year"]),
            str(entry["region_id"]),
        )
        if key in lookup:
            raise ArchiveValidationError(f"Duplicate manifest file key: {key}.")
        if key[0] not in config["variables"]:
            raise ArchiveValidationError(f"Unexpected variable in manifest: {key[0]}.")
        lookup[key] = entry
    expected_count = len(config["variables"]) * len(config["years"]) * len(config["region_ids"])
    if len(lookup) != expected_count:
        raise ArchiveValidationError(
            f"Manifest has {len(lookup)} file entries; expected {expected_count}."
        )
    actual_paths = {
        path.resolve()
        for path in source_root.rglob("*.json")
        if path.is_file()
    }
    expected_paths = {
        (source_root / str(entry["relative_path"])).resolve()
        for entry in lookup.values()
    }
    if actual_paths != expected_paths:
        raise ArchiveValidationError(
            f"Source file set changed after manifest creation: missing={len(expected_paths-actual_paths)}, "
            f"extra={len(actual_paths-expected_paths)}."
        )
    return lookup
