from __future__ import annotations

import asyncio
import math
from pathlib import Path

import httpx
import pandas as pd
from fastapi import FastAPI

from bharatcrop_foundation.app import create_app
from bharatcrop_foundation.config import Settings
from bharatcrop_foundation.models.yield_prediction import YieldFeatures

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TRAINING_SOURCE = (
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
    json: dict[str, str | int] | None = None,
) -> httpx.Response:
    async def perform() -> httpx.Response:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.request(method, path, json=json)

    return asyncio.run(perform())


def test_real_artifact_options_and_inference_without_publishing_unitless_yield() -> None:
    application = create_app(Settings(database_url=None))
    options_response = _request(
        application,
        "GET",
        "/api/v1/predictions/yield/options",
    )
    assert options_response.status_code == 200
    options = options_response.json()
    assert options["crops"]
    assert options["seasons"]
    assert options["states"]
    assert options["year_start"] == 2013
    assert options["year_end"] == 2022
    assert options["category_label_basis"] == "model_training_encoder"
    assert options["year_range_type"] == "training_with_extrapolation"
    assert options["target_unit"] == "kg/ha"
    assert options["target_unit_status"] == "verification_pending"
    assert "pending" in options["target_semantics"].lower()
    assert options["target_conversion_applied"] is False
    assert "Ministry of Statistics and Programme Implementation" in options[
        "target_unit_source"
    ]

    service = application.state.yield_prediction_service
    model = service.adapter.load()
    assert tuple(model.feature_names_in_) == (
        "Crop",
        "Season",
        "Crop_Category",
        "State",
        "District",
        "FE_YearStart",
    )
    source = pd.read_csv(
        TRAINING_SOURCE,
        usecols=[
            "State",
            "District",
            "Crop",
            "Season",
            "Crop_Category",
            "Year",
            "Area",
            "Production",
            "Yield",
        ],
        low_memory=False,
    )
    source["FE_YearStart"] = pd.to_numeric(
        source["Year"].astype("string").str.extract(r"^(\d{4})", expand=False),
        errors="coerce",
    )
    measurements = source[["Area", "Production", "Yield"]].apply(
        pd.to_numeric,
        errors="coerce",
    )
    source = source.loc[
        source["Crop_Category"].eq("Individual Crop Candidate")
        & source["Crop"].astype("string").str.casefold().ne("total")
        & source["Season"].astype("string").str.casefold().ne("total")
        & source["FE_YearStart"].between(2013, 2022)
        & measurements["Area"].gt(0)
        & measurements["Production"].gt(0)
        & measurements["Yield"].gt(0)
    ]

    result = None
    for row in source.itertuples(index=False):
        features = YieldFeatures(
            Crop=row.Crop,
            Season=row.Season,
            Crop_Category=row.Crop_Category,
            State=row.State,
            District=row.District,
            FE_YearStart=int(row.FE_YearStart),
        )
        try:
            result = service.predict(features)
            break
        except ValueError:
            continue
    assert result is not None, "A valid, observed training-category fixture must exist."
    assert math.isfinite(result.value)
    assert result.provenance.target_unit == "kg/ha"
    assert result.provenance.target_unit_status == "verification_pending"
    assert result.provenance.model_version == (
        "individual_crop_hgb_location/2013-2022/sha256:dc057a8cbe39adef"
    )
    assert result.provenance.validation_metrics == {}
    assert len(result.provenance.artifact_sha256) == 64

    valid_request: dict[str, str | int] = {
        "crop": features.Crop,
        "season": features.Season,
        "crop_category": features.Crop_Category,
        "state": features.State,
        "district": features.District,
        "year_start": features.FE_YearStart,
    }
    public_response = _request(
        application,
        "POST",
        "/api/v1/predictions/yield",
        json=valid_request,
    )
    assert public_response.status_code == 200
    assert public_response.headers["x-request-id"]
    response_body = public_response.json()
    assert response_body["prediction"] == result.value
    assert response_body["unit"] == "kg/ha"
    assert response_body["quality_status"] == "experimental"
    assert response_body["production_approved"] is False
    assert response_body["model_name"] == "HistGradientBoostingRegressor"
    assert response_body["model_version"] == (
        "individual_crop_hgb_location/2013-2022/sha256:dc057a8cbe39adef"
    )
    assert response_body["model_version_status"] == "recorded"
    assert response_body["data_provenance"]["unit_verification_status"] == (
        "verification_pending"
    )
    assert response_body["training_year_start"] == 2013
    assert response_body["training_year_end"] == 2022
    assert response_body["prediction_period_status"] == "in_training_range"
    assert response_body["data_provenance"]["unit_source_section"] == (
        "4.10.5 Agricultural Productivity"
    )
    assert response_body["data_provenance"]["unit_source_url"].startswith(
        "https://mospi.gov.in/"
    )
    assert response_body["data_provenance"]["numerical_conversion_applied"] is False
    assert "Notebook 06" in response_body["data_provenance"]["target_construction"]
    assert "Area in hectares" in response_body["data_provenance"]["target_definition"]
    assert "Production in tonnes/bales" in response_body["data_provenance"]["target_definition"]
    assert "median" in response_body["data_provenance"]["target_consistency_check"]
    assert response_body["crop"] == features.Crop
    assert response_body["state"] == features.State
    assert response_body["district"] == features.District

    extrapolation = _request(
        application,
        "POST",
        "/api/v1/predictions/yield",
        json={**valid_request, "year_start": 2028},
    )
    assert extrapolation.status_code == 200
    assert extrapolation.json()["prediction_period_status"] == (
        "out_of_training_range_extrapolation"
    )
    assert extrapolation.json()["prediction_year"] == 2028
    assert extrapolation.json()["quality_status"] == "experimental"
    assert any(
        "not a validated" in limitation and "forecast" in limitation
        for limitation in extrapolation.json()["limitations"]
    )

    for field, value in (
        ("crop", "Unsupported crop"),
        ("season", "Unsupported season"),
        ("year_start", 0),
    ):
        invalid_request: dict[str, str | int] = {**valid_request, field: value}
        invalid_response = _request(
            application,
            "POST",
            "/api/v1/predictions/yield",
            json=invalid_request,
        )
        assert invalid_response.status_code == 422
        assert invalid_response.json()["error"]["request_id"] == invalid_response.headers[
            "x-request-id"
        ]
    malformed_request = {key: value for key, value in valid_request.items() if key != "crop"}
    malformed_response = _request(
        application,
        "POST",
        "/api/v1/predictions/yield",
        json=malformed_request,
    )
    assert malformed_response.status_code == 422

    other_state = next(
        candidate
        for candidate in options["states"]
        if candidate != features.State
        and any(
            district not in options["districts_by_state"][features.State]
            for district in options["districts_by_state"][candidate]
        )
    )
    unsupported_district = next(
        district
        for district in options["districts_by_state"][other_state]
        if district not in options["districts_by_state"][features.State]
    )
    unsupported = _request(
        application,
        "POST",
        "/api/v1/predictions/yield",
        json={
            "crop": features.Crop,
            "season": features.Season,
            "crop_category": features.Crop_Category,
            "state": features.State,
            "district": unsupported_district,
            "year_start": features.FE_YearStart,
        },
    )
    assert unsupported.status_code == 422


def test_capability_separates_execution_from_production_approval() -> None:
    application = create_app(Settings(database_url=None))
    response = _request(application, "GET", "/api/v1/capabilities")

    assert response.status_code == 200
    yield_capability = next(
        capability
        for capability in response.json()["capabilities"]
        if capability["name"] == "yield_prediction"
    )
    assert yield_capability["availability"] == "available"
    assert yield_capability["quality_status"] == "experimental"
    assert yield_capability["production_approved"] is False
    assert yield_capability["status"] == "enabled"
    assert "target_unit_unverified" not in yield_capability["reason_codes"]
    assert "model_version_not_recorded" not in yield_capability["reason_codes"]
