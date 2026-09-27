import pytest

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
    VendorItemAttributes,
    VendorStatus,
)
from python_integration_service.mappers.vendor import (
    map_vendor_item,
    map_vendor_items_page,
)


def test_map_vendor_item_transforms_upstream_item() -> None:
    item = VendorItem(
        id=42,
        attributes=VendorItemAttributes(
            display_name="  Mechanical Keyboard  ",
            category=VendorCategory.HARDWARE,
        ),
        status=VendorStatus.ENABLED,
    )

    result = map_vendor_item(item)

    assert result == ItemResponse(
        id=42,
        name="Mechanical Keyboard",
        category=ItemCategory.HARDWARE,
        active=True,
    )


def test_map_vendor_item_maps_disabled_status_to_inactive() -> None:
    item = VendorItem(
        id=42,
        attributes=VendorItemAttributes(
            display_name="Mechanical Keyboard",
            category=VendorCategory.HARDWARE,
        ),
        status=VendorStatus.DISABLED,
    )

    result = map_vendor_item(item)

    assert result.active is False


def test_map_vendor_items_page_maps_items_and_pagination() -> None:
    page = ItemsPage(
        items=[
            VendorItem(
                id=1,
                attributes=VendorItemAttributes(
                    display_name="Keyboard",
                    category=VendorCategory.HARDWARE,
                ),
                status=VendorStatus.ENABLED,
            )
        ],
        next_page=2,
    )

    result = map_vendor_items_page(page)

    assert result == ItemsPageResponse(
        items=[
            ItemResponse(
                id=1,
                name="Keyboard",
                category=ItemCategory.HARDWARE,
                active=True,
            )
        ],
        next_page=2,
    )


def test_map_vendor_item_rejects_unsupported_vendor_category() -> None:
    item = VendorItem(
        id=42,
        attributes=VendorItemAttributes(
            display_name="Bundle",
            category=VendorCategory.BUNDLE,
        ),
        status=VendorStatus.ENABLED,
    )

    with pytest.raises(
        UnsupportedVendorCategoryError,
        match="not supported by the public API",
    ) as exc_info:
        map_vendor_item(item)

    assert isinstance(
        exc_info.value.__cause__,
        KeyError,
    )
