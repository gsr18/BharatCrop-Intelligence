from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from fastapi import FastAPI

from bharatcrop_foundation.app import create_app
from bharatcrop_foundation.config import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
APY_SOURCE = (
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
    json: dict[str, Any] | None = None,
    params: dict[str, str | int] | None = None,
) -> httpx.Response:
    async def perform() -> httpx.Response:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.request(method, path, json=json, params=params)

    return asyncio.run(perform())


def test_real_apy_options_filter_districts_and_named_seasons() -> None:
    application = create_app(Settings(database_url=None, apy_data_path=APY_SOURCE))
    global_options = _request(application, "GET", "/api/v1/rankings/crops/options")
    assert global_options.status_code == 200
    assert "Rice" in global_options.json()["crops"]
    assert "Cereals" not in global_options.json()["crops"]
    assert global_options.json()["seasons"] == ["Kharif", "Rabi", "Summer"]
    assert global_options.json()["agricultural_years"] == list(range(2013, 2025))

    state_options = _request(
        application,
        "GET",
        "/api/v1/rankings/crops/options",
        params={"state": "Andhra Pradesh"},
    )
    assert state_options.status_code == 200
    assert "Alluri Sitharama Raju" in state_options.json()["districts"]
    assert "Nicobars" not in state_options.json()["districts"]

    invalid_season = _request(
        application,
        "GET",
        "/api/v1/rankings/crops/options",
        params={"season": "Total"},
    )
    assert invalid_season.status_code == 422
    assert invalid_season.json()["error"]["code"] == "validation_error"


def test_real_apy_ranking_and_historical_evidence_contracts() -> None:
    application = create_app(Settings(database_url=None, apy_data_path=APY_SOURCE))
    ranking = _request(
        application,
        "POST",
        "/api/v1/rankings/crops",
        json={
            "state": "Andhra Pradesh",
            "district": "Anakapalli",
            "season": "Kharif",
        },
    )

    assert ranking.status_code == 200
    result = ranking.json()
    assert result["ranking_available"] is True
    assert result["crop_category"] == "Individual Crop Candidate"
    assert result["ranking_basis"] == "recent_median"
    assert result["latest_data_year"] == 2024
    assert result["agricultural_year_start"] == 2024
    assert result["top_n"] == 5
    assert result["reference_year"] == 2022

    candidates = result["candidates"]
    assert 2 <= len(candidates) <= 5
    assert [candidate["rank"] for candidate in candidates] == list(
        range(1, len(candidates) + 1)
    )
    assert all(candidate["candidate_eligibility"]["eligible"] for candidate in candidates)
    yield_values = [candidate["ranking_value"] for candidate in candidates]
    assert yield_values == sorted(yield_values, reverse=True)
    assert all(isinstance(candidate["evidence_rank"], int) for candidate in candidates)
    assert all(candidate["unit"] == "kg/ha" for candidate in candidates)
    for candidate in candidates:
        if candidate["predicted_yield"] is not None:
            assert candidate["model_reference_year"] == 2022
            assert candidate["model_prediction_period_status"] == "in_training_range"

    assert result["ranking_model"]["model_name"] == "HistGradientBoostingRegressor"
    assert result["ranking_model"]["quality_status"] == "experimental"
    assert result["ranking_model"]["production_approved"] is False
    assert result["ranking_model"]["prediction_period_status"] == "in_training_range"
    assert "not a multi-year average" in result["ranking_model"]["reference_year_policy"]

    assert result["data_provenance"]["dataset_name"] == (
        "apy_weather_integrated_exploratory.csv"
    )
    assert len(result["data_provenance"]["sha256"]) == 64
    assert "not planting recommendations" in " ".join(result["limitations"])
    assert "Yield-based ranking" in result["ranking_methodology"]
    assert "not a guarantee of agronomic suitability" in result["ranking_methodology"]

    comparison = _request(
        application,
        "GET",
        "/api/v1/rankings/crops/comparison",
        params={
            "state": "Andhra Pradesh",
            "district": "Alluri Sitharama Raju",
            "season": "Kharif",
            "through_year_start": 2024,
        },
    )
    assert comparison.status_code == 200
    rice = next(item for item in comparison.json()["crops"] if item["crop"] == "Rice")
    assert rice["historical_median_yield"] == 2987.0
    assert rice["recent_median_yield"] == 2987.0
    assert rice["valid_years"] == [2022, 2023, 2024]
    assert comparison.json()["comparison_group_coverage"] == [
        {
            "year_start": 2022,
            "year_label": "2022-23",
            "valid_observation_count": 5,
            "candidate_count": 5,
            "comparable": True,
        },
        {
            "year_start": 2023,
            "year_label": "2023-24",
            "valid_observation_count": 4,
            "candidate_count": 4,
            "comparable": True,
        },
        {
            "year_start": 2024,
            "year_label": "2024-25",
            "valid_observation_count": 4,
            "candidate_count": 4,
            "comparable": True,
        },
    ]

    trend = _request(
        application,
        "GET",
        "/api/v1/rankings/crops/history/Rice/trend",
        params={
            "state": "Andhra Pradesh",
            "district": "Alluri Sitharama Raju",
            "season": "Kharif",
            "through_year_start": 2024,
        },
    )
    assert trend.status_code == 200
    assert [row["yield_value"] for row in trend.json()["observations"]] == [
        2987.0,
        1762.0,
        3155.0,
    ]

    evidence = _request(
        application,
        "GET",
        "/api/v1/rankings/crops/history/Rice/evidence",
        params={
            "state": "Andhra Pradesh",
            "district": "Alluri Sitharama Raju",
            "season": "Kharif",
            "through_year_start": 2024,
        },
    )
    assert evidence.status_code == 200
    assert evidence.json()["source_observation_count"] >= 3
    assert evidence.json()["valid_observation_count"] == 3


def test_crop_ranking_capability_distinguishes_execution_evidence_and_approval() -> None:
    application = create_app(Settings(database_url=None, apy_data_path=APY_SOURCE))
    response = _request(application, "GET", "/api/v1/capabilities")

    assert response.status_code == 200
    capability = next(
        item
        for item in response.json()["capabilities"]
        if item["name"] == "crop_ranking"
    )
    assert capability["status"] == "enabled"
    assert capability["execution_available"] is True
    assert capability["availability"] == "available"
    assert capability["evidence_quality"] == "varies_by_comparison_group"
    assert capability["production_approved"] is False


def test_api_reports_dataset_loading_failure_as_unavailable(tmp_path: Path) -> None:
    application = create_app(
        Settings(database_url=None, apy_data_path=tmp_path / "missing.csv")
    )
    response = _request(
        application,
        "GET",
        "/api/v1/rankings/crops/options",
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "feature_not_approved"


def test_dataset_used_by_integration_tests_exists() -> None:
    assert APY_SOURCE.is_file()
    sample = pd.read_csv(APY_SOURCE, nrows=1, usecols=["Crop", "Yield"])
    assert set(sample.columns) == {"Crop", "Yield"}
