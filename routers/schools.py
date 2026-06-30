import sqlite3

from fastapi import APIRouter, Depends, status

from crud import school as school_crud
from db import get_db
from schemas.school import SchoolCreate, SchoolResponse


router = APIRouter(prefix="/schools", tags=["schools"])


@router.post("", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED)
def create_school(
    school: SchoolCreate,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    return school_crud.create_school(db, school)


@router.get("", response_model=list[SchoolResponse])
def list_schools(db: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return school_crud.list_schools(db)
