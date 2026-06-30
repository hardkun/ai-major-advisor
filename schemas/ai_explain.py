from pydantic import BaseModel


class AIExplanation(BaseModel):
    recommend_reason: str
    study_focus: str
    suitable_for: str
    career_suggestions: str
    risk_notice: str

