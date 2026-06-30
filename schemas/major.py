from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MajorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["人工智能"])
    category: str | None = Field(default=None, max_length=100, examples=["工学"])
    direction_tags: str | None = Field(default=None, examples=["机器学习,计算机视觉"])
    description: str | None = None
    career_paths: str | None = Field(default=None, examples=["算法工程师,数据科学家"])


class MajorResponse(MajorCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
