from typing import cast

from fastapi import Request

from python_integration_service.integrations.vendor_client import VendorClient


def get_vendor_client(request: Request) -> VendorClient:
    return cast(VendorClient, request.app.state.vendor_client)
