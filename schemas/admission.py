from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdmissionCreate(BaseModel):
    school_id: int = Field(gt=0)
    major_id: int = Field(gt=0)
    year: int = Field(ge=2000, le=2100)
    province: str = Field(min_length=1, max_length=50, examples=["浙江"])
    subject_type: str = Field(min_length=1, max_length=50, examples=["物理类"])
    batch: str | None = Field(default=None, max_length=50)
    min_score: int | None = Field(default=None, ge=0)
    min_rank: int | None = Field(default=None, gt=0)
    plan_count: int | None = Field(default=None, ge=0)
    tuition: str | None = Field(default=None, max_length=100)
    source: str | None = None
    school_code: str | None = None
    major_group_code: str | None = None
    major_code: str | None = None
    elective_requirement: str | None = None
    campus: str | None = None
    source_id: int | None = None
    import_batch_id: int | None = None
    is_verified: bool = False
    remark: str | None = None


class AdmissionResponse(AdmissionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
