import pytest

from python_integration_service.api.schemas import (
    ItemCategory,
    ItemResponse,
    ItemsPageResponse,
)
from python_integration_service.integrations.exceptions import (
    InvalidVendorDataError,
)
from python_integration_service.integrations.vendor_schemas import (
    ItemsPage,
    VendorCategory,
    VendorItem,
    VendorItemAttributes,
    VendorStatus,
)
from python_integration_service.transformers.vendor import (
    transform_vendor_item,
    transform_vendor_items_page,
)


def test_transform_vendor_item_validates_and_maps_item() -> None:
    item = VendorItem(
        id=42,
        attributes=VendorItemAttributes(
            display_name="  Mechanical Keyboard  ",
            category=VendorCategory.HARDWARE,
        ),
        status=VendorStatus.ENABLED,
    )

    result = transform_vendor_item(item)

    assert result == ItemResponse(
        id=42,
        name="Mechanical Keyboard",
        category=ItemCategory.HARDWARE,
        active=True,
    )


def test_transform_vendor_item_rejects_semantically_invalid_data() -> None:
    item = VendorItem(
        id=42,
        attributes=VendorItemAttributes(
            display_name="   ",
            category=VendorCategory.HARDWARE,
        ),
        status=VendorStatus.ENABLED,
    )

    with pytest.raises(
        InvalidVendorDataError,
        match="display_name cannot be blank",
    ):
        transform_vendor_item(item)


def test_transform_vendor_items_page_validates_and_maps_page() -> None:
    page = ItemsPage(
        items=[
            VendorItem(
                id=1,
                attributes=VendorItemAttributes(
                    display_name="  Keyboard  ",
                    category=VendorCategory.HARDWARE,
                ),
                status=VendorStatus.ENABLED,
            )
        ],
        next_page=2,
    )

    result = transform_vendor_items_page(page)

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


def test_transform_vendor_items_page_rejects_semantically_invalid_item() -> None:
    page = ItemsPage(
        items=[
            VendorItem(
                id=1,
                attributes=VendorItemAttributes(
                    display_name="   ",
                    category=VendorCategory.HARDWARE,
                ),
                status=VendorStatus.ENABLED,
            )
        ],
        next_page=None,
    )

    with pytest.raises(
        InvalidVendorDataError,
        match="display_name cannot be blank",
    ):
        transform_vendor_items_page(page)


def test_transform_vendor_items_page_fails_for_mixed_semantically_invalid_page() -> (
    None
):
    page = ItemsPage(
        items=[
            VendorItem(
                id=1,
                attributes=VendorItemAttributes(
                    display_name="Valid item",
                    category=VendorCategory.HARDWARE,
                ),
                status=VendorStatus.ENABLED,
            ),
            VendorItem(
                id=2,
                attributes=VendorItemAttributes(
                    display_name="   ",
                    category=VendorCategory.SOFTWARE,
                ),
                status=VendorStatus.DISABLED,
            ),
            VendorItem(
                id=3,
                attributes=VendorItemAttributes(
                    display_name="Another valid item",
                    category=VendorCategory.ACCESSORY,
                ),
                status=VendorStatus.ENABLED,
            ),
        ],
        next_page=None,
    )

    with pytest.raises(
        InvalidVendorDataError,
        match="display_name cannot be blank",
    ):
        transform_vendor_items_page(page)
