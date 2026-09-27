from typing import Annotated

from fastapi import APIRouter, Depends, Query

from python_integration_service.api.schemas import (
    ErrorResponse,
    ItemsPageResponse,
)
from python_integration_service.dependencies import get_vendor_client
from python_integration_service.integrations.vendor_client import VendorClient
from python_integration_service.transformers.vendor import (
    transform_vendor_items_page,
)

router = APIRouter(
    prefix="/vendor",
    tags=["vendor"],
)


@router.get(
    "/items",
    response_model=ItemsPageResponse,
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
    page: Annotated[int, Query(ge=1)] = 1,
) -> ItemsPageResponse:
    vendor_page = vendor_client.get_items_page(page=page)

    return transform_vendor_items_page(vendor_page)
