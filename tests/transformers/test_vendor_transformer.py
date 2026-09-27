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
    VendorCategory,
    VendorStatus,
)
from python_integration_service.transformers.vendor import (
    transform_vendor_item,
    transform_vendor_items_page,
)
from tests.factories.vendor import (
    make_items_page,
    make_vendor_item,
)


def test_transform_vendor_item_validates_and_maps_item() -> None:
    item = make_vendor_item(
        item_id=42,
        display_name="  Mechanical Keyboard  ",
    )

    result = transform_vendor_item(item)

    assert result == ItemResponse(
        id=42,
        name="Mechanical Keyboard",
        category=ItemCategory.HARDWARE,
        active=True,
    )


def test_transform_vendor_item_rejects_semantically_invalid_data() -> None:
    item = make_vendor_item(
        item_id=42,
        display_name="   ",
    )

    with pytest.raises(
        InvalidVendorDataError,
        match="display_name cannot be blank",
    ):
        transform_vendor_item(item)


def test_transform_vendor_items_page_validates_and_maps_page() -> None:
    page = make_items_page(
        items=[
            make_vendor_item(
                display_name="  Keyboard  ",
            ),
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
    page = make_items_page(
        items=[
            make_vendor_item(
                display_name="   ",
            ),
        ],
    )

    with pytest.raises(
        InvalidVendorDataError,
        match="display_name cannot be blank",
    ):
        transform_vendor_items_page(page)


def test_transform_vendor_items_page_fails_for_mixed_semantically_invalid_page() -> (
    None
):
    page = make_items_page(
        items=[
            make_vendor_item(
                display_name="Valid item",
            ),
            make_vendor_item(
                item_id=2,
                display_name="   ",
                category=VendorCategory.SOFTWARE,
                status=VendorStatus.DISABLED,
            ),
            make_vendor_item(
                item_id=3,
                display_name="Another valid item",
                category=VendorCategory.ACCESSORY,
            ),
        ],
    )

    with pytest.raises(
        InvalidVendorDataError,
        match="display_name cannot be blank",
    ):
        transform_vendor_items_page(page)
