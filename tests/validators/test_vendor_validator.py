import pytest

from python_integration_service.integrations.exceptions import (
    InvalidVendorDataError,
)
from python_integration_service.integrations.vendor_schemas import (
    VendorCategory,
    VendorStatus,
)
from python_integration_service.validators.vendor import (
    validate_vendor_item,
    validate_vendor_items_page,
)
from tests.factories.vendor import (
    make_items_page,
    make_vendor_item,
)


def test_validate_vendor_item_accepts_non_blank_name() -> None:
    item = make_vendor_item(
        display_name="Keyboard",
    )

    validate_vendor_item(item)


def test_validate_vendor_item_accepts_name_with_surrounding_whitespace() -> None:
    item = make_vendor_item(
        display_name="  Keyboard  ",
    )

    validate_vendor_item(item)


@pytest.mark.parametrize(
    "display_name",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="spaces"),
        pytest.param("\t", id="tab"),
        pytest.param("\n", id="newline"),
    ],
)
def test_validate_vendor_item_rejects_blank_name(
    display_name: str,
) -> None:
    item = make_vendor_item(
        display_name=display_name,
    )

    with pytest.raises(
        InvalidVendorDataError,
        match="display_name cannot be blank",
    ):
        validate_vendor_item(item)


def test_validate_vendor_items_page_accepts_valid_page() -> None:
    page = make_items_page(
        items=[
            make_vendor_item(),
            make_vendor_item(
                item_id=2,
                display_name="IDE",
                category=VendorCategory.SOFTWARE,
                status=VendorStatus.DISABLED,
            ),
        ],
        next_page=2,
    )

    validate_vendor_items_page(page)


def test_validate_vendor_items_page_rejects_page_with_invalid_item() -> None:
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
        ],
    )

    with pytest.raises(
        InvalidVendorDataError,
        match="display_name cannot be blank",
    ):
        validate_vendor_items_page(page)
