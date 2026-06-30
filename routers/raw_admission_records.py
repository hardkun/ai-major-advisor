from fastapi import APIRouter, HTTPException, Query, status

from crud.raw_admission_records import (
    create_raw_admission_record,
    get_raw_admission_record_by_id,
    list_raw_admission_records,
    update_raw_admission_record_status,
)
from crud.raw_data_sources import get_raw_data_source_by_id
from schemas.raw_admission_records import (
    RawAdmissionRecordCreate,
    RawAdmissionRecordResponse,
    RawAdmissionRecordUpdateStatus,
)


router = APIRouter(prefix="/raw-admission-records", tags=["raw-admission-records"])

VALID_STATUSES = {"pending", "verified", "rejected"}


@router.post(
    "",
    response_model=RawAdmissionRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_raw_admission_record(
    data: RawAdmissionRecordCreate,
) -> RawAdmissionRecordResponse:
    if data.raw_source_id and not get_raw_data_source_by_id(data.raw_source_id):
        raise HTTPException(status_code=404, detail="原始数据来源不存在")
    return create_raw_admission_record(data)


@router.get("", response_model=list[RawAdmissionRecordResponse])
def get_raw_admission_records(
    status: str | None = Query(default=None),
) -> list[RawAdmissionRecordResponse]:
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="status 只能是 pending / verified / rejected",
        )
    return list_raw_admission_records(status=status)


@router.get("/{record_id}", response_model=RawAdmissionRecordResponse)
def get_raw_admission_record(record_id: int) -> RawAdmissionRecordResponse:
    record = get_raw_admission_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="原始招生记录不存在")
    return record


@router.patch("/{record_id}/status", response_model=RawAdmissionRecordResponse)
def update_raw_admission_record_status_api(
    record_id: int,
    data: RawAdmissionRecordUpdateStatus,
) -> RawAdmissionRecordResponse:
    record = update_raw_admission_record_status(record_id, data)
    if not record:
        raise HTTPException(status_code=404, detail="原始招生记录不存在")
    return record
