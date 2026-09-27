from python_integration_service.api.schemas import (
    ItemCategory,
    ItemResponse,
    ItemsPageResponse,
)
from python_integration_service.integrations.exceptions import (
    UnsupportedVendorCategoryError,
)
from python_integration_service.integrations.vendor_schemas import (
    ItemsPage,
    VendorCategory,
    VendorItem,
    VendorStatus,
)

_CATEGORY_MAPPING: dict[VendorCategory, ItemCategory] = {
    VendorCategory.HARDWARE: ItemCategory.HARDWARE,
    VendorCategory.SOFTWARE: ItemCategory.SOFTWARE,
    VendorCategory.ACCESSORY: ItemCategory.ACCESSORY,
}


def _map_category(
    category: VendorCategory,
) -> ItemCategory:
    try:
        return _CATEGORY_MAPPING[category]
    except KeyError as exc:
        raise UnsupportedVendorCategoryError(
            "Vendor category is not supported by the public API"
        ) from exc


def map_vendor_item(item: VendorItem) -> ItemResponse:
    return ItemResponse(
        id=item.id,
        name=item.attributes.display_name.strip(),
        category=_map_category(item.attributes.category),
        active=item.status is VendorStatus.ENABLED,
    )


def map_vendor_items_page(
    page: ItemsPage,
) -> ItemsPageResponse:
    return ItemsPageResponse(
        items=[map_vendor_item(item) for item in page.items],
        next_page=page.next_page,
    )
