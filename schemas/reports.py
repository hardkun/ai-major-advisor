from pydantic import BaseModel


class ReportResponse(BaseModel):
    id: int
    log_id: int
    free_result: dict
    paid_result: dict | None
    is_paid: bool
    created_at: str
    updated_at: str

