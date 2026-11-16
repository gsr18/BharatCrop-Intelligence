from typing import cast

from fastapi import APIRouter, HTTPException, Request, status

from bharatcrop_foundation.models.weather_agriculture import (
    WeatherAgricultureDataError,
    WeatherAgricultureService,
)
from bharatcrop_foundation.schemas import (
    CropRegionEvidenceResponse,
    WeatherAgricultureOptionsResponse,
    WeatherAgricultureRequest,
)

router = APIRouter(prefix="/weather-agriculture", tags=["weather-agriculture intelligence"])


def _service(request: Request) -> WeatherAgricultureService:
    return cast(WeatherAgricultureService, request.app.state.weather_agriculture_service)


@router.get("/options", response_model=WeatherAgricultureOptionsResponse)
def weather_agriculture_options(request: Request) -> WeatherAgricultureOptionsResponse:
    try:
        return WeatherAgricultureOptionsResponse.model_validate(_service(request).options())
    except WeatherAgricultureDataError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error


@router.post("/regions", response_model=CropRegionEvidenceResponse)
def rank_crop_regions(
    body: WeatherAgricultureRequest,
    request: Request,
) -> CropRegionEvidenceResponse:
    try:
        result = _service(request).rank(
            crop=body.crop,
            season=body.season,
            state=body.state,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from error
    except WeatherAgricultureDataError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from error
    return CropRegionEvidenceResponse.model_validate(result)
