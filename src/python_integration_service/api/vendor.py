from typing import Annotated

from fastapi import APIRouter, Depends

from python_integration_service.api.schemas import ErrorResponse
from python_integration_service.dependencies import get_vendor_client
from python_integration_service.integrations.vendor_client import VendorClient

router = APIRouter(
    prefix="/vendor",
    tags=["vendor"],
)


@router.get(
    "/items",
    responses={
        502: {
            "model": ErrorResponse,
            "description": "Upstream integration failure.",
        },
        503: {
            "model": ErrorResponse,
            "description": "Upstream service temporarily unavailable.",
        },
        504: {
            "model": ErrorResponse,
            "description": "Upstream service timeout.",
        },
    },
)
def get_vendor_items(
    vendor_client: Annotated[
        VendorClient,
        Depends(get_vendor_client),
    ],
) -> dict:
    return vendor_client.get("/items")
