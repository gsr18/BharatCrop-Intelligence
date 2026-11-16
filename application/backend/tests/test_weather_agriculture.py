from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bharatcrop_foundation.app import create_app
from bharatcrop_foundation.config import PROJECT_ROOT, Settings
from bharatcrop_foundation.models.apy_data import APYDataService
from bharatcrop_foundation.models.weather_agriculture import (
    FEATURE_COLUMNS,
    WeatherAgricultureService,
)
from bharatcrop_foundation.routes.weather_agriculture import router

CALENDAR = {
    "version": "test-1",
    "mappings": [
        {
            "mapping_id": "test-rice-kharif-v1",
            "classification": "normal_calendar_proxy",
            "state": "Punjab",
            "crop": "Rice",
            "season": "Kharif",
            "source": "test source",
            "source_url": "https://example.invalid/calendar",
            "recommended_nursery_sowing_window": "May 20-June 20",
            "recommended_transplanting_window": "June 20-July 10",
            "crop_duration_after_transplant_days": {"minimum": 93, "maximum": 117},
            "weather_window_start": "05-20",
            "weather_window_end_rule": {
                "anchor": "latest_recommended_transplanting_date",
                "duration_days_after_transplant": 117,
                "inclusive_end_date": True,
            },
            "assumptions": ["Test proxy."],
            "limitations": [],
        }
    ],
}


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    parent = PROJECT_ROOT / "phase3b_weather_agriculture" / "tmp" / "pytest_cases"
    path = parent / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class FakeWeatherService:
    years = list(range(2013, 2025))

    def __init__(self, locations: pd.DataFrame) -> None:
        self.locations = locations


def _apy_record(
    state: str,
    district: str,
    year: int,
    yield_value: float,
    *,
    crop: str = "Rice",
    season: str = "Kharif",
    invalid: bool = False,
) -> dict[str, object]:
    return {
        "State": state,
        "District": district,
        "Crop": crop,
        "Season": season,
        "Crop_Category": "Individual Crop Candidate",
        "Year": f"{year}-{year + 1}",
        "Area": 1.0 if not invalid else 0.0,
        "Production": 1.0,
        "Yield": yield_value,
        "start_year": year,
        "QC_AreaZero-ProductionPositive": invalid,
        "QC_AreaPositive-ProductionZero": False,
        "QC_NegativeMeasurements": False,
        "QC_PositiveYieldWithoutPositiveAreaProduction": False,
    }


def _locations(*, include_alpha: bool = True, include_beta: bool = True) -> pd.DataFrame:
    records = []
    for district, latitude, longitude in (
        ("Alpha", 31.5, 75.0),
        ("Beta", 31.5, 75.0),
    ):
        if (district == "Alpha" and not include_alpha) or (district == "Beta" and not include_beta):
            continue
        records.append(
            {
                "State": "Punjab",
                "District": district,
                "apy_geography_id": f"APY-{district}",
                "coordinate_source": "district centroid",
                "geography_confidence": "medium",
                "nearest_grid_latitude": latitude,
                "nearest_grid_longitude": longitude,
                "nearest_grid_distance_km": 18.0,
                "QC_Long_District_Grid_Distance": False,
            }
        )
    return pd.DataFrame(records)


def _feature_record(
    district: str,
    year: int,
    *,
    complete: bool = True,
    precipitation: float = 700.0,
) -> dict[str, object]:
    monthly_totals = {
        "5": 20.0,
        "6": 90.0,
        "7": 280.0,
        "8": 220.0,
        "9": 80.0,
        "10": 10.0,
        "11": 0.0,
    }
    monthly_shares = {
        key: (value / sum(monthly_totals.values()) * 100) for key, value in monthly_totals.items()
    }
    return {
        "State": "Punjab",
        "District": district,
        "calendar_year": year,
        "calendar_mapping_id": "test-rice-kharif-v1",
        "calendar_version": "test-1",
        "calendar_classification": "normal_calendar_proxy",
        "weather_source": "NASA POWER test daily grid",
        "latitude": 31.5,
        "longitude": 75.0,
        "mapping_distance_km": 18.0,
        "geography_confidence": "medium",
        "coordinate_source": "district centroid",
        "long_distance_flag": False,
        "shared_grid_district_count": 2,
        "tile_id": "R001",
        "window_start": f"{year}-05-20",
        "window_end_exclusive": f"{year}-11-05",
        "expected_days": 169,
        "complete_days": 169 if complete else 168,
        "precipitation_valid_days": 169 if complete else 168,
        "tmax_valid_days": 169 if complete else 169,
        "tmin_valid_days": 169 if complete else 169,
        "complete_window": complete,
        "seasonal_total_precipitation_mm": precipitation if complete else np.nan,
        "mean_daily_precipitation_mm": precipitation / 169 if complete else np.nan,
        "maximum_daily_precipitation_mm": 51.0 if complete else np.nan,
        "daily_precipitation_standard_deviation_mm": 6.2 if complete else np.nan,
        "mean_daily_tmax_c": 35.2 if complete else np.nan,
        "mean_daily_tmin_c": 24.8 if complete else np.nan,
        "monthly_precipitation_totals_json": json.dumps(monthly_totals) if complete else np.nan,
        "monthly_precipitation_share_json": json.dumps(monthly_shares) if complete else np.nan,
    }


