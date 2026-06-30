import sqlite3

from fastapi import APIRouter, Depends, status

from crud import major as major_crud
from db import get_db
from schemas.major import MajorCreate, MajorResponse


router = APIRouter(prefix="/majors", tags=["majors"])


@router.post("", response_model=MajorResponse, status_code=status.HTTP_201_CREATED)
def create_major(
    major: MajorCreate,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    return major_crud.create_major(db, major)


@router.get("", response_model=list[MajorResponse])
def list_majors(db: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return major_crud.list_majors(db)
