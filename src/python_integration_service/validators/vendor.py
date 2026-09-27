from python_integration_service.integrations.exceptions import (
    InvalidVendorDataError,
)
from python_integration_service.integrations.vendor_schemas import (
    ItemsPage,
    VendorItem,
)


def validate_vendor_item(item: VendorItem) -> None:
    if not item.attributes.display_name.strip():
        raise InvalidVendorDataError("Vendor item display_name cannot be blank")


def validate_vendor_items_page(page: ItemsPage) -> None:
    for item in page.items:
        validate_vendor_item(item)
