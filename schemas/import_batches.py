from pydantic import BaseModel, Field


class ImportBatchCreate(BaseModel):
    batch_name: str = Field(min_length=1, max_length=200)
    data_year: int | None = None
    province: str | None = None
    source_id: int | None = None
    row_count: int = Field(default=0, ge=0)
    remark: str | None = None


class ImportBatchResponse(BaseModel):
    id: int
    batch_name: str
    data_year: int | None
    province: str | None
    source_id: int | None
    row_count: int
    remark: str | None
    created_at: str

