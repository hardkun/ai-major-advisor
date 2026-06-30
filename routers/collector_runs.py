from fastapi import APIRouter, Query

from crud.collector_runs import list_collector_runs
from schemas.collector_runs import CollectorRunResponse


router = APIRouter(prefix="/collector-runs", tags=["collector-runs"])


@router.get("", response_model=list[CollectorRunResponse])
def get_collector_runs(
    limit: int = Query(default=50, ge=1, le=200),
) -> list[CollectorRunResponse]:
    return list_collector_runs(limit=limit)
