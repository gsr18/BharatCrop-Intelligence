from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pandas as pd
import pytest
from fastapi import FastAPI

from bharatcrop_foundation.app import create_app
from bharatcrop_foundation.config import PROJECT_ROOT, Settings

WEATHER_SOURCE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "weather_regional"
    / "district_weather_annual_cleaned_flagged_2013_2024.csv"
)
WEATHER_HISTORY = PROJECT_ROOT / "models" / "weather_intelligence" / "district_weather_history.csv"
WEATHER_REFERENCE = (
    PROJECT_ROOT / "models" / "weather_intelligence" / "district_weather_reference.csv"
)
APY_WEATHER_SOURCE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "weather_regional"
    / "apy_weather_integrated_exploratory.csv"
)


def _request(
    application: FastAPI,
    method: str,
    path: str,
    *,
    params: dict[str, str | int] | None = None,
) -> httpx.Response:
    async def perform() -> httpx.Response:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.request(method, path, params=params)

    return asyncio.run(perform())


def test_real_weather_options_aggregation_and_route_contracts() -> None:
    application = create_app(Settings(database_url=None))
    options = _request(application, "GET", "/api/v1/weather/options")
    assert options.status_code == 200
    assert options.headers["x-request-id"]
    result = options.json()
    assert result["years"] == list(range(2013, 2025))
    assert result["dataset_provenance"]["record_count"] == 7680
    assert result["dataset_provenance"]["district_geography_count"] == 640

    state_options = _request(
        application,
        "GET",
        "/api/v1/weather/options",
        params={"state": "Andhra Pradesh"},
    )
    assert state_options.status_code == 200
    assert "Anakapalli" in state_options.json()["districts"]

    temperature = _request(
        application,
        "GET",
        "/api/v1/weather/temperature",
        params={
            "metric": "tmax_mean_c",
            "state": "Andhra Pradesh",
            "district": "Anakapalli",
            "year_start": 2024,
            "year_end": 2024,
        },
    )
    assert temperature.status_code == 200
    point = temperature.json()["points"][0]
    assert point["year"] == 2024
    assert point["value"] == 31.239836065573776
    assert point["unit"] == "degC"

    precipitation = _request(
        application,
        "GET",
        "/api/v1/weather/precipitation",
        params={
            "state": "Andhra Pradesh",
            "district": "Anakapalli",
            "year_start": 2024,
            "year_end": 2024,
        },
    )
    assert precipitation.status_code == 200
    assert precipitation.json()["points"][0]["value"] == 1389.61
    assert precipitation.json()["unit"] == "mm/year"

    overview = _request(
        application,
        "GET",
        "/api/v1/weather/overview",
        params={"state": "Andhra Pradesh", "district": "Anakapalli", "year": 2024},
    )
    assert overview.status_code == 200
    assert overview.json()["record_count"] == 1
    assert overview.json()["valid_day_coverage"]["tmax_valid_days"][
        "valid_day_total"
    ] == 366

    invalid = _request(
        application,
        "GET",
        "/api/v1/weather/temperature",
        params={"metric": "relative_humidity"},
    )
    assert invalid.status_code == 422


