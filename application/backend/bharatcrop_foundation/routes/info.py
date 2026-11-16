from fastapi import APIRouter, Request

from bharatcrop_foundation.schemas import ServiceInfo

router = APIRouter(tags=["service"])


@router.get("/info", response_model=ServiceInfo)
def get_service_info(request: Request) -> ServiceInfo:
    settings = request.app.state.settings
    return ServiceInfo(
        service=settings.service_name,
        api_version=settings.api_version,
    )
