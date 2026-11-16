from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from weather_intelligence.manifest import (
    ArchiveValidationError,
    canonical_json_bytes,
    expected_date_keys,
    manifest_digest,
    parse_source_document,
    sha256_bytes,
    verify_manifest_digest,
    write_immutable_json,
)


def _raw_source(
    *,
    year: int = 2020,
    variable: str = "T2M_MAX",
    values: dict[str, object] | None = None,
    sources: list[str] | None = None,
    duplicate_feature: bool = False,
) -> tuple[Path, bytes]:
    unit = "mm/day" if variable == "PRECTOTCORR" else "C"
    source_tags = sources or (["MERRA2"] if variable == "PRECTOTCORR" else ["MERRA2", "POWER"])
    days = expected_date_keys(year)
    daily_values = values or {day: 12.5 for day in days}
    feature = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [80.625, 17.5]},
        "properties": {"parameter": {variable: daily_values}},
    }
    features = [feature, feature] if duplicate_feature else [feature]
    document = {
        "header": {
            "api": {"name": "POWER Daily API", "version": "v2.10.1"},
            "time_standard": "UTC",
            "fill_value": -999,
            "start": f"{year}0101",
            "end": f"{year}1231",
            "sources": source_tags,
        },
        "parameters": {variable: {"units": unit}},
        "features": features,
    }
    path = Path(f"R001_{variable}_{year}.json")
    return path, json.dumps(document, separators=(",", ":")).encode("utf-8")


def test_normal_and_leap_year_date_parsing() -> None:
    assert len(expected_date_keys(2013)) == 365
    assert expected_date_keys(2013)[0] == "20130101"
    assert expected_date_keys(2013)[-1] == "20131231"
    assert len(expected_date_keys(2024)) == 366
    assert expected_date_keys(2024)[59] == "20240229"
    assert date.fromisoformat("2024-02-29").isoformat() == "2024-02-29"


def test_source_parser_preserves_variable_specific_metadata() -> None:
    for variable, tags in (
        ("T2M_MAX", ["MERRA2", "POWER"]),
        ("T2M_MIN", ["MERRA2", "POWER"]),
        ("PRECTOTCORR", ["MERRA2"]),
    ):
        path, raw = _raw_source(variable=variable, sources=tags)
        parsed = parse_source_document(
            path,
            raw,
            variable=variable,
            year=2020,
            expected_sources=tags,
            expected_unit="mm/day" if variable == "PRECTOTCORR" else "C",
        )
        assert parsed.header["sources"] == tags
        assert parsed.parameter["units"] == ("mm/day" if variable == "PRECTOTCORR" else "C")
        assert parsed.region_id == "R001"
        assert parsed.features[(17.5, 80.625)]["20200229"] == 12.5


def test_source_metadata_variation_is_rejected() -> None:
    path, raw = _raw_source(sources=["POWER"])
    with pytest.raises(ArchiveValidationError, match="source tags"):
        parse_source_document(
            path,
            raw,
            variable="T2M_MAX",
            year=2020,
            expected_sources=["MERRA2", "POWER"],
            expected_unit="C",
        )


def test_missing_daily_record_is_rejected() -> None:
    values = {day: 12.5 for day in expected_date_keys(2020) if day != "20200229"}
    path, raw = _raw_source(values=values)
    with pytest.raises(ArchiveValidationError, match="Date coverage differs"):
        parse_source_document(
            path,
            raw,
            variable="T2M_MAX",
            year=2020,
            expected_sources=["MERRA2", "POWER"],
            expected_unit="C",
        )


def test_duplicate_coordinate_record_is_rejected() -> None:
    path, raw = _raw_source(duplicate_feature=True)
    with pytest.raises(ArchiveValidationError, match="Duplicate coordinate"):
        parse_source_document(
            path,
            raw,
            variable="T2M_MAX",
            year=2020,
            expected_sources=["MERRA2", "POWER"],
            expected_unit="C",
        )


def test_malformed_json_and_duplicate_json_key_are_rejected() -> None:
    path, _ = _raw_source()
    with pytest.raises(ArchiveValidationError, match="Malformed"):
        parse_source_document(
            path,
            b"{not-json",
            variable="T2M_MAX",
            year=2020,
            expected_sources=["MERRA2", "POWER"],
            expected_unit="C",
        )
    duplicate_date = b'{"header":{},"header":{},"parameters":{},"features":[]}'
    with pytest.raises(ArchiveValidationError, match="duplicate-key"):
        parse_source_document(
            path,
            duplicate_date,
            variable="T2M_MAX",
            year=2020,
            expected_sources=["MERRA2", "POWER"],
            expected_unit="C",
        )


@pytest.mark.parametrize(
    ("variable", "value", "message"),
    [
        ("T2M_MAX", -999, "sentinel"),
        ("T2M_MAX", float("inf"), "Non-finite"),
        ("PRECTOTCORR", -0.1, "Negative precipitation"),
    ],
)
def test_sentinel_non_finite_and_invalid_precipitation_are_rejected(
    variable: str, value: float, message: str
) -> None:
    values = {day: 1.0 for day in expected_date_keys(2020)}
    values["20200101"] = value
    path, raw = _raw_source(variable=variable, values=values)
    sources = ["MERRA2"] if variable == "PRECTOTCORR" else ["MERRA2", "POWER"]
    unit = "mm/day" if variable == "PRECTOTCORR" else "C"
    with pytest.raises(ArchiveValidationError, match=message):
        parse_source_document(
            path,
            raw,
            variable=variable,
            year=2020,
            expected_sources=sources,
            expected_unit=unit,
        )


def test_non_finite_json_constant_is_rejected() -> None:
    path, raw = _raw_source()
    raw = raw.replace(b"12.5", b"NaN", 1)
    with pytest.raises(ArchiveValidationError, match="Non-finite"):
        parse_source_document(
            path,
            raw,
            variable="T2M_MAX",
            year=2020,
            expected_sources=["MERRA2", "POWER"],
            expected_unit="C",
        )


def test_canonical_manifest_hash_and_immutable_write_are_reproducible(
    workspace_root: Path,
) -> None:
    first = {"b": 2, "a": 1}
    second = {"a": 1, "b": 2}
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    manifest = {"files": [], "value": "same"}
    manifest["manifest_sha256"] = manifest_digest(manifest)
    assert verify_manifest_digest(manifest) == verify_manifest_digest(dict(manifest))
    output = workspace_root / "tests" / ".manifest-immutable-test.json"
    assert not output.exists()
    try:
        write_immutable_json(output, manifest)
        write_immutable_json(output, dict(manifest))
        assert sha256_bytes(output.read_bytes()) == sha256_bytes(canonical_json_bytes(manifest))
        with pytest.raises(ArchiveValidationError, match="Refusing to overwrite"):
            write_immutable_json(output, {"different": True})
    finally:
        output.unlink(missing_ok=True)
