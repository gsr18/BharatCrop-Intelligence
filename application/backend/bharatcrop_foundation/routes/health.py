from fastapi import APIRouter, Request, Response, status

from bharatcrop_foundation.schemas import HealthResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
def live(request: Request) -> HealthResponse:
    return HealthResponse(
        status="live",
        request_id=request.state.request_id,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
def ready(request: Request, response: Response) -> ReadinessResponse:
    database = request.app.state.database
    if database.engine is None:
        database_status = "not_configured"
    else:
        database_status = "ready" if database.is_ready() else "unavailable"
    is_ready = database_status == "ready"
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        checks={"database": database_status},
        request_id=request.state.request_id,
    )
