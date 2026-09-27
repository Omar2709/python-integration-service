from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    detail: str


class ItemResponse(BaseModel):
    id: int
    name: str


class ItemsPageResponse(BaseModel):
    items: list[ItemResponse]
    next_page: int | None