def test_weather_anomalies_match_saved_notebook_history_and_baseline() -> None:
    application = create_app(Settings(database_url=None))
    response = _request(
        application,
        "GET",
        "/api/v1/weather/anomalies",
        params={
            "state": "Andhra Pradesh",
            "district": "Anakapalli",
            "year_start": 2024,
            "year_end": 2024,
        },
    )
    assert response.status_code == 200
    record = response.json()["records"][0]

    history = pd.read_csv(WEATHER_HISTORY)
    saved = history.loc[
        history["State"].eq("Andhra Pradesh")
        & history["District"].eq("Anakapalli")
        & history["year"].eq(2024)
    ].iloc[0]
    for metric in ("tmin_mean_c", "tmax_mean_c", "precipitation_total_mm"):
        assert record["historical_percentile_status"][metric]["status"] == saved[
            f"{metric}_status"
        ]

    annual = pd.read_csv(
        WEATHER_SOURCE,
        usecols=["apy_geography_id", "State", "District", "calendar_year", "tmax_mean_c"],
    )
    district_rows = annual.loc[
        annual["State"].eq("Andhra Pradesh")
        & annual["District"].eq("Anakapalli")
    ]
    expected_deviation = (
        district_rows.loc[district_rows["calendar_year"].eq(2024), "tmax_mean_c"].iloc[0]
        - district_rows["tmax_mean_c"].mean()
    )
    assert record["tmax_mean_same_period_deviation_c"] == expected_deviation
    assert "not forecasts" in response.json()["method"]["interpretation"]

    temperature = _request(
        application,
        "GET",
        "/api/v1/weather/trends",
        params={
            "metric": "tmax_mean_c",
            "state": "Andhra Pradesh",
            "district": "Anakapalli",
        },
    )
    assert temperature.status_code == 200
    reference = pd.read_csv(WEATHER_REFERENCE)
    assert len(reference) == 751
    assert temperature.json()["series"][0]["observation_count"] == 12
    saved_history = pd.read_csv(WEATHER_HISTORY)
    expected_trend = saved_history.loc[
        saved_history["State"].eq("Andhra Pradesh")
        & saved_history["District"].eq("Anakapalli")
    ].sort_values("year")["mean_max_temperature_c"].tolist()
    actual_trend = [
        point["value"]
        for point in temperature.json()["series"][0]["yearly_values"]
    ]
    assert actual_trend == expected_trend

    annual_weather = pd.read_csv(
        WEATHER_SOURCE,
        usecols=["calendar_year", "tmax_mean_c"],
    )
    year_rows = annual_weather.loc[annual_weather["calendar_year"].eq(2013), "tmax_mean_c"]
    national = _request(
        application,
        "GET",
        "/api/v1/weather/trends",
        params={"metric": "tmax_mean_c"},
    )
    assert national.status_code == 200
    national_2013 = national.json()["series"][0]["yearly_values"][0]
    assert national_2013["year"] == 2013
    assert national_2013["value"] == pytest.approx(float(year_rows.mean()))
    assert national_2013["median"] == pytest.approx(float(year_rows.median()))
    assert national_2013["p95"] == pytest.approx(float(year_rows.quantile(0.95)))
    assert national_2013["maximum"] == pytest.approx(float(year_rows.max()))


def test_real_geographic_coverage_and_crop_weather_proxy_matching() -> None:
    application = create_app(Settings(database_url=None))
    global_coverage = _request(
        application,
        "GET",
        "/api/v1/weather/coverage",
        params={"page_size": 1},
    )
    assert global_coverage.status_code == 200
    assert global_coverage.json()["coverage_summary"] == {
        "reference_location_count": 751,
        "locations_with_weather": 640,
        "locations_without_weather": 111,
        "district_year_observations": 7680,
        "year_start": 2013,
        "year_end": 2024,
    }

    coverage = _request(
        application,
        "GET",
        "/api/v1/weather/coverage",
        params={"state": "Andhra Pradesh", "page_size": 500},
    )
    assert coverage.status_code == 200
    assert coverage.json()["coverage_summary"]["reference_location_count"] > 0
    assert coverage.json()["coverage_summary"]["district_year_observations"] == 288

    uncovered = _request(
        application,
        "GET",
        "/api/v1/weather/coverage",
        params={
            "state": "Andhra Pradesh",
            "district": "Alluri Sitharama Raju",
        },
    )
    assert uncovered.status_code == 200
    location = uncovered.json()["locations"][0]
    assert location["weather_year_count"] == 0
    assert location["available_years"] == []
    assert location["mapping_quality"] == "low"

    matched = _request(
        application,
        "GET",
        "/api/v1/weather/crop-context",
        params={
            "state": "Andhra Pradesh",
            "district": "Anakapalli",
            "crop": "Rice",
            "season": "Kharif",
            "year_start": 2024,
            "year_end": 2024,
        },
    )
    assert matched.status_code == 200
    match = matched.json()
    assert match["matched_count"] == 1
    assert match["unmatched_count"] == 0
    assert match["full_season_alignment_verified"] is False
    assert match["points"][0]["yield"] == 3164.0
    assert match["points"][0]["yield_unit"] == "kg/ha"
    assert match["points"][0]["weather_proxy_calendar_year"] == 2024
    assert match["points"][0]["weather_values"]["precipitation_total_mm"] == 1389.61
    assert match["crop_data_provenance"]["dataset_name"] == (
        "apy_weather_integrated_exploratory.csv"
    )
    assert len(match["crop_data_provenance"]["sha256"]) == 64
    assert match["project_integration_totals"]["apy_rows"] == 376272
    assert match["project_integration_totals"]["matched_rows"] == 320124
    assert match["project_integration_totals"]["unmatched_rows"] == 56148

    unmatched = _request(
        application,
        "GET",
        "/api/v1/weather/crop-context",
        params={
            "state": "Andhra Pradesh",
            "district": "Alluri Sitharama Raju",
            "page_size": 1,
        },
    )
    assert unmatched.status_code == 200
    assert unmatched.json()["matched_count"] == 0
    assert unmatched.json()["unmatched_count"] == unmatched.json()["total"]
    assert unmatched.json()["points"][0]["weather_available"] is False
    assert unmatched.json()["points"][0]["weather_values"]["tmax_mean_c"] is None


