from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException, Query, Request, status

from bharatcrop_foundation.models.weather_data import (
    WeatherDataError,
    WeatherDataService,
)
from bharatcrop_foundation.schemas import (
    ErrorResponse,
    WeatherAnomaliesResponse,
    WeatherClassifierStatusResponse,
    WeatherCoverageResponse,
    WeatherCropContextResponse,
    WeatherOptionsResponse,
    WeatherOverviewResponse,
    WeatherSeriesResponse,
    WeatherTrendsResponse,
)

router = APIRouter(prefix="/weather", tags=["weather intelligence"])


def _service(request: Request) -> WeatherDataService:
    return cast(WeatherDataService, request.app.state.weather_data_service)


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, WeatherDataError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)


@router.get(
    "/options",
    response_model=WeatherOptionsResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def weather_options(
    request: Request,
    state: str | None = None,
) -> WeatherOptionsResponse:
    try:
        return WeatherOptionsResponse.model_validate(_service(request).options(state=state))
    except (WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/overview",
    response_model=WeatherOverviewResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def weather_overview(
    request: Request,
    state: str | None = None,
    district: str | None = None,
    year: int | None = Query(default=None, ge=2013, le=2024),
) -> WeatherOverviewResponse:
    try:
        return WeatherOverviewResponse.model_validate(
            _service(request).overview(state=state, district=district, year=year)
        )
    except (WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/trends",
    response_model=WeatherTrendsResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def weather_trends(
    request: Request,
    metric: str = "tmax_mean_c",
    state: str | None = None,
    district: str | None = None,
    year_start: int | None = Query(default=None, ge=2013, le=2024),
    year_end: int | None = Query(default=None, ge=2013, le=2024),
) -> WeatherTrendsResponse:
    try:
        return WeatherTrendsResponse.model_validate(
            _service(request).trends(
                metric=metric,
                state=state,
                district=district,
                year_start=year_start,
                year_end=year_end,
            )
        )
    except (WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


def _weather_series(
    request: Request,
    metric: str,
    state: str | None,
    district: str | None,
    year_start: int | None,
    year_end: int | None,
    page: int,
    page_size: int,
) -> WeatherSeriesResponse:
    try:
        return WeatherSeriesResponse.model_validate(
            _service(request).series(
                metric=metric,
                state=state,
                district=district,
                year_start=year_start,
                year_end=year_end,
                page=page,
                page_size=page_size,
            )
        )
    except (WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/temperature",
    response_model=WeatherSeriesResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def temperature_history(
    request: Request,
    metric: str = "tmin_mean_c",
    state: str | None = None,
    district: str | None = None,
    year_start: int | None = Query(default=None, ge=2013, le=2024),
    year_end: int | None = Query(default=None, ge=2013, le=2024),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> WeatherSeriesResponse:
    if metric not in {"tmin_mean_c", "tmin_min_c", "tmax_mean_c", "tmax_max_c"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    return _weather_series(
        request, metric, state, district, year_start, year_end, page, page_size
    )


@router.get(
    "/precipitation",
    response_model=WeatherSeriesResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def precipitation_history(
    request: Request,
    metric: str = "precipitation_total_mm",
    state: str | None = None,
    district: str | None = None,
    year_start: int | None = Query(default=None, ge=2013, le=2024),
    year_end: int | None = Query(default=None, ge=2013, le=2024),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> WeatherSeriesResponse:
    if metric not in {
        "precipitation_total_mm",
        "precipitation_mean_mm_day",
        "precipitation_max_mm_day",
    }:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    return _weather_series(
        request, metric, state, district, year_start, year_end, page, page_size
    )


@router.get(
    "/anomalies",
    response_model=WeatherAnomaliesResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def weather_anomalies(
    request: Request,
    metric: str | None = None,
    state: str | None = None,
    district: str | None = None,
    year_start: int | None = Query(default=None, ge=2013, le=2024),
    year_end: int | None = Query(default=None, ge=2013, le=2024),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> WeatherAnomaliesResponse:
    try:
        return WeatherAnomaliesResponse.model_validate(
            _service(request).anomalies(
                metric=metric,
                state=state,
                district=district,
                year_start=year_start,
                year_end=year_end,
                page=page,
                page_size=page_size,
            )
        )
    except (WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/coverage",
    response_model=WeatherCoverageResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def weather_coverage(
    request: Request,
    state: str | None = None,
    district: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> WeatherCoverageResponse:
    try:
        return WeatherCoverageResponse.model_validate(
            _service(request).coverage(
                state=state,
                district=district,
                page=page,
                page_size=page_size,
            )
        )
    except (WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/crop-context",
    response_model=WeatherCropContextResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def weather_crop_context(
    request: Request,
    state: str,
    district: str,
    crop: str | None = None,
    season: str | None = None,
    year_start: int | None = Query(default=None, ge=2013, le=2024),
    year_end: int | None = Query(default=None, ge=2013, le=2024),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> WeatherCropContextResponse:
    try:
        return WeatherCropContextResponse.model_validate(
            _service(request).crop_context(
                state=state,
                district=district,
                crop=crop,
                season=season,
                year_start=year_start,
                year_end=year_end,
                page=page,
                page_size=page_size,
            )
        )
    except (WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/classifier",
    response_model=WeatherClassifierStatusResponse,
    responses={503: {"model": ErrorResponse}},
)
def weather_classifier_status(request: Request) -> WeatherClassifierStatusResponse:
    try:
        return WeatherClassifierStatusResponse.model_validate(
            _service(request).classifier_status()
        )
    except WeatherDataError as error:
        raise _http_error(error) from error
