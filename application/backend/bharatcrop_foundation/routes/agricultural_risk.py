from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException, Query, Request, status

from bharatcrop_foundation.models.agricultural_risk import (
    AgriculturalRiskDataError,
    AgriculturalRiskService,
)
from bharatcrop_foundation.models.weather_data import WeatherDataError
from bharatcrop_foundation.schemas import (
    ErrorResponse,
    RiskAnomaliesResponse,
    RiskBenchmarkingResponse,
    RiskCoverageResponse,
    RiskDiversificationResponse,
    RiskIndicatorsResponse,
    RiskInstabilityResponse,
    RiskOptionsResponse,
    RiskOverviewResponse,
)

router = APIRouter(prefix="/risk", tags=["agricultural risk intelligence"])


def _service(request: Request) -> AgriculturalRiskService:
    return cast(AgriculturalRiskService, request.app.state.agricultural_risk_service)


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, (AgriculturalRiskDataError, WeatherDataError)):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)


@router.get(
    "/options",
    response_model=RiskOptionsResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def risk_options(
    request: Request,
    state: str | None = None,
) -> RiskOptionsResponse:
    try:
        return RiskOptionsResponse.model_validate(_service(request).options(state=state))
    except (AgriculturalRiskDataError, WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/overview",
    response_model=RiskOverviewResponse,
    responses={503: {"model": ErrorResponse}},
)
def risk_overview(request: Request) -> RiskOverviewResponse:
    try:
        return RiskOverviewResponse.model_validate(_service(request).overview())
    except (AgriculturalRiskDataError, WeatherDataError) as error:
        raise _http_error(error) from error


def _year_filter(
    year_start: int | None,
    year_end: int | None,
) -> None:
    if (
        year_start is not None
        and year_end is not None
        and year_start > year_end
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)


@router.get(
    "/anomalies",
    response_model=RiskAnomaliesResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def risk_anomalies(
    request: Request,
    state: str,
    district: str,
    crop: str,
    season: str,
    year_start: int | None = Query(default=None, ge=2013, le=2024),
    year_end: int | None = Query(default=None, ge=2013, le=2024),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> RiskAnomaliesResponse:
    _year_filter(year_start, year_end)
    try:
        return RiskAnomaliesResponse.model_validate(
            _service(request).anomalies(
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
    except (AgriculturalRiskDataError, WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/instability",
    response_model=RiskInstabilityResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def risk_instability(
    request: Request,
    state: str,
    district: str,
    crop: str,
    season: str,
    year_start: int | None = Query(default=None, ge=2013, le=2024),
    year_end: int | None = Query(default=None, ge=2013, le=2024),
) -> RiskInstabilityResponse:
    _year_filter(year_start, year_end)
    try:
        return RiskInstabilityResponse.model_validate(
            _service(request).instability(
                state=state,
                district=district,
                crop=crop,
                season=season,
                year_start=year_start,
                year_end=year_end,
            )
        )
    except (AgriculturalRiskDataError, WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/indicators",
    response_model=RiskIndicatorsResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def risk_indicators(
    request: Request,
    state: str,
    district: str,
    crop: str,
    season: str,
    year_start: int | None = Query(default=None, ge=2013, le=2024),
    year_end: int | None = Query(default=None, ge=2013, le=2024),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> RiskIndicatorsResponse:
    _year_filter(year_start, year_end)
    try:
        return RiskIndicatorsResponse.model_validate(
            _service(request).indicators(
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
    except (AgriculturalRiskDataError, WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/diversification",
    response_model=RiskDiversificationResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def risk_diversification(
    request: Request,
    state: str,
    district: str,
    season: str,
    year_start: int = Query(ge=2013, le=2024),
) -> RiskDiversificationResponse:
    try:
        return RiskDiversificationResponse.model_validate(
            _service(request).diversification(
                state=state,
                district=district,
                season=season,
                year_start=year_start,
            )
        )
    except (AgriculturalRiskDataError, WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/benchmarking",
    response_model=RiskBenchmarkingResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def risk_benchmarking(
    request: Request,
    state: str,
    crop: str,
    season: str,
    year_start: int = Query(ge=2013, le=2024),
    through_year_start: int | None = Query(default=None, ge=2013, le=2024),
) -> RiskBenchmarkingResponse:
    try:
        return RiskBenchmarkingResponse.model_validate(
            _service(request).benchmarking(
                state=state,
                crop=crop,
                season=season,
                year_start=year_start,
                through_year_start=through_year_start,
            )
        )
    except (AgriculturalRiskDataError, WeatherDataError, ValueError) as error:
        raise _http_error(error) from error


@router.get(
    "/coverage",
    response_model=RiskCoverageResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def risk_coverage(
    request: Request,
    state: str | None = None,
    district: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> RiskCoverageResponse:
    try:
        return RiskCoverageResponse.model_validate(
            _service(request).coverage(
                state=state,
                district=district,
                page=page,
                page_size=page_size,
            )
        )
    except (AgriculturalRiskDataError, WeatherDataError, ValueError) as error:
        raise _http_error(error) from error
