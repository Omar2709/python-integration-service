from python_integration_service.integrations.vendor_schemas import (
    ItemsPage,
    VendorCategory,
    VendorItem,
    VendorItemAttributes,
    VendorStatus,
)


def make_vendor_item(
    *,
    item_id: int = 1,
    display_name: str = "Keyboard",
    category: VendorCategory = VendorCategory.HARDWARE,
    status: VendorStatus = VendorStatus.ENABLED,
) -> VendorItem:
    return VendorItem(
        id=item_id,
        attributes=VendorItemAttributes(
            display_name=display_name,
            category=category,
        ),
        status=status,
    )


def make_items_page(
    *,
    items: list[VendorItem] | None = None,
    next_page: int | None = None,
) -> ItemsPage:
    return ItemsPage(
        items=[] if items is None else items,
        next_page=next_page,
    )


def make_vendor_item_payload(
    *,
    item_id: object = 1,
    display_name: object = "Item 1",
    category: object = "hardware",
    status: object = "enabled",
) -> dict[str, object]:
    return {
        "id": item_id,
        "attributes": {
            "display_name": display_name,
            "category": category,
        },
        "status": status,
    }


def make_items_page_payload(
    *,
    items: list[dict[str, object]] | None = None,
    next_page: object = None,
) -> dict[str, object]:
    return {
        "items": [] if items is None else items,
        "next_page": next_page,
    }
