from pydantic import BaseModel, Field


class RawAdmissionRecordCreate(BaseModel):
    raw_source_id: int | None = Field(default=None, gt=0)
    school_name: str | None = None
    school_code: str | None = None
    school_province: str | None = None
    city: str | None = None
    school_level: str | None = None
    school_tags: str | None = None
    major_name: str | None = None
    major_code: str | None = None
    major_category: str | None = None
    direction_tags: str | None = None
    major_description: str | None = None
    career_paths: str | None = None
    admission_year: int | None = Field(default=None, ge=2000, le=2100)
    admission_province: str | None = None
    subject_type: str | None = None
    batch: str | None = None
    major_group_code: str | None = None
    elective_requirement: str | None = None
    min_score: int | None = Field(default=None, ge=0)
    min_rank: int | None = Field(default=None, gt=0)
    plan_count: int | None = Field(default=None, ge=0)
    tuition: str | None = None
    campus: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    raw_text: str | None = None
    status: str = Field(default="pending", pattern="^(pending|verified|rejected)$")
    error_message: str | None = None


class RawAdmissionRecordResponse(RawAdmissionRecordCreate):
    id: int
    is_duplicate: bool
    created_at: str
    updated_at: str


class RawAdmissionRecordUpdateStatus(BaseModel):
    status: str = Field(pattern="^(pending|verified|rejected)$")
    error_message: str | None = None
