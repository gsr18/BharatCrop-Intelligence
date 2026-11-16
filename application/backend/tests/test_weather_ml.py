from __future__ import annotations

import asyncio
from datetime import date

import httpx
import pandas as pd
from fastapi import FastAPI

from bharatcrop_foundation.app import create_app
from bharatcrop_foundation.config import Settings
from bharatcrop_foundation.models.weather_ml import WeatherMlService


def _app() -> FastAPI:
    return create_app(Settings(database_url=None))


async def _get(application: FastAPI, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def _post(application: FastAPI, path: str, payload: dict) -> httpx.Response:
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, json=payload)


def test_rainfall_forecast_status_reports_loaded_models_without_live_input() -> None:
    response = asyncio.run(
        _get(_app(), "/api/v1/weather-ml/rainfall-forecast/status")
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task"] == "wi05_rainfall_forecast"
    assert payload["status"] == "awaiting_input_pipeline"
    assert payload["forecast_available"] is False
    assert payload["reason_code"] == "awaiting_daily_weather_input_pipeline"
    assert payload["production_approved"] is False
    assert payload["predictor_count"] == 53
    assert len(payload["horizons"]) == 7
    assert all(row["status"] == "loaded" for row in payload["horizons"])
    assert payload["input"]["latest_available_input_date"] == "2024-12-31"
    assert payload["input"]["provider"] == "none_configured"


def test_rainfall_forecast_request_does_not_emit_predictions_without_inputs() -> None:
    response = asyncio.run(
        _post(
            _app(),
            "/api/v1/weather-ml/rainfall-forecast",
            {"latitude": 20.0, "longitude": 80.0, "horizons": [1, 7]},
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["forecast_available"] is False
    assert payload["reason_code"] == "awaiting_daily_weather_input_pipeline"
    assert [row["horizon"] for row in payload["horizons"]] == [1, 7]
    assert "expected_precipitation_mm_day" not in response.text


def test_rainfall_forecast_rejects_out_of_grid_coordinates() -> None:
    response = asyncio.run(
        _post(
            _app(),
            "/api/v1/weather-ml/rainfall-forecast",
            {"latitude": 40.0, "longitude": 80.0},
        )
    )

    assert response.status_code == 422


def test_predict_feature_row_uses_loaded_wi05_artifacts() -> None:
    settings = Settings(database_url=None)
    service = WeatherMlService(
        settings.weather_ml_feature_spec_path,
        settings.weather_ml_model_dirs,
        settings.weather_ml_dataset_metadata_path,
    )
    service.status()
    row = {name: 0.0 for name in service.feature_predictors}
    row.update({"latitude": 20.0, "longitude": 80.0, "PRECTOTCORR_current": 2.5})

    predictions = service.predict_feature_row(row, as_of_date=date(2024, 12, 31), horizons=(1, 2))
    models, _ = service._load_models()
    frame = pd.DataFrame([row])[service.feature_predictors]

    assert [item["horizon"] for item in predictions] == [1, 2]
    for item in predictions:
        horizon = item["horizon"]
        bundle = models[horizon]
        probabilities = bundle["classifier"].predict_proba(frame)[0]
        classes = [int(value) for value in bundle["classifier"].classes_]
        wet_probability = float(probabilities[classes.index(1)])
        amount = float(bundle["amount_regressor"].predict(frame)[0])
        assert item["wet_probability"] == wet_probability
        assert item["conditional_wet_amount_mm_day"] == amount
        assert item["expected_precipitation_mm_day"] == wet_probability * amount
        assert item["target_date"] == f"2025-01-0{horizon}"


def test_district_options_expose_only_archived_supported_districts() -> None:
    response = asyncio.run(
        _get(_app(), "/api/v1/weather-ml/rainfall-forecast/districts")
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["forecast_origin_date"] == "2024-12-31"
    assert payload["archive_end_date"] == "2024-12-31"
    assert payload["supported_district_count"] > 0
    assert "Mizoram" in payload["states"]
    assert "Hnahthial" in payload["districts_by_state"]["Mizoram"]
    option = next(
        row for row in payload["districts"] if row["district"] == "Hnahthial"
    )
    assert option["intersecting_cell_count"] == 2
    assert option["valid_cell_count"] == 2


def test_district_archive_forecast_aggregates_real_wi05_outputs() -> None:
    response = asyncio.run(
        _post(
            _app(),
            "/api/v1/weather-ml/rainfall-forecast/district",
            {"state": "Mizoram", "district": "Hnahthial"},
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["forecast_available"] is True
    assert payload["forecast_origin_date"] == "2024-12-31"
    assert payload["spatial"]["total_intersecting_cell_count"] == 2
    assert payload["spatial"]["valid_cell_count"] == 2
    assert payload["forecast_dates"] == [
        "2025-01-01",
        "2025-01-02",
        "2025-01-03",
        "2025-01-04",
        "2025-01-05",
        "2025-01-06",
        "2025-01-07",
    ]
    assert len(payload["horizons"]) == 7
    assert "archive ends on 31 December 2024" in payload["notice"]
    for horizon in payload["horizons"]:
        assert horizon["expected_precipitation_mm_day"] >= 0
        assert horizon["expected_precipitation_mm_day"] == horizon["expected_precipitation_mm_day"]
        assert 0 <= horizon["wet_probability"] <= 1
        assert horizon["cell_count"] == 2


def test_district_archive_forecast_supports_single_cell_district() -> None:
    response = asyncio.run(
        _post(
            _app(),
            "/api/v1/weather-ml/rainfall-forecast/district",
            {"state": "Arunachal Pradesh", "district": "Lower Subansiri"},
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["forecast_available"] is True
    assert payload["spatial"]["total_intersecting_cell_count"] == 1
    assert payload["spatial"]["valid_cell_count"] == 1
    assert len(payload["horizons"]) == 7


def test_district_archive_forecast_rejects_unsupported_district() -> None:
    response = asyncio.run(
        _post(
            _app(),
            "/api/v1/weather-ml/rainfall-forecast/district",
            {"state": "Nowhere", "district": "Nowhere"},
        )
    )

    assert response.status_code == 422
