import pytest
from fastapi.testclient import TestClient

from bharatcrop_foundation.app import create_app
from bharatcrop_foundation.config import Settings


@pytest.fixture
def client() -> TestClient:
    app = create_app(Settings(database_url=None))
    return TestClient(app)
