from python_integration_service.api.schemas import (
    ItemResponse,
    ItemsPageResponse,
)
from python_integration_service.integrations.vendor_schemas import (
    ItemsPage,
    VendorItem,
)
from python_integration_service.mappers.vendor import (
    map_vendor_item,
    map_vendor_items_page,
)
from python_integration_service.validators.vendor import (
    validate_vendor_item,
    validate_vendor_items_page,
)


def transform_vendor_item(item: VendorItem) -> ItemResponse:
    validate_vendor_item(item)

    return map_vendor_item(item)


def transform_vendor_items_page(
    page: ItemsPage,
) -> ItemsPageResponse:
    validate_vendor_items_page(page)

    return map_vendor_items_page(page)
