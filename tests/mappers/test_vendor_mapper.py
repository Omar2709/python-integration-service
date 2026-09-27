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
    VendorCategory,
    VendorStatus,
)
from python_integration_service.mappers.vendor import (
    map_vendor_item,
    map_vendor_items_page,
)
from tests.factories.vendor import (
    make_items_page,
    make_vendor_item,
)


def test_map_vendor_item_transforms_upstream_item() -> None:
    item = make_vendor_item(
        item_id=42,
        display_name="  Mechanical Keyboard  ",
    )

    result = map_vendor_item(item)

    assert result == ItemResponse(
        id=42,
        name="Mechanical Keyboard",
        category=ItemCategory.HARDWARE,
        active=True,
    )


@pytest.mark.parametrize(
    ("status", "expected_active"),
    [
        pytest.param(
            VendorStatus.ENABLED,
            True,
            id="enabled",
        ),
        pytest.param(
            VendorStatus.DISABLED,
            False,
            id="disabled",
        ),
    ],
)
def test_map_vendor_item_maps_status_to_active(
    status: VendorStatus,
    expected_active: bool,
) -> None:
    item = make_vendor_item(
        status=status,
    )

    result = map_vendor_item(item)

    assert result.active is expected_active


def test_map_vendor_items_page_maps_items_and_pagination() -> None:
    page = make_items_page(
        items=[
            make_vendor_item(),
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
    item = make_vendor_item(
        item_id=42,
        display_name="Bundle",
        category=VendorCategory.BUNDLE,
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
