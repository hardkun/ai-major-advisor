from pydantic import BaseModel, Field

from schemas.ai_explain import AIExplanation


class RecommendRequest(BaseModel):
    province: str = Field(min_length=1, max_length=50, examples=["浙江"])
    score: int = Field(ge=0, examples=[650])
    rank: int = Field(gt=0, examples=[5000])
    subject_type: str = Field(min_length=1, max_length=50, examples=["物理类"])
    target_direction: str = Field(min_length=1, examples=["机器学习"])
    use_ai: bool = False


class RecommendItem(BaseModel):
    school_name: str
    major_name: str
    city: str | None
    school_level: str | None
    match_type: str
    min_score: int | None
    min_rank: int | None
    direction_tags: str | None
    career_paths: str | None
    reason: str
    year: int | None = None
    school_code: str | None = None
    major_group_code: str | None = None
    major_code: str | None = None
    elective_requirement: str | None = None
    campus: str | None = None
    source_name: str | None = None
    is_verified: bool = False
    ai_explanation: AIExplanation | None = None


class RecommendResponse(BaseModel):
    items: list[RecommendItem]
    disclaimer: str
    log_id: int | None = None
    report_id: int | None = None
