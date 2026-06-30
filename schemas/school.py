from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SchoolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["清华大学"])
    province: str | None = Field(default=None, max_length=50, examples=["北京"])
    city: str | None = Field(default=None, max_length=50)
    level: str | None = Field(default=None, max_length=50, examples=["双一流"])
    tags: str | None = Field(default=None, examples=["985,211,强基计划"])


class SchoolResponse(SchoolCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
