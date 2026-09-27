from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

PositivePage = Annotated[int, Field(gt=0)]


class VendorItem(BaseModel):
    id: int
    name: str

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
