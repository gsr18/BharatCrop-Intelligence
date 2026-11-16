"""Phase 2E — separate, versioned endpoints for the experimental future-yield
forecast. This router never touches the served manual HistGradientBoosting
endpoints (``/predictions/yield`` and ``/predictions/yield/options``)."""
from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException, Request, status

from bharatcrop_foundation.models.experimental_yield_forecast import (
    ExperimentalYieldForecastService,
)
from bharatcrop_foundation.models.yield_prediction import (
    ModelArtifactError,
    ModelNotReadyError,
)
from bharatcrop_foundation.schemas import (
    ErrorResponse,
    ExperimentalForecastOptionsResponse,
    ExperimentalForecastRequest,
    ExperimentalForecastResponse,
)

router = APIRouter(tags=["experimental future yield forecast"])


def _service(request: Request) -> ExperimentalYieldForecastService:
    return cast(ExperimentalYieldForecastService, request.app.state.experimental_forecast_service)


@router.get(
    "/predictions/yield/forecast/options",
    response_model=ExperimentalForecastOptionsResponse,
    responses={503: {"model": ErrorResponse}},
)
def experimental_forecast_options(request: Request) -> ExperimentalForecastOptionsResponse:
    try:
        return ExperimentalForecastOptionsResponse.model_validate(_service(request).options())
    except ModelNotReadyError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error
    except ModelArtifactError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error


@router.post(
    "/predictions/yield/forecast",
    response_model=ExperimentalForecastResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def experimental_forecast(
    _request: ExperimentalForecastRequest,
    request: Request,
) -> ExperimentalForecastResponse:
    service = _service(request)
    try:
        result = service.forecast(
            crop=_request.crop,
            season=_request.season,
            state=_request.state,
            district=_request.district,
            horizon=_request.horizon,
        )
    except ModelNotReadyError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error
    except ModelArtifactError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from error

    prov = result.provenance
    return ExperimentalForecastResponse.model_validate(
        {
            "crop": result.crop,
            "season": result.season,
            "state": result.state,
            "district": result.district,
            "horizon": result.horizon,
            "origin_year": result.origin_year,
            "target_year": result.target_year,
            "predicted_yield": result.predicted_yield,
            "unit": result.unit,
            "unit_status": result.unit_status,
            "history_count": result.history_count,
            "eligibility_status": result.eligibility_status,
            "future_projection": result.future_projection,
            "target_year_status": result.target_year_status,
            "experimental_status": result.experimental_status,
            "quality_status": "experimental",
            "production_approved": False,
            "provenance": {
                "model_id": prov.model_id,
                "model_name": prov.model_name,
                "model_version": prov.model_version,
                "strategy": prov.strategy,
                "base_model": prov.base_model,
                "cohort": prov.cohort,
                "artifact_sha256": prov.artifact_sha256,
                "metadata_sha256": prov.metadata_sha256,
                "training_cutoff_year": prov.training_cutoff_year,
                "latest_observation_year": prov.latest_observation_year,
                "reference_year": prov.reference_year,
                "target": prov.target,
                "target_unit": prov.target_unit,
                "target_unit_status": prov.target_unit_status,
                "target_unit_source": prov.target_unit_source,
                "target_unit_source_url": prov.target_unit_source_url,
                "design_width": prov.design_width,
                "numeric_features": list(prov.numeric_features),
                "research_expanding_window_mae": dict(
                    prov.research_expanding_window_mae
                ),
                "research_expanding_window_r2": dict(
                    prov.research_expanding_window_r2
                ),
            },
            "limitations": list(result.limitations),
            "warnings": list(result.warnings),
        }
    )
