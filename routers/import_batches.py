from fastapi import APIRouter, HTTPException, status

from crud.data_sources import get_data_source_by_id
from crud.import_batches import create_import_batch, list_import_batches
from schemas.import_batches import ImportBatchCreate, ImportBatchResponse


router = APIRouter(prefix="/import-batches", tags=["import-batches"])


@router.post("", response_model=ImportBatchResponse, status_code=status.HTTP_201_CREATED)
def add_import_batch(data: ImportBatchCreate) -> ImportBatchResponse:
    if data.source_id is not None and get_data_source_by_id(data.source_id) is None:
        raise HTTPException(status_code=404, detail="数据来源不存在")
    return create_import_batch(data)


@router.get("", response_model=list[ImportBatchResponse])
def get_import_batches() -> list[ImportBatchResponse]:
    return list_import_batches()

