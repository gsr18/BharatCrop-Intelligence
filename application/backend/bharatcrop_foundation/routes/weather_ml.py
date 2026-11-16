from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException, Request, status

from bharatcrop_foundation.models.weather_ml import WeatherMlError, WeatherMlService
from bharatcrop_foundation.schemas import (
    ErrorResponse,
    WeatherMlDistrictForecastRequest,
    WeatherMlDistrictForecastResponse,
    WeatherMlDistrictOptionsResponse,
    WeatherMlForecastRequest,
    WeatherMlForecastResponse,
    WeatherMlStatusResponse,
)

router = APIRouter(prefix="/weather-ml", tags=["weather machine learning"])


def _service(request: Request) -> WeatherMlService:
    return cast(WeatherMlService, request.app.state.weather_ml_service)


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, WeatherMlError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


@router.get(
    "/rainfall-forecast/status",
    response_model=WeatherMlStatusResponse,
    responses={503: {"model": ErrorResponse}},
)
def rainfall_forecast_status(request: Request) -> WeatherMlStatusResponse:
    try:
        return WeatherMlStatusResponse.model_validate(_service(request).status())
    except WeatherMlError as error:
        raise _http_error(error) from error


@router.post(
    "/rainfall-forecast",
    response_model=WeatherMlForecastResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def rainfall_forecast(
    request: Request,
    payload: WeatherMlForecastRequest,
) -> WeatherMlForecastResponse:
    try:
        return WeatherMlForecastResponse.model_validate(
            _service(request).rainfall_forecast(
                latitude=payload.latitude,
                longitude=payload.longitude,
                as_of_date=payload.as_of_date,
                horizons=payload.horizons,
            )
        )
    except (WeatherMlError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/rainfall-forecast/districts",
    response_model=WeatherMlDistrictOptionsResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def rainfall_forecast_district_options(request: Request) -> WeatherMlDistrictOptionsResponse:
    try:
        return WeatherMlDistrictOptionsResponse.model_validate(_service(request).district_options())
    except (WeatherMlError, ValueError) as error:
        raise _http_error(error) from error


@router.post(
    "/rainfall-forecast/district",
    response_model=WeatherMlDistrictForecastResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def rainfall_forecast_district(
    request: Request,
    payload: WeatherMlDistrictForecastRequest,
) -> WeatherMlDistrictForecastResponse:
    try:
        return WeatherMlDistrictForecastResponse.model_validate(
            _service(request).district_forecast(
                state=payload.state,
                district=payload.district,
                horizons=payload.horizons,
            )
        )
    except (WeatherMlError, ValueError) as error:
        raise _http_error(error) from error