def _service(
    tmp_path: Path,
    records: list[dict[str, object]],
    features: list[dict[str, object]] | None,
    *,
    locations: pd.DataFrame | None = None,
) -> WeatherAgricultureService:
    tmp_path.mkdir(parents=True, exist_ok=True)
    apy_path = tmp_path / "apy.csv"
    pd.DataFrame(records).to_csv(apy_path, index=False)
    calendar_path = tmp_path / "calendars.json"
    calendar_path.write_text(json.dumps(CALENDAR), encoding="utf-8")
    feature_path = tmp_path / "seasonal.csv"
    if features is not None:
        pd.DataFrame(features, columns=list(FEATURE_COLUMNS)).to_csv(feature_path, index=False)
    return WeatherAgricultureService(
        APYDataService(apy_path),
        FakeWeatherService(locations if locations is not None else _locations()),
        features_path=feature_path,
        calendar_path=calendar_path,
    )


def _records() -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for year, amount in zip(range(2020, 2025), [100, 200, 300, 400, 500], strict=True):
        output.append(_apy_record("Punjab", "Alpha", year, float(amount)))
        output.append(_apy_record("Punjab", "Beta", year, float(amount)))
    output.extend(
        [
            _apy_record("Punjab", "Old", 2018, 100),
            _apy_record("Punjab", "Old", 2019, 200),
            _apy_record("Other State", "Different", 2024, 900),
            _apy_record("Punjab", "Alpha", 2019, 9999, invalid=True),
            _apy_record("Punjab", "Alpha", 2024, 50, crop="Wheat", season="Rabi"),
        ]
    )
    return output


def test_apy_recent_historical_statistics_filtering_and_tie_order(tmp_path: Path) -> None:
    service = _service(
        tmp_path,
        _records(),
        [_feature_record("Alpha", 2023), _feature_record("Alpha", 2024)],
    )
    options = service.options()
    assert "Rice" in options["crops"] and "Wheat" in options["crops"]
    assert options["latest_apy_year"] == 2024

    result = service.rank(crop="Rice", season="Kharif", state="Punjab")
    assert [(row["state"], row["district"]) for row in result["candidates"][:2]] == [
        ("Punjab", "Alpha"),
        ("Punjab", "Beta"),
    ]
    assert result["candidates"][0]["recent_five_year_median_yield"] == 300
    assert result["candidates"][0]["historical_median_yield"] == 300
    assert result["candidates"][0]["valid_observation_count"] == 5
    assert result["candidates"][0]["valid_observation_year_count"] == 5
    assert result["candidates"][0]["latest_observation_year"] == 2024
    assert result["candidates"][0]["yield_standard_deviation"] == pytest.approx(
        np.std([100, 200, 300, 400, 500], ddof=1)
    )
    assert result["candidates"][0]["coefficient_of_variation"] == pytest.approx(
        np.std([100, 200, 300, 400, 500], ddof=1) / np.mean([100, 200, 300, 400, 500])
    )
    assert result["candidates"][0]["evidence_quality"] == "strong"
    assert result["candidates"][2]["ranking_status"] == "no_recent_observation"
    assert result["candidates"][2]["rank"] is None
    assert {row["state"] for row in service.rank(crop="Rice", season="Kharif")["candidates"]} == {
        "Punjab",
        "Other State",
    }
    other_state = service.rank(crop="Rice", season="Kharif", state="Other State")
    assert other_state["ranking_available"] is False
    assert other_state["ranked_district_count"] == 0
    assert other_state["candidates"][0]["ranking_status"] == "insufficient_comparison_set"
    with pytest.raises(ValueError, match="No valid APY evidence"):
        service.rank(crop="Rice", season="Rabi")


