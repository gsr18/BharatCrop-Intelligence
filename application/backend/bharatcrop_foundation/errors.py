from __future__ import annotations

from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from bharatcrop_foundation.schemas import ErrorBody, ErrorDetail, ErrorResponse

HTTP_ERROR_MESSAGES: Mapping[int, tuple[str, str]] = {
    400: ("bad_request", "The request could not be processed."),
    401: ("authentication_required", "Authentication is required."),
    403: ("permission_denied", "The request is not permitted."),
    404: ("resource_not_found", "The requested resource was not found."),
    405: ("method_not_allowed", "The request method is not allowed."),
    409: ("conflict", "The request conflicts with the current resource state."),
    410: ("resource_expired", "The requested resource is no longer available."),
    422: ("validation_error", "The request contains invalid values."),
    413: ("request_too_large", "The request is too large."),
    429: ("rate_limited", "Too many requests."),
    503: ("feature_not_approved", "This capability is not currently available."),
}
GENERIC_HTTP_ERROR = ("request_failed", "The request could not be processed.")


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unavailable"))


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            details=[ErrorDetail(**detail) for detail in details or []],
            request_id=_request_id(request),
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers={"X-Request-ID": _request_id(request)},
    )


async def handle_http_error(request: Request, exception: Exception) -> JSONResponse:
    if not isinstance(exception, StarletteHTTPException):
        return await handle_unexpected_error(request, exception)
    code, message = HTTP_ERROR_MESSAGES.get(exception.status_code, GENERIC_HTTP_ERROR)
    return _error_response(request, exception.status_code, code, message)


async def handle_validation_error(request: Request, exception: Exception) -> JSONResponse:
    if not isinstance(exception, RequestValidationError):
        return await handle_unexpected_error(request, exception)
    details = [
        {"location": "request", "message": "A request value is invalid."}
        for _ in exception.errors()
    ]
    return _error_response(
        request,
        422,
        "validation_error",
        "The request contains invalid values.",
        details,
    )


async def handle_unexpected_error(request: Request, _exception: Exception) -> JSONResponse:
    return _error_response(
        request,
        500,
        "internal_error",
        "An unexpected error occurred.",
    )


def register_error_handlers(application: FastAPI) -> None:
    application.add_exception_handler(StarletteHTTPException, handle_http_error)
    application.add_exception_handler(RequestValidationError, handle_validation_error)
    application.add_exception_handler(Exception, handle_unexpected_error)
