import pytest

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
from python_integration_service.validators.vendor import (
    validate_vendor_item,
    validate_vendor_items_page,
)


def test_validate_vendor_item_accepts_non_blank_name() -> None:
    item = VendorItem(
        id=1,
        attributes=VendorItemAttributes(
            display_name="Keyboard",
            category=VendorCategory.HARDWARE,
        ),
        status=VendorStatus.ENABLED,
    )

    validate_vendor_item(item)


def test_validate_vendor_item_accepts_name_with_surrounding_whitespace() -> None:
    item = VendorItem(
        id=1,
        attributes=VendorItemAttributes(
            display_name="  Keyboard  ",
            category=VendorCategory.HARDWARE,
        ),
        status=VendorStatus.ENABLED,
    )

    validate_vendor_item(item)


def test_validate_vendor_item_rejects_blank_name() -> None:
    item = VendorItem(
        id=1,
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
        validate_vendor_item(item)


def test_validate_vendor_items_page_accepts_valid_page() -> None:
    page = ItemsPage(
        items=[
            VendorItem(
                id=1,
                attributes=VendorItemAttributes(
                    display_name="Keyboard",
                    category=VendorCategory.HARDWARE,
                ),
                status=VendorStatus.ENABLED,
            ),
            VendorItem(
                id=2,
                attributes=VendorItemAttributes(
                    display_name="IDE",
                    category=VendorCategory.SOFTWARE,
                ),
                status=VendorStatus.DISABLED,
            ),
        ],
        next_page=2,
    )

    validate_vendor_items_page(page)


def test_validate_vendor_items_page_rejects_page_with_invalid_item() -> None:
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
        ],
        next_page=None,
    )

    with pytest.raises(
        InvalidVendorDataError,
        match="display_name cannot be blank",
    ):
        validate_vendor_items_page(page)
