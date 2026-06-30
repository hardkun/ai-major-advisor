import sqlite3

from crud import admission as admission_crud


def get_admissions(
    db: sqlite3.Connection,
    school_id: int | None = None,
    major_id: int | None = None,
    year: int | None = None,
    province: str | None = None,
) -> list[dict]:
    """录取数据查询业务；后续可在这里添加排序和推荐规则。"""
    return admission_crud.list_admissions(
        db=db,
        school_id=school_id,
        major_id=major_id,
        year=year,
        province=province,
    )

