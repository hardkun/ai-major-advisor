import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, status

from crud import admission as admission_crud
from crud import major as major_crud
from crud import school as school_crud
from db import get_db
from schemas.admission import AdmissionCreate, AdmissionResponse
from services import admission as admission_service


router = APIRouter(prefix="/admissions", tags=["admissions"])


@router.post("", response_model=AdmissionResponse, status_code=status.HTTP_201_CREATED)
def create_admission(
    admission: AdmissionCreate,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    if not school_crud.get_school(db, admission.school_id):
        raise HTTPException(status_code=404, detail="学校不存在")
    if not major_crud.get_major(db, admission.major_id):
        raise HTTPException(status_code=404, detail="专业不存在")
    return admission_crud.create_admission(db, admission)


@router.get("", response_model=list[AdmissionResponse])
def list_admissions(
    school_id: int | None = Query(default=None, gt=0),
    major_id: int | None = Query(default=None, gt=0),
    year: int | None = Query(default=None, ge=2000, le=2100),
    province: str | None = Query(default=None, min_length=1),
    db: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    return admission_service.get_admissions(
        db=db,
        school_id=school_id,
        major_id=major_id,
        year=year,
        province=province,
    )
