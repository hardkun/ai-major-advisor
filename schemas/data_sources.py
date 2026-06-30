from pydantic import BaseModel, Field


class DataSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: str | None = None
    url: str | None = None
    description: str | None = None


class DataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str | None
    url: str | None
    description: str | None
    created_at: str
    updated_at: str

