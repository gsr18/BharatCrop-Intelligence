from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pandas as pd
import pytest
from fastapi import FastAPI

from bharatcrop_foundation.app import create_app
from bharatcrop_foundation.config import PROJECT_ROOT, Settings

APY_WEATHER_SOURCE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "weather_regional"
    / "apy_weather_integrated_exploratory.csv"
)
RISK_ARTIFACTS = PROJECT_ROOT / "models" / "agricultural_risk_intelligence"
RISK_OBSERVATIONS = RISK_ARTIFACTS / "yield_risk_indicators.csv"
RISK_SUMMARIES = RISK_ARTIFACTS / "district_crop_risk_summary.csv"


def _request(
    application: FastAPI,
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
            return await client.get(path, params=params)

    return asyncio.run(perform())


def test_real_options_and_overview_match_notebook_20_outputs() -> None:
    application = create_app(Settings(database_url=None))
    options = _request(application, "/api/v1/risk/options")
    assert options.status_code == 200
    option_data = options.json()
    assert len(option_data["crops"]) == 13
    assert "Rice" in option_data["crops"]
    assert "Cereals" not in option_data["crops"]
    assert option_data["seasons"] == ["Kharif", "Rabi", "Summer"]
    assert option_data["years"] == list(range(2013, 2025))
    assert option_data["methodology"]["composite_score"] == (
        "Not defined by Notebook 20."
    )
    assert "C:\\Users" not in str(option_data["dataset_provenance"])

    scoped = _request(
        application,
        "/api/v1/risk/options",
        params={"state": "Andhra Pradesh"},
    )
    assert scoped.status_code == 200
    assert "Anakapalli" in scoped.json()["districts"]
    assert "Nicobars" not in scoped.json()["districts"]

    overview = _request(application, "/api/v1/risk/overview")
    assert overview.status_code == 200
    result = overview.json()
    assert result["prepared_observation_count"] == 90893
    assert result["observations_with_historical_baseline"] == 69693
    assert result["observations_without_sufficient_history"] == 21200
    assert result["district_crop_season_group_count"] == 9236
    assert result["indicator_counts"] == {
        "Within Historical Range": 37772,
        "Above Historical Range": 18926,
        "Moderate Concern": 6968,
        "High Concern": 5877,
        "Extreme Deviation - Review Data": 150,
    }
    assert result["weather_context"]["available_observations"] == 60001
    assert result["weather_context"]["unavailable_observations"] == 9692
    assert result["weather_context"]["weather_changes_yield_indicator"] is False


def test_real_yield_anomaly_matches_notebook_20_saved_observation() -> None:
    application = create_app(Settings(database_url=None))
    response = _request(
        application,
        "/api/v1/risk/anomalies",
        params={
            "state": "Andaman And Nicobar Islands",
            "district": "South Andamans",
            "crop": "Urad",
            "season": "Rabi",
            "year_start": 2023,
            "year_end": 2023,
        },
    )
    assert response.status_code == 200
    record = response.json()["records"][0]

    saved = pd.read_csv(RISK_OBSERVATIONS)
    notebook_row = saved.loc[
        saved["State"].eq("Andaman And Nicobar Islands")
        & saved["District"].eq("South Andamans")
        & saved["Crop"].eq("Urad")
        & saved["Season"].eq("Rabi")
        & saved["start_year"].eq(2023)
    ].iloc[0]
    assert record["yield_value"] == notebook_row["Yield"] == 385540.0
    assert record["historical_median_yield"] == notebook_row[
        "historical_median_yield"
    ] == 7.0
    assert record["historical_observation_count"] == notebook_row[
        "historical_observation_count"
    ] == 3
    assert record["yield_to_baseline_ratio"] == pytest.approx(
        notebook_row["yield_to_baseline_ratio"]
    )
    assert record["risk_indicator"] == notebook_row["yield_risk_indicator"]
    assert record["baseline_observations"] == [
        {
            "year_start": 2020,
            "agricultural_year": "2020-21",
            "yield_value": 7.0,
        },
        {
            "year_start": 2021,
            "agricultural_year": "2021-22",
            "yield_value": 7.0,
        },
        {
            "year_start": 2022,
            "agricultural_year": "2022-23",
            "yield_value": 492.0,
        },
    ]

    saved_summary = pd.read_csv(RISK_SUMMARIES)
    group = saved_summary.loc[
        saved_summary["State"].eq("Andaman And Nicobar Islands")
        & saved_summary["District"].eq("South Andamans")
        & saved_summary["Crop"].eq("Urad")
        & saved_summary["Season"].eq("Rabi")
    ].iloc[0]
    high_concern_years = sorted(
        int(year)
        for year in saved.loc[
            saved["State"].eq("Andaman And Nicobar Islands")
            & saved["District"].eq("South Andamans")
            & saved["Crop"].eq("Urad")
            & saved["Season"].eq("Rabi")
            & saved["yield_risk_indicator"].eq("High Concern"),
            "start_year",
        ].unique()
    )
    indicators = _request(
        application,
        "/api/v1/risk/indicators",
        params={
            "state": "Andaman And Nicobar Islands",
            "district": "South Andamans",
            "crop": "Urad",
            "season": "Rabi",
        },
    )
    assert indicators.status_code == 200
    summary = indicators.json()["historical_pattern_summary"]
    assert summary["observation_count"] == group["observations"]
    assert summary["high_concern_count"] == group["high_concern_count"]
    assert summary["moderate_concern_count"] == group["moderate_concern_count"]
    assert summary["high_concern_years"] == high_concern_years
    assert summary["persistence_indicator"] == group["persistence_indicator"]


def test_real_weather_context_keeps_proxy_and_mapping_quality_separate() -> None:
    application = create_app(Settings(database_url=None))
    response = _request(
        application,
        "/api/v1/risk/indicators",
        params={
            "state": "Andhra Pradesh",
            "district": "Anakapalli",
            "crop": "Rice",
            "season": "Kharif",
            "year_start": 2024,
            "year_end": 2024,
        },
    )
    assert response.status_code == 200
    record = response.json()["records"][0]
    context = record["weather_context"]
    assert record["yield_value"] == 3164.0
    assert context["available"] is True
    assert context["calendar_year"] == 2024
    assert context["alignment_method"] == "STARTING_CALENDAR_YEAR_PROXY"
    assert context["full_season_alignment_verified"] is False
    assert context["weather_values"]["precipitation_total_mm"] == 1389.61
    assert context["nearest_grid_distance_km"] is not None
    assert context["dataset_provenance"]["dataset_name"] == (
        "district_weather_annual_cleaned_flagged_2013_2024.csv"
    )
    assert context["apy_weather_integration_provenance"]["dataset_name"] == (
        "apy_weather_integrated_exploratory.csv"
    )

    missing = _request(
        application,
        "/api/v1/risk/indicators",
        params={
            "state": "Andhra Pradesh",
            "district": "Alluri Sitharama Raju",
            "crop": "Rice",
            "season": "Kharif",
            "year_start": 2024,
            "year_end": 2024,
        },
    )
    assert missing.status_code == 200
    missing_record = missing.json()["records"][0]
    assert missing_record["weather_context"]["available"] is False
    assert missing_record["weather_context"]["weather_values"]["tmax_mean_c"] is None
    assert missing_record["risk_indicator"] in {
        "High Concern",
        "Moderate Concern",
        "Within Historical Range",
        "Above Historical Range",
        "Extreme Deviation - Review Data",
        "Insufficient History",
    }


def test_real_instability_diversification_and_benchmarking_are_data_backed() -> None:
    application = create_app(Settings(database_url=None))
    source = pd.read_csv(
        APY_WEATHER_SOURCE,
        usecols=[
            "State",
            "District",
            "Crop",
            "Season",
            "Crop_Category",
            "start_year",
            "Area",
            "Yield",
        ],
    )
    selected_yields = source.loc[
        source["State"].eq("Andhra Pradesh")
        & source["District"].eq("Anakapalli")
        & source["Crop"].eq("Rice")
        & source["Season"].eq("Kharif")
        & source["Crop_Category"].eq("Individual Crop Candidate")
        & source["start_year"].between(2022, 2024)
        & source["Yield"].gt(0),
        "Yield",
    ]
    instability = _request(
        application,
        "/api/v1/risk/instability",
        params={
            "state": "Andhra Pradesh",
            "district": "Anakapalli",
            "crop": "Rice",
            "season": "Kharif",
            "year_start": 2022,
            "year_end": 2024,
        },
    )
    assert instability.status_code == 200
    summary = instability.json()
    assert summary["valid_observation_count"] == len(selected_yields) == 3
    assert summary["mean_yield"] == pytest.approx(selected_yields.mean())
    assert summary["median_yield"] == pytest.approx(selected_yields.median())
    assert summary["sample_standard_deviation"] == pytest.approx(
        selected_yields.std(ddof=1)
    )
    assert summary["coefficient_of_variation_pct"] == pytest.approx(
        selected_yields.std(ddof=1) / selected_yields.mean() * 100
    )

    diversity_source = source.loc[
        source["State"].eq("Andhra Pradesh")
        & source["District"].eq("Anakapalli")
        & source["Season"].eq("Kharif")
        & source["start_year"].eq(2024)
        & source["Crop_Category"].eq("Individual Crop Candidate")
    ].copy()
    area = pd.to_numeric(diversity_source["Area"], errors="coerce")
    valid_area = area.loc[area.gt(0)]
    expected_shares = (
        diversity_source.loc[valid_area.index]
        .assign(_area=valid_area)
        .groupby("Crop")["_area"]
        .sum()
        .div(valid_area.sum())
    )
    diversification = _request(
        application,
        "/api/v1/risk/diversification",
        params={
            "state": "Andhra Pradesh",
            "district": "Anakapalli",
            "season": "Kharif",
            "year_start": 2024,
        },
    )
    assert diversification.status_code == 200
    diversity = diversification.json()
    assert diversity["herfindahl_hirschman_index"] == pytest.approx(
        float((expected_shares**2).sum())
    )
    assert diversity["agricultural_year"] == "2024-25"
    assert diversity["area_unit"] == "ha"
    assert all(crop["crop"] != "All Crops" for crop in diversity["crop_area_shares"])

    benchmark = _request(
        application,
        "/api/v1/risk/benchmarking",
        params={
            "state": "Andhra Pradesh",
            "crop": "Rice",
            "season": "Kharif",
            "year_start": 2024,
            "through_year_start": 2024,
        },
    )
    assert benchmark.status_code == 200
    bench = benchmark.json()
    expected_district_count = source.loc[
        source["State"].eq("Andhra Pradesh")
        & source["Crop"].eq("Rice")
        & source["Season"].eq("Kharif")
        & source["Crop_Category"].eq("Individual Crop Candidate")
        & source["start_year"].eq(2024)
        & source["Yield"].gt(0),
        "District",
    ].nunique()
    assert bench["district_count"] == expected_district_count
    assert bench["districts_ranked"] is False
    assert next(
        district for district in bench["districts"]
        if district["district"] == "Anakapalli"
    )["current_year_yield"] == 3164.0


def test_risk_validation_coverage_and_capability_contracts() -> None:
    application = create_app(Settings(database_url=None))
    invalid_season = _request(
        application,
        "/api/v1/risk/anomalies",
        params={
            "state": "Andhra Pradesh",
            "district": "Anakapalli",
            "crop": "Rice",
            "season": "Total",
        },
    )
    assert invalid_season.status_code == 422
    assert invalid_season.headers["x-request-id"]
    assert invalid_season.json()["error"]["request_id"] == (
        invalid_season.headers["x-request-id"]
    )

    no_state = _request(
        application,
        "/api/v1/risk/coverage",
        params={"district": "Anakapalli"},
    )
    assert no_state.status_code == 422

    coverage = _request(
        application,
        "/api/v1/risk/coverage",
        params={"state": "Andhra Pradesh", "page_size": 1},
    )
    assert coverage.status_code == 200
    assert coverage.json()["total_locations"] > 1
    assert len(coverage.json()["locations"]) == 1

    capabilities = _request(application, "/api/v1/capabilities")
    assert capabilities.status_code == 200
    by_name = {
        item["name"]: item for item in capabilities.json()["capabilities"]
    }
    for name in (
        "agricultural_risk_indicators",
        "agricultural_yield_anomalies",
        "yield_instability_analysis",
        "crop_diversification",
        "district_benchmarking",
    ):
        assert by_name[name]["execution_available"] is True
        assert by_name[name]["production_approved"] is False
    assert by_name["composite_agricultural_risk_score"]["execution_available"] is False
    assert by_name["composite_agricultural_risk_score"]["reason_code"] == (
        "notebook_20_does_not_define_composite_formula"
    )

    paths = application.openapi()["paths"]
    for route in (
        "/api/v1/risk/options",
        "/api/v1/risk/overview",
        "/api/v1/risk/anomalies",
        "/api/v1/risk/instability",
        "/api/v1/risk/indicators",
        "/api/v1/risk/diversification",
        "/api/v1/risk/benchmarking",
        "/api/v1/risk/coverage",
    ):
        assert route in paths


def test_missing_risk_source_or_research_metadata_is_unavailable(
    tmp_path: Path,
) -> None:
    missing_dataset = create_app(
        Settings(
            database_url=None,
            weather_integration_path=tmp_path / "missing-integration.csv",
            weather_integration_summary_path=tmp_path / "missing-summary.csv",
        )
    )
    unavailable_data = _request(missing_dataset, "/api/v1/risk/options")
    assert unavailable_data.status_code == 503
    assert unavailable_data.json()["error"]["code"] == "feature_not_approved"

    missing_metadata = create_app(
        Settings(
            database_url=None,
            agricultural_risk_metadata_path=tmp_path / "missing-risk-metadata.json",
        )
    )
    unavailable_metadata = _request(missing_metadata, "/api/v1/risk/overview")
    assert unavailable_metadata.status_code == 503
    assert unavailable_metadata.json()["error"]["code"] == "feature_not_approved"
