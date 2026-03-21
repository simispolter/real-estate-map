from pydantic import BaseModel, Field


class Pagination(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    total: int = Field(default=0, ge=0)


class SelectOption(BaseModel):
    id: str | None = None
    label: str
