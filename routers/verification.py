from fastapi import APIRouter

from services.verification_service import verify_raw_record_to_admission


router = APIRouter(tags=["verification"])


@router.post("/raw-admission-records/{record_id}/verify")
def verify_raw_admission_record(record_id: int) -> dict:
    return verify_raw_record_to_admission(record_id)
