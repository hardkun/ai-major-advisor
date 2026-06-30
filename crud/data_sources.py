from db import create_connection
from schemas.data_sources import DataSourceCreate, DataSourceResponse


def create_data_source(data: DataSourceCreate) -> DataSourceResponse:
    """新增数据来源。"""
    db = create_connection()
    try:
        cursor = db.execute(
            """
            INSERT INTO data_sources (name, source_type, url, description)
            VALUES (?, ?, ?, ?)
            """,
            (data.name, data.source_type, data.url, data.description),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM data_sources WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return DataSourceResponse(**dict(row))
    finally:
        db.close()


def list_data_sources() -> list[DataSourceResponse]:
    """按创建顺序倒序查询数据来源。"""
    db = create_connection()
    try:
        rows = db.execute(
            "SELECT * FROM data_sources ORDER BY id DESC"
        ).fetchall()
        return [DataSourceResponse(**dict(row)) for row in rows]
    finally:
        db.close()


def get_data_source_by_id(source_id: int) -> DataSourceResponse | None:
    db = create_connection()
    try:
        row = db.execute(
            "SELECT * FROM data_sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        return DataSourceResponse(**dict(row)) if row else None
    finally:
        db.close()


def get_data_source_by_name(name: str) -> DataSourceResponse | None:
    db = create_connection()
    try:
        row = db.execute(
            """
            SELECT * FROM data_sources
            WHERE name = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (name,),
        ).fetchone()
        return DataSourceResponse(**dict(row)) if row else None
    finally:
        db.close()

