from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

PositivePage = Annotated[int, Field(gt=0)]


class VendorStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class VendorCategory(StrEnum):
    HARDWARE = "hardware"
    SOFTWARE = "software"
    ACCESSORY = "accessory"
    BUNDLE = "bundle"


class VendorItemAttributes(BaseModel):
    display_name: str
    category: VendorCategory = Field(strict=False)

    model_config = ConfigDict(
        extra="ignore",
        strict=True,
    )


class VendorItem(BaseModel):
    id: int
    attributes: VendorItemAttributes
    status: VendorStatus = Field(strict=False)

    model_config = ConfigDict(
        extra="ignore",
        strict=True,
    )


class ItemsPage(BaseModel):
    items: list[VendorItem]
    next_page: PositivePage | None

    model_config = ConfigDict(
        extra="ignore",
        strict=True,
    )
