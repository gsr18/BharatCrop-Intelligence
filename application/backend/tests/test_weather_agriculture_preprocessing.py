from __future__ import annotations

import importlib.util
import json
import shutil
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pandas as pd
from pytest import fixture

from bharatcrop_foundation.config import PROJECT_ROOT

SCRIPT = (
    PROJECT_ROOT / "phase3b_weather_agriculture" / "scripts" / "build_seasonal_weather_features.py"
)
SPEC = importlib.util.spec_from_file_location("phase3b_weather_features", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
FEATURE_BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FEATURE_BUILDER)


@fixture
def tmp_path() -> Iterator[Path]:
    parent = PROJECT_ROOT / "phase3b_weather_agriculture" / "tmp" / "pytest_cases"
    path = parent / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _parameter_file(path: Path, variable: str, values: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "header": {"api": {"version": "v2.10.1"}, "sources": ["MERRA2"], "fill_value": -999.0},
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [75.0, 31.5, 250.0]},
                "properties": {"parameter": {variable: values}},
            }
        ],
    }
    path.write_text(json.dumps(document), encoding="utf-8")


def _mapping() -> dict[str, object]:
    return {
        "mapping_id": "test-calendar-v1",
        "classification": "normal_calendar_proxy",
        "state": "Punjab",
        "crop": "Rice",
        "season": "Kharif",
        "source": "Test source",
        "source_url": "https://example.invalid",
        "recommended_nursery_sowing_window": "May 20-June 20",
        "recommended_transplanting_window": "June 20-July 10",
        "crop_duration_after_transplant_days": {"minimum": 93, "maximum": 117},
        "weather_window_start": "05-20",
        "weather_window_end_rule": {
            "anchor": "latest_recommended_transplanting_date",
            "duration_days_after_transplant": 117,
            "inclusive_end_date": True,
        },
        "assumptions": [],
        "limitations": [],
    }


def _inputs(tmp_path: Path, *, omit_temperature_day: bool = False):
    raw_root = tmp_path / "raw"
    start = date(2013, 5, 20)
    end_exclusive = date(2013, 11, 5)
    day_keys = [
        (start + timedelta(days=index)).strftime("%Y%m%d")
        for index in range((end_exclusive - start).days)
    ]
    precipitation = {day: 0.0 for day in day_keys}
    precipitation["20130520"] = 1.0
    precipitation["20130601"] = 2.0
    precipitation["20130701"] = 3.0
    tmax = {day: 30.0 for day in day_keys}
    tmin = {day: 20.0 for day in day_keys}
    if omit_temperature_day:
        del tmax["20130801"]
    for variable, values in (
        ("PRECTOTCORR", precipitation),
        ("T2M_MAX", tmax),
        ("T2M_MIN", tmin),
    ):
        _parameter_file(
            raw_root / variable / "2013" / f"R001_{variable}_2013.json",
            variable,
            values,
        )
    reference = pd.DataFrame(
        [
            {
                "State": "Punjab",
                "District": district,
                "apy_geography_id": district,
                "nearest_grid_latitude": latitude,
                "nearest_grid_longitude": longitude,
                "nearest_grid_distance_km": 18.0,
                "geography_confidence": "medium",
                "coordinate_source": "district centroid",
                "QC_Long_District_Grid_Distance": False,
            }
            for district, latitude, longitude in (
                ("One", 31.5, 75.0),
                ("Two", 31.5, 75.0),
                ("No Grid", 35.0, 80.0),
            )
        ]
    )
    reference_path = tmp_path / "grid_reference.csv"
    reference.to_csv(reference_path, index=False)
    calendar_path = tmp_path / "calendar.json"
    calendar_path.write_text(
        json.dumps({"version": "test-1", "mappings": [_mapping()]}), encoding="utf-8"
    )
    return raw_root, reference_path, calendar_path


def test_complete_daily_window_aggregates_rainfall_distribution_and_shared_grid(
    tmp_path: Path,
) -> None:
    raw_root, reference, calendar = _inputs(tmp_path)
    output_path = tmp_path / "derived" / "features.csv"
    result = FEATURE_BUILDER.build_features(
        raw_root=raw_root,
        grid_reference_path=reference,
        calendar_path=calendar,
        output_path=output_path,
    )
    first = result.loc[result["District"].eq("One") & result["calendar_year"].eq(2013)].iloc[0]
    assert first["complete_window"]
    assert first["expected_days"] == 169
    assert first["complete_days"] == 169
    assert first["seasonal_total_precipitation_mm"] == 6
    assert first["mean_daily_precipitation_mm"] == 6 / 169
    assert first["maximum_daily_precipitation_mm"] == 3
    assert first["mean_daily_tmax_c"] == 30
    assert first["mean_daily_tmin_c"] == 20
    monthly = json.loads(first["monthly_precipitation_totals_json"])
    assert monthly["5"] == 1
    assert monthly["6"] == 2
    assert monthly["7"] == 3
    assert first["shared_grid_district_count"] == 2
    assert not result.loc[
        result["District"].eq("No Grid") & result["calendar_year"].eq(2013), "complete_window"
    ].iloc[0]
    assert pd.isna(
        result.loc[
            result["District"].eq("No Grid") & result["calendar_year"].eq(2013),
            "seasonal_total_precipitation_mm",
        ].iloc[0]
    )
    assert output_path.is_file()


def test_incomplete_daily_weather_does_not_produce_partial_season_metrics(tmp_path: Path) -> None:
    raw_root, reference, calendar = _inputs(tmp_path, omit_temperature_day=True)
    result = FEATURE_BUILDER.build_features(
        raw_root=raw_root,
        grid_reference_path=reference,
        calendar_path=calendar,
        output_path=tmp_path / "features.csv",
    )
    first = result.loc[result["District"].eq("One") & result["calendar_year"].eq(2013)].iloc[0]
    assert not first["complete_window"]
    assert first["complete_days"] == 168
    assert first["precipitation_valid_days"] == 169
    assert first["tmax_valid_days"] == 168
    assert pd.isna(first["seasonal_total_precipitation_mm"])
    assert pd.isna(first["mean_daily_tmax_c"])
