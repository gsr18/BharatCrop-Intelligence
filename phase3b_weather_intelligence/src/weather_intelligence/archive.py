from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from weather_intelligence.manifest import (
    VARIABLES,
    ArchiveAudit,
    ArchiveValidationError,
    _expected_source_files,
    expected_date_keys,
    manifest_digest,
    parse_source_document,
)


def audit_archive(
    source_root: Path,
    config: dict[str, Any],
    *,
    source_root_label: str,
) -> ArchiveAudit:
    """Validate the corpus a region-year at a time to bound peak memory."""
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise ArchiveValidationError(f"Weather source directory does not exist: {source_root}")
    expected_files = _expected_source_files(source_root, config)
    years = tuple(int(value) for value in config["years"])
    regions = tuple(str(value) for value in config["region_ids"])
    entries: list[dict[str, Any]] = []
    feature_count_by_variable_year: Counter[tuple[str, int]] = Counter()
    coordinates_by_variable_year: dict[tuple[str, int], set[tuple[float, float]]] = defaultdict(set)
    seen_coordinates_by_variable_year: dict[tuple[str, int], set[tuple[float, float]]] = defaultdict(set)
    ranges = {variable: [math.inf, -math.inf] for variable in VARIABLES}
    observation_counts: Counter[str] = Counter()
    feature_count_distribution: Counter[int] = Counter()
    source_headers_by_variable: dict[str, dict[str, Any]] = {}
    source_region_by_coordinate: dict[tuple[float, float], str] = {}
    regional_groups_checked = 0

    for year in years:
        expected_days = expected_date_keys(year)
        for region in regions:
            group: dict[str, Any] = {}
            for variable in VARIABLES:
                variable_spec = config["variables"][variable]
                path = expected_files[(variable, year, region)]
                try:
                    raw = path.read_bytes()
                except OSError as error:
                    raise ArchiveValidationError(f"Cannot read source file {path}: {error}") from error
                document = parse_source_document(
                    path,
                    raw,
                    variable=variable,
                    year=year,
                    expected_sources=list(variable_spec["source_tags"]),
                    expected_unit=str(variable_spec["unit"]),
                    fill_value=float(config["source_api"]["fill_value"]),
                )
                key = (variable, year)
                coordinates = set(document.features)
                for coordinate in coordinates:
                    previous_region = source_region_by_coordinate.setdefault(coordinate, region)
                    if previous_region != region:
                        raise ArchiveValidationError(
                            f"Grid cell {coordinate} changes archive region from "
                            f"{previous_region} to {region} for {variable} {year}."
                        )
                duplicates = seen_coordinates_by_variable_year[key].intersection(coordinates)
                if duplicates:
                    raise ArchiveValidationError(
                        f"Duplicate coordinates across region files for {variable} {year}: "
                        f"{sorted(duplicates)[:3]}"
                    )
                seen_coordinates_by_variable_year[key].update(coordinates)
                coordinates_by_variable_year[key].update(coordinates)
                feature_count_by_variable_year[key] += len(document.features)
                feature_count_distribution[len(document.features)] += 1
                observation_counts[variable] += len(document.features) * len(expected_days)
                for values in document.features.values():
                    for numeric in values.values():
                        ranges[variable][0] = min(ranges[variable][0], numeric)
                        ranges[variable][1] = max(ranges[variable][1], numeric)

                api = document.header["api"]
                source_metadata = {
                    "api_name": api["name"],
                    "api_version": api["version"],
                    "source_tags": document.header["sources"],
                    "time_standard": document.header["time_standard"],
                    "fill_value": document.header["fill_value"],
                    "unit": document.parameter["units"],
                }
                previous_metadata = source_headers_by_variable.setdefault(
                    variable, source_metadata
                )
                if previous_metadata != source_metadata:
                    raise ArchiveValidationError(
                        f"Source metadata changes within {variable}; refusing to flatten lineage."
                    )
                group[variable] = document
                entries.append(
                    {
                        "relative_path": path.relative_to(source_root).as_posix(),
                        "region_id": document.region_id,
                        "year": document.year,
                        "parameter_name": document.variable,
                        "unit": document.parameter["units"],
                        "start_date": document.header["start"],
                        "end_date": document.header["end"],
                        "time_standard": document.header["time_standard"],
                        "source_tags": document.header["sources"],
                        "fill_value": document.header["fill_value"],
                        "header": document.header,
                        "parameter_metadata": document.parameter,
                        "size_bytes": document.size_bytes,
                        "sha256": document.sha256,
                    }
                )

            first_variable = group[VARIABLES[0]]
            first_coordinates = set(first_variable.features)
            if any(set(group[variable].features) != first_coordinates for variable in VARIABLES[1:]):
                raise ArchiveValidationError(f"Variable grid keys differ in {region} {year}.")
            for coordinate in first_coordinates:
                maximum = group["T2M_MAX"].features[coordinate]
                minimum = group["T2M_MIN"].features[coordinate]
                precipitation = group["PRECTOTCORR"].features[coordinate]
                if (
                    len(maximum) != len(expected_days)
                    or len(minimum) != len(expected_days)
                    or len(precipitation) != len(expected_days)
                ):
                    raise ArchiveValidationError(
                        f"Inconsistent date counts at {coordinate} in {region} {year}."
                    )
                for day_key in expected_days:
                    if minimum[day_key] > maximum[day_key]:
                        raise ArchiveValidationError(
                            f"T2M_MIN exceeds T2M_MAX at {coordinate} {day_key} in {region}."
                        )
            regional_groups_checked += 1

    expected_coordinates_count = int(config["expected_grid"]["cell_count"])
    reference_coordinates = coordinates_by_variable_year[(VARIABLES[0], years[0])]
    if len(reference_coordinates) != expected_coordinates_count:
        raise ArchiveValidationError(
            f"Expected {expected_coordinates_count} grid cells; found {len(reference_coordinates)}."
        )
    for variable in VARIABLES:
        for year in years:
            key = (variable, year)
            if feature_count_by_variable_year[key] != expected_coordinates_count:
                raise ArchiveValidationError(
                    f"Feature count differs for {variable} {year}: "
                    f"{feature_count_by_variable_year[key]} vs {expected_coordinates_count}."
                )
            if coordinates_by_variable_year[key] != reference_coordinates:
                raise ArchiveValidationError(f"Grid coordinates differ for {variable} {year}.")

    grid = config["expected_grid"]
    latitudes = sorted({coordinate[0] for coordinate in reference_coordinates})
    longitudes = sorted({coordinate[1] for coordinate in reference_coordinates})
    if len(latitudes) != int(grid["latitude_count"]) or len(longitudes) != int(
        grid["longitude_count"]
    ):
        raise ArchiveValidationError("Latitude/longitude axis sizes differ from the audited grid.")
    for values, step, axis in (
        (latitudes, float(grid["latitude_step"]), "latitude"),
        (longitudes, float(grid["longitude_step"]), "longitude"),
    ):
        if any(not math.isclose(b - a, step, abs_tol=1e-9) for a, b in zip(values, values[1:])):
            raise ArchiveValidationError(f"Unexpected {axis} grid spacing.")
    if len(reference_coordinates) != len(latitudes) * len(longitudes):
        raise ArchiveValidationError("Grid coordinate set is not a complete rectangular product.")
    for actual, key in (
        (min(latitudes), "latitude_min"),
        (max(latitudes), "latitude_max"),
        (min(longitudes), "longitude_min"),
        (max(longitudes), "longitude_max"),
    ):
        if not math.isclose(actual, float(grid[key]), abs_tol=1e-9):
            raise ArchiveValidationError(f"Grid extent {key} differs from the audited contract.")

    if sum(observation_counts.values()) != 33_135_480:
        raise ArchiveValidationError(
            f"Expected 33,135,480 measurements; found {sum(observation_counts.values())}."
        )
    if regional_groups_checked != len(years) * len(regions):
        raise ArchiveValidationError(
            f"Expected {len(years) * len(regions)} region-year groups; found {regional_groups_checked}."
        )
    coordinates = [
        {
            "cell_id": f"cell_{index:04d}",
            "latitude": latitude,
            "longitude": longitude,
            "source_region_id": source_region_by_coordinate[(latitude, longitude)],
        }
        for index, (latitude, longitude) in enumerate(sorted(reference_coordinates))
    ]
    entries.sort(key=lambda item: (item["parameter_name"], item["year"], item["region_id"]))
    total_bytes = sum(int(item["size_bytes"]) for item in entries)
    manifest_payload = {
        "manifest_schema_version": "1.0.0",
        "dataset_version": str(config["dataset_version"]),
        "source_root": source_root_label,
        "source_file_count": len(entries),
        "source_total_bytes": total_bytes,
        "date_start": "2013-01-01",
        "date_end": "2024-12-31",
        "dates_per_cell": 4383,
        "cell_count": len(coordinates),
        "coordinate_id_rule": config["canonical"]["cell_id_rule"],
        "source_api": config["source_api"],
        "source_metadata_by_variable": source_headers_by_variable,
        "coordinates": coordinates,
        "files": entries,
    }
    manifest = dict(manifest_payload)
    manifest["manifest_sha256"] = manifest_digest(manifest_payload)
    quality_report = {
        "report_schema_version": "1.0.0",
        "dataset_version": str(config["dataset_version"]),
        "manifest_sha256": manifest["manifest_sha256"],
        "source_files": len(entries),
        "grid_cells": len(coordinates),
        "dates_per_cell": 4383,
        "date_start": "2013-01-01",
        "date_end": "2024-12-31",
        "canonical_rows": 11_045_160,
        "measurements_by_variable": dict(sorted(observation_counts.items())),
        "measurements_total": sum(observation_counts.values()),
        "checks": {
            "expected_files": 2016,
            "all_source_headers_match": True,
            "variable_source_tags_preserved": True,
            "matching_grid_cells_across_variables_and_years": True,
            "complete_date_keys": True,
            "duplicate_json_keys": 0,
            "duplicate_coordinates": 0,
            "duplicate_cell_dates": 0,
            "missing_expected_cell_dates": 0,
            "unexpected_dates": 0,
            "sentinel_values": 0,
            "non_finite_values": 0,
            "non_numeric_values": 0,
            "negative_precipitation_values": 0,
            "tmin_greater_than_tmax": 0,
        },
        "value_ranges": {
            variable: {"minimum": bounds[0], "maximum": bounds[1]}
            for variable, bounds in sorted(ranges.items())
        },
        "feature_count_per_file_distribution": {
            str(count): frequency
            for count, frequency in sorted(feature_count_distribution.items())
        },
        "source_total_bytes": total_bytes,
    }
    return ArchiveAudit(manifest=manifest, quality_report=quality_report)
