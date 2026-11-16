import asyncio

import httpx
import pytest

from bharatcrop_foundation.app import create_app
from bharatcrop_foundation.config import Settings, load_settings
from bharatcrop_foundation.database import Database


def _client_request(path: str) -> httpx.Response:
    application = create_app(Settings(database_url=None))

    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.get(path)

    return asyncio.run(request())


def test_liveness_is_independent_of_database_configuration() -> None:
    response = _client_request("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "live"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_readiness_discloses_only_coarse_unconfigured_state() -> None:
    response = _client_request("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"] == {"database": "not_configured"}
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "DATABASE_URL" not in response.text


def test_readiness_sanitizes_database_connection_failure() -> None:
    application = create_app(
        Settings(
            database_url="postgresql+psycopg://user:secret@127.0.0.1:1/testdb",
        )
    )

    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.get("/health/ready")

    response = asyncio.run(request())

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "unavailable"}
    assert "secret" not in response.text
    assert "127.0.0.1" not in response.text


def test_capabilities_fail_closed_for_unverified_features() -> None:
    response = _client_request("/api/v1/capabilities")

    assert response.status_code == 200
    statuses = {item["name"]: item["status"] for item in response.json()["capabilities"]}
    assert statuses
    assert statuses["yield_prediction"] == "enabled"
    assert statuses["crop_ranking"] == "enabled"
    assert statuses["weather_insights"] == "enabled"
    assert statuses["crop_weather_context"] == "enabled"
    assert statuses["low_yield_classifier"] == "disabled"
    assert statuses["agricultural_risk_indicators"] == "enabled"
    assert statuses["agricultural_yield_anomalies"] == "enabled"
    assert statuses["yield_instability_analysis"] == "enabled"
    assert statuses["crop_diversification"] == "enabled"
    assert statuses["district_benchmarking"] == "enabled"
    assert statuses["composite_agricultural_risk_score"] == "disabled"
    assert statuses["global_explainability"] == "enabled"
    assert statuses["local_explainability"] == "disabled"
    assert statuses["prediction_uncertainty"] == "disabled"
    assert statuses["yield_scenarios"] == "enabled"
    assert statuses["model_insights"] == "enabled"
    assert statuses["grounded_assistant"] == "disabled"
    assert all(
        status == "disabled"
        for name, status in statuses.items()
        if name
        not in {
            "yield_prediction",
            "crop_ranking",
            "weather_insights",
            "crop_weather_context",
            "agricultural_risk_indicators",
            "agricultural_yield_anomalies",
            "yield_instability_analysis",
            "crop_diversification",
            "district_benchmarking",
            "global_explainability",
            "yield_scenarios",
            "model_insights",
        }
    )
    assert {
        "yield_prediction",
        "crop_ranking",
        "weather_insights",
        "crop_weather_context",
        "low_yield_classifier",
        "agricultural_risk_indicators",
        "agricultural_yield_anomalies",
        "yield_instability_analysis",
        "crop_diversification",
        "district_benchmarking",
        "composite_agricultural_risk_score",
        "global_explainability",
        "local_explainability",
        "prediction_uncertainty",
        "yield_scenarios",
        "model_insights",
        "grounded_assistant",
        "mandi_prices",
        "farmer_data",
        "expert_workflows",
        "data_export_and_deletion",
    } <= statuses.keys()
    yield_capability = next(
        item for item in response.json()["capabilities"] if item["name"] == "yield_prediction"
    )
    assert "target_unit_unverified" not in yield_capability["reason_codes"]
    assert "artifact_runtime_compatibility_unverified" not in yield_capability["reason_codes"]
    assert "model_version_not_recorded" not in yield_capability["reason_codes"]
    assert yield_capability["availability"] == "available"
    assert yield_capability["execution_available"] is True
    assert yield_capability["quality_status"] == "experimental"
    assert yield_capability["production_approved"] is False
    ranking_capability = next(
        item for item in response.json()["capabilities"] if item["name"] == "crop_ranking"
    )
    assert ranking_capability["execution_available"] is True
    assert ranking_capability["evidence_quality"] == "varies_by_comparison_group"
    assert ranking_capability["production_approved"] is False
    model_insights_capability = next(
        item for item in response.json()["capabilities"] if item["name"] == "model_insights"
    )
    assert model_insights_capability["status"] == "enabled"
    assert model_insights_capability["execution_available"] is True
    assert model_insights_capability["evidence_quality"] == "notebook_22_model_registry"
    assert model_insights_capability["production_approved"] is False
    assistant_cap = next(
        item for item in response.json()["capabilities"] if item["name"] == "grounded_assistant"
    )
    assert assistant_cap["status"] == "disabled"
    assert assistant_cap["reason_code"] == "provider_credentials_unconfigured"


def test_app_creation_does_not_load_serialized_model() -> None:
    application = create_app(Settings(database_url=None))

    assert application.state.yield_prediction_service.adapter._model is None


def test_openapi_documents_only_registered_routes() -> None:
    response = _client_request("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/info" in paths
    assert "/api/v1/capabilities" in paths
    assert "/health/live" in paths
    assert "/health/ready" in paths
    assert "/api/v1/predictions/yield" in paths
    assert "/api/v1/rankings/crops" in paths
    assert "/api/v1/rankings/crops/options" in paths
    assert "/api/v1/rankings/crops/comparison" in paths
    assert "/api/v1/rankings/crops/history/{crop}/trend" in paths
    assert "/api/v1/rankings/crops/history/{crop}/evidence" in paths
    assert "/api/v1/weather/options" in paths
    assert "/api/v1/weather/overview" in paths
    assert "/api/v1/weather/trends" in paths
    assert "/api/v1/weather/temperature" in paths
    assert "/api/v1/weather/precipitation" in paths
    assert "/api/v1/weather/anomalies" in paths
    assert "/api/v1/weather/coverage" in paths
    assert "/api/v1/weather/crop-context" in paths
    assert "/api/v1/weather/classifier" in paths
    assert "/api/v1/risk/options" in paths
    assert "/api/v1/risk/overview" in paths
    assert "/api/v1/risk/anomalies" in paths
    assert "/api/v1/risk/instability" in paths
    assert "/api/v1/risk/indicators" in paths
    assert "/api/v1/risk/diversification" in paths
    assert "/api/v1/risk/benchmarking" in paths
    assert "/api/v1/risk/coverage" in paths
    assert "/api/v1/model-insights/portfolio" in paths
    assert "/api/v1/model-insights/models" in paths
    assert "/api/v1/model-insights/governance" in paths
    assert "/api/v1/assistant/chat" in paths
    assert "/api/v1/assistant/status" in paths
    assert "/api/v1/assistant/suggestions" in paths
    assert "503" in response.json()["paths"]["/api/v1/predictions/yield"]["post"]["responses"]
    assert "/api/v1/predictions/yield/options" in paths


def test_invalid_or_total_season_request_is_rejected_before_not_ready() -> None:
    application = create_app(Settings(database_url=None))

    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.post(
                "/api/v1/predictions/yield",
                json={
                    "crop": "Rice",
                    "season": "Total",
                    "crop_category": "Individual Crop Candidate",
                    "state": "Unknown state",
                    "district": "Unknown district",
                    "year_start": 2020,
                },
            )

    response = asyncio.run(request())

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "Total" not in response.text


def test_database_without_configuration_is_not_ready() -> None:
    assert Database(database_url=None).is_ready() is False


def test_database_configuration_rejects_non_postgresql_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///local.db")

    with pytest.raises(ValueError, match="must use PostgreSQL") as error:
        load_settings()

    assert "local.db" not in str(error.value)
