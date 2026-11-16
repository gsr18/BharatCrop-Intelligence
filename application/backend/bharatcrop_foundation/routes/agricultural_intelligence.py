from typing import cast

from fastapi import APIRouter, HTTPException, Query, Request, status

from bharatcrop_foundation.models.apy_data import (
    DATASET_LIMITATIONS,
    APYDataError,
    APYDataService,
)
from bharatcrop_foundation.models.yield_prediction import (
    ModelArtifactError,
    ModelNotReadyError,
    YieldFeatures,
)
from bharatcrop_foundation.schemas import (
    CropComparisonResponse,
    CropEvidenceResponse,
    CropRankingOptionsResponse,
    CropRankingRequest,
    CropRankingResponse,
    CropTrendResponse,
    ErrorResponse,
    YieldDataProvenance,
    YieldOptionsResponse,
    YieldPredictionRequest,
    YieldPredictionResponse,
)

router = APIRouter(tags=["agricultural intelligence"])


def _apy_service(request: Request) -> APYDataService:
    return cast(APYDataService, request.app.state.apy_data_service)


@router.get(
    "/predictions/yield/options",
    response_model=YieldOptionsResponse,
    responses={503: {"model": ErrorResponse}},
)
def yield_options(request: Request) -> YieldOptionsResponse:
    try:
        return YieldOptionsResponse.model_validate(
            request.app.state.yield_prediction_service.options()
        )
    except ModelArtifactError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error


@router.post(
    "/predictions/yield",
    response_model=YieldPredictionResponse,
    responses={
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def predict_yield(
    _request: YieldPredictionRequest,
    request: Request,
) -> YieldPredictionResponse:
    service = request.app.state.yield_prediction_service
    features = YieldFeatures(
        Crop=_request.crop,
        Season=_request.season,
        Crop_Category=_request.crop_category,
        State=_request.state,
        District=_request.district,
        FE_YearStart=_request.year_start,
    )
    try:
        prediction = service.predict(features)
    except ModelNotReadyError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error
    except ModelArtifactError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from error
    provenance = prediction.provenance
    return YieldPredictionResponse(
        crop=_request.crop,
        season=_request.season,
        crop_category=_request.crop_category,
        state=_request.state,
        district=_request.district,
        prediction_year=_request.year_start,
        prediction_period_status=prediction.prediction_period_status,
        prediction=prediction.value,
        target=provenance.target,
        unit=provenance.target_unit,
        model_name=provenance.model_name,
        model_version=provenance.model_version,
        model_version_status=(
            "recorded" if provenance.model_version else "not_recorded"
        ),
        artifact_sha256=provenance.artifact_sha256,
        training_year_start=provenance.training_year_start,
        training_year_end=provenance.training_year_end,
        quality_status="experimental",
        production_approved=False,
        data_provenance=YieldDataProvenance(
            dataset_source=(
                "Agricultural Production Statistics (APY), Ministry of Agriculture "
                "and Farmers' Welfare; state-supplied records."
            ),
            target_field=provenance.target,
            target_definition=(
                "MoSPI documents Area in hectares, Production in tonnes/bales, and "
                "Yield in kilograms per hectare (kg/ha)."
            ),
            target_construction=provenance.target_construction,
            target_consistency_check=provenance.target_consistency_check,
            unit_source=provenance.target_unit_source,
            unit_source_url=provenance.target_unit_source_url,
            unit_source_section="4.10.5 Agricultural Productivity",
            unit_verification_status=provenance.target_unit_status,
            numerical_conversion_applied=provenance.target_conversion_applied,
        ),
        limitations=list(prediction.limitations),
    )


@router.post(
    "/rankings/crops",
    response_model=CropRankingResponse,
    responses={
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def rank_crops(
    _request: CropRankingRequest,
    request: Request,
) -> CropRankingResponse:
    try:
        result = _apy_service(request).rank(
            state=_request.state,
            district=_request.district,
            season=_request.season,
            top_n=_request.top_n,
            ranking_basis=_request.ranking_basis,
        )
    except APYDataError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from error
    return CropRankingResponse.model_validate(result)


@router.get(
    "/rankings/crops/options",
    response_model=CropRankingOptionsResponse,
    responses={
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def crop_ranking_options(
    request: Request,
    state: str | None = None,
    district: str | None = None,
    season: str | None = None,
    year_start: int | None = Query(default=None, ge=1, le=9999),
) -> CropRankingOptionsResponse:
    try:
        options = _apy_service(request).options(
            state=state,
            district=district,
            season=season,
            year_start=year_start,
        )
    except APYDataError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from error
    return CropRankingOptionsResponse.model_validate(options)


@router.get(
    "/rankings/crops/comparison",
    response_model=CropComparisonResponse,
    responses={
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def crop_comparison(
    request: Request,
    state: str,
    district: str,
    season: str,
    through_year_start: int | None = Query(default=None, ge=1, le=9999),
) -> CropComparisonResponse:
    service = _apy_service(request)
    try:
        year = through_year_start if through_year_start is not None else service.years[-1]
        crops = service.comparison(
            state=state,
            district=district,
            season=season,
            through_year=year,
        )
        coverage = service.comparison_group_coverage(
            state=state,
            district=district,
            season=season,
            through_year=year,
        )
    except APYDataError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error
    except (IndexError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from error
    if not crops:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    return CropComparisonResponse.model_validate(
        {
            "state": state,
            "district": district,
            "season": season,
            "through_year_start": year,
            "crops": crops,
            "comparison_group_coverage": coverage,
            "data_provenance": service.provenance,
            "limitations": list(DATASET_LIMITATIONS),
        }
    )


@router.get(
    "/rankings/crops/history/{crop}/trend",
    response_model=CropTrendResponse,
    responses={
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def crop_trend(
    crop: str,
    request: Request,
    state: str,
    district: str,
    season: str,
    through_year_start: int | None = Query(default=None, ge=1, le=9999),
) -> CropTrendResponse:
    service = _apy_service(request)
    try:
        year = through_year_start if through_year_start is not None else service.years[-1]
        summary, observations = service.trends(
            state=state,
            district=district,
            season=season,
            crop=crop,
            through_year=year,
        )
    except APYDataError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error
    except (IndexError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from error
    return CropTrendResponse.model_validate(
        {
            "state": state,
            "district": district,
            "season": season,
            "through_year_start": year,
            "statistics": summary,
            "observations": observations,
            "data_provenance": service.provenance,
            "limitations": list(DATASET_LIMITATIONS),
        }
    )


@router.get(
    "/rankings/crops/history/{crop}/evidence",
    response_model=CropEvidenceResponse,
    responses={
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def crop_evidence(
    crop: str,
    request: Request,
    state: str,
    district: str,
    season: str,
    through_year_start: int | None = Query(default=None, ge=1, le=9999),
) -> CropEvidenceResponse:
    service = _apy_service(request)
    try:
        year = through_year_start if through_year_start is not None else service.years[-1]
        result = service.evidence(
            state=state,
            district=district,
            season=season,
            crop=crop,
            through_year=year,
        )
    except APYDataError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error
    except (IndexError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from error
    return CropEvidenceResponse(
        state=state,
        district=district,
        season=season,
        through_year_start=year,
        **result,
    )