def test_complete_weather_features_calendar_and_shared_grid_provenance(tmp_path: Path) -> None:
    service = _service(
        tmp_path,
        _records(),
        [
            _feature_record("Alpha", 2023, precipitation=600),
            _feature_record("Alpha", 2024, precipitation=800),
            _feature_record("Beta", 2023, precipitation=500),
            _feature_record("Beta", 2024, precipitation=700),
        ],
    )
    result = service.rank(crop="Rice", season="Kharif", state="Punjab")
    profile = result["weather_profiles"]["Punjab::Alpha"]
    assert profile["status"] == "available"
    assert profile["complete_year_count"] == 2
    assert profile["matched_apy_years"] == [2020, 2021, 2022, 2023, 2024]
    assert profile["complete_weather_years"] == [2023, 2024]
    assert profile["median_seasonal_total_precipitation_mm"] == 700
    assert profile["maximum_daily_precipitation_mm"] == 51
    assert profile["median_mean_daily_tmax_c"] == pytest.approx(35.2)
    assert profile["grid"]["shared_grid_district_count"] == 2
    assert profile["calendar"]["classification"] == "normal_calendar_proxy"
    assert profile["calendar"]["version"] == "test-1"
    assert profile["year_profiles"][0]["complete_days"] == 169
    assert profile["year_profiles"][0]["monthly_precipitation"][0]["total_mm"] == 20
    assert profile["rainy_day_count"] is None
    assert profile["extreme_temperature_day_count"] is None


def test_incomplete_and_missing_weather_remain_unavailable_and_null(tmp_path: Path) -> None:
    incomplete = _feature_record("Alpha", 2024, complete=False)
    service = _service(tmp_path, _records(), [incomplete])
    profile = service.rank(crop="Rice", season="Kharif", state="Punjab")["weather_profiles"][
        "Punjab::Alpha"
    ]
    assert profile["status"] == "no_complete_weather_year"
    assert profile["year_profiles"][0]["complete_window"] is False
    assert profile["year_profiles"][0]["seasonal_total_precipitation_mm"] is None
    assert profile["year_profiles"][0]["mean_daily_tmax_c"] is None

    missing = _service(tmp_path / "missing", _records(), None)
    missing_profile = missing.rank(crop="Rice", season="Kharif", state="Punjab")[
        "weather_profiles"
    ]["Punjab::Alpha"]
    assert missing_profile["status"] == "features_unavailable"
    assert missing_profile["median_seasonal_total_precipitation_mm"] is None


def test_calendar_unavailable_and_unmatched_geography_keep_apy_ranking(tmp_path: Path) -> None:
    records = _records()
    records.extend(_apy_record("Punjab", "Unknown Grid", year, 250) for year in range(2020, 2025))
    service = _service(tmp_path, records, [], locations=_locations())
    result = service.rank(crop="Rice", season="Kharif", state="Punjab")
    assert result["candidates"]
    assert result["weather_profiles"]["Punjab::Unknown Grid"]["status"] == "geography_unmatched"
    wheat = service.rank(crop="Wheat", season="Rabi", state="Punjab")
    assert wheat["weather_profiles"]["Punjab::Alpha"]["status"] == "calendar_unavailable"


def test_api_schema_validates_inputs_and_returns_typed_response(tmp_path: Path) -> None:
    service = _service(
        tmp_path,
        _records(),
        [_feature_record("Alpha", 2023), _feature_record("Alpha", 2024)],
    )
    application = FastAPI()
    application.state.weather_agriculture_service = service
    application.include_router(router, prefix="/api/v1")
    client = TestClient(application)

    response = client.post(
        "/api/v1/weather-agriculture/regions",
        json={"crop": "Rice", "season": "Kharif", "state": "Punjab"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ranking_basis"] == "descending recent five-calendar-year median APY yield"
    assert payload["candidates"][0]["district"] == "Alpha"
    assert payload["weather_profiles"]["Punjab::Alpha"]["calendar"]["version"] == "test-1"
    assert "year" not in payload

    unsupported_season = client.post(
        "/api/v1/weather-agriculture/regions",
        json={"crop": "Rice", "season": "Total"},
    )
    assert unsupported_season.status_code == 422
    extra_year = client.post(
        "/api/v1/weather-agriculture/regions",
        json={"crop": "Rice", "season": "Kharif", "year": 2024},
    )
    assert extra_year.status_code == 422


def test_real_weather_agriculture_api_uses_processed_phase3b_dataset() -> None:
    client = TestClient(create_app(Settings(database_url=None)))
    options = client.get("/api/v1/weather-agriculture/options")
    assert options.status_code == 200
    assert options.json()["latest_apy_year"] == 2024
    assert options.json()["weather_source"].startswith("NASA POWER Daily API")

    response = client.post(
        "/api/v1/weather-agriculture/regions",
        json={"crop": "Rice", "season": "Kharif", "state": "Punjab"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ranking_available"] is True
    assert payload["ranked_district_count"] == 23
    assert payload["weather_feature_dataset"] == "seasonal_weather_features.csv"
    profiles = payload["weather_profiles"]
    assert profiles["Punjab::Amritsar"]["status"] == "available"
    assert profiles["Punjab::Amritsar"]["calendar"]["classification"] == "normal_calendar_proxy"
    assert profiles["Punjab::Amritsar"]["complete_year_count"] > 0
    assert profiles["Punjab::Amritsar"]["median_seasonal_total_precipitation_mm"] is not None
