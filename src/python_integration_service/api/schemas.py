from enum import StrEnum

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    detail: str


class ItemCategory(StrEnum):
    HARDWARE = "hardware"
    SOFTWARE = "software"
    ACCESSORY = "accessory"


class ItemResponse(BaseModel):
    id: int
    name: str
    category: ItemCategory
    active: bool


class ItemsPageResponse(BaseModel):
    items: list[ItemResponse]
    next_page: int | None
