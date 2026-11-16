import asyncio
from typing import Annotated

import httpx
from fastapi import APIRouter, FastAPI, Query

from bharatcrop_foundation.app import create_app
from bharatcrop_foundation.config import Settings


def _app_with_test_routes() -> FastAPI:
    application = create_app(Settings(database_url=None))
    test_router = APIRouter(prefix="/api/v1")

    @test_router.get("/test-validation")
    def validate_count(count: Annotated[int, Query(ge=1, le=5)]) -> dict[str, int]:
        return {"count": count}

    @test_router.get("/test-unexpected")
    def raise_unexpected_error() -> None:
        raise RuntimeError("sensitive filesystem path")

    application.include_router(test_router)
    return application


async def _get(
    application: FastAPI,
    path: str,
    params: dict[str, str] | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path, params=params)


def test_service_information_is_minimal_and_versioned() -> None:
    response = asyncio.run(_get(create_app(Settings(database_url=None)), "/api/v1/info"))

    assert response.status_code == 200
    assert response.json() == {
        "service": "BharatCrop Intelligence",
        "api_version": "v1",
    }
    assert response.headers["x-request-id"]


def test_validation_error_uses_safe_common_envelope() -> None:
    response = asyncio.run(
        _get(
            _app_with_test_routes(),
            "/api/v1/test-validation",
            params={"count": "not-an-integer"},
        )
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "The request contains invalid values.",
            "details": [{"location": "request", "message": "A request value is invalid."}],
            "request_id": response.headers["x-request-id"],
        }
    }
    assert "input" not in response.text
    assert "not-an-integer" not in response.text


def test_unknown_route_returns_common_not_found_envelope() -> None:
    response = asyncio.run(_get(create_app(Settings(database_url=None)), "/api/v1/not-found"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resource_not_found"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert "filesystem" not in response.text


def test_unexpected_error_is_sanitized() -> None:
    response = asyncio.run(_get(_app_with_test_routes(), "/api/v1/test-unexpected"))

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert response.json()["error"]["message"] == "An unexpected error occurred."
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert "sensitive filesystem path" not in response.text
    assert "Traceback" not in response.text
