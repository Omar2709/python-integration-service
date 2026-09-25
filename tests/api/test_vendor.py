from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from python_integration_service.api.vendor import router
from python_integration_service.dependencies import get_vendor_client
from python_integration_service.integrations.vendor_client import VendorClient


def test_get_vendor_items_returns_vendor_response() -> None:
    vendor_client = MagicMock(spec=VendorClient)
    vendor_client.get.return_value = {
        "items": [
            {"id": 1, "name": "Item 1"},
        ]
    }

    test_app = FastAPI()
    test_app.include_router(router)

    test_app.dependency_overrides[get_vendor_client] = lambda: vendor_client

    with TestClient(test_app) as client:
        response = client.get("/vendor/items")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": 1, "name": "Item 1"},
        ]
    }

    vendor_client.get.assert_called_once_with("/items")
