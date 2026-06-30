from pydantic import BaseModel


class CollectorRunResponse(BaseModel):
    id: int
    raw_source_id: int | None
    source_name: str | None
    parser_type: str | None
    status: str
    inserted_count: int
    skipped_count: int
    error_count: int
    message: str | None
    started_at: str | None
    finished_at: str | None
    created_at: str
