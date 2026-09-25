from typing import Annotated
from unittest.mock import MagicMock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from python_integration_service.dependencies import get_vendor_client
from python_integration_service.integrations.vendor_client import VendorClient


def test_get_vendor_client_returns_client_from_app_state() -> None:
    vendor_client = MagicMock()
    request = MagicMock()

    request.app.state.vendor_client = vendor_client

    result = get_vendor_client(request)

    assert result is vendor_client


def test_fastapi_injects_same_vendor_client_from_app_state() -> None:
    expected_client = MagicMock(spec=VendorClient)
    test_app = FastAPI()
    test_app.state.vendor_client = expected_client

    @test_app.get("/test-vendor")
    def test_vendor_endpoint(
        vendor_client: Annotated[
            VendorClient,
            Depends(get_vendor_client),
        ],
    ) -> dict[str, bool]:
        return {"same_instance": vendor_client is expected_client}

    with TestClient(test_app) as client:
        response = client.get("/test-vendor")

    assert response.status_code == 200
    assert response.json() == {"same_instance": True}