def test_classifier_and_weather_capabilities_are_reported_separately() -> None:
    application = create_app(Settings(database_url=None))
    classifier = _request(application, "GET", "/api/v1/weather/classifier")
    assert classifier.status_code == 200
    assert classifier.json()["artifact_available"] is False
    assert classifier.json()["execution_available"] is False
    assert classifier.json()["production_approved"] is False
    assert classifier.json()["deployment_status"] == "NOT READY"
    assert classifier.json()["algorithms_evaluated"] == [
        "Logistic regression",
        "Random forest classifier",
    ]
    assert classifier.json()["baseline_features"] == [
        "State",
        "District",
        "Crop",
        "Season",
        "start_year",
    ]
    assert classifier.json()["weather_feature_additions"] == [
        "tmin_mean_c",
        "tmax_mean_c",
        "precipitation_total_mm",
    ]
    assert classifier.json()["training_years"] == [2015, 2022]
    assert classifier.json()["test_years"] == [2023, 2024]

    capabilities = _request(application, "GET", "/api/v1/capabilities")
    assert capabilities.status_code == 200
    reported = {item["name"]: item for item in capabilities.json()["capabilities"]}
    assert reported["weather_insights"]["execution_available"] is True
    assert reported["crop_weather_context"]["execution_available"] is True
    assert reported["low_yield_classifier"]["execution_available"] is False
    assert reported["low_yield_classifier"]["production_approved"] is False


def test_weather_dataset_loading_failure_returns_unavailable(
    tmp_path: Path,
) -> None:
    application = create_app(
        Settings(database_url=None, weather_data_path=tmp_path / "missing.csv")
    )
    response = _request(application, "GET", "/api/v1/weather/options")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "feature_not_approved"


def test_invalid_weather_location_and_season_are_rejected() -> None:
    application = create_app(Settings(database_url=None))
    invalid_location = _request(
        application,
        "GET",
        "/api/v1/weather/temperature",
        params={"state": "Unknown state", "district": "Unknown district"},
    )
    assert invalid_location.status_code == 422

    district_without_state = _request(
        application,
        "GET",
        "/api/v1/weather/coverage",
        params={"district": "Anakapalli"},
    )
    assert district_without_state.status_code == 422

    invalid_season = _request(
        application,
        "GET",
        "/api/v1/weather/crop-context",
        params={
            "state": "Andhra Pradesh",
            "district": "Anakapalli",
            "season": "Monsoon",
        },
    )
    assert invalid_season.status_code == 422


def test_weather_dataset_files_are_the_processed_research_sources() -> None:
    assert WEATHER_SOURCE.is_file()
    assert WEATHER_HISTORY.is_file()
    assert WEATHER_REFERENCE.is_file()
    assert APY_WEATHER_SOURCE.is_file()
    assert len(pd.read_csv(WEATHER_SOURCE, nrows=1).columns) == 29
    assert pd.read_csv(APY_WEATHER_SOURCE, nrows=1).shape[0] == 1
