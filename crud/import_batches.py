from db import create_connection
from schemas.import_batches import ImportBatchCreate, ImportBatchResponse


def create_import_batch(data: ImportBatchCreate) -> ImportBatchResponse:
    """新增数据导入批次。"""
    db = create_connection()
    try:
        cursor = db.execute(
            """
            INSERT INTO import_batches
                (batch_name, data_year, province, source_id, row_count, remark)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data.batch_name,
                data.data_year,
                data.province,
                data.source_id,
                data.row_count,
                data.remark,
            ),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM import_batches WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return ImportBatchResponse(**dict(row))
    finally:
        db.close()


def list_import_batches() -> list[ImportBatchResponse]:
    """按创建顺序倒序查询导入批次。"""
    db = create_connection()
    try:
        rows = db.execute(
            "SELECT * FROM import_batches ORDER BY id DESC"
        ).fetchall()
        return [ImportBatchResponse(**dict(row)) for row in rows]
    finally:
        db.close()


def update_import_batch_row_count(batch_id: int, row_count: int) -> None:
    """更新指定导入批次的数据行数。"""
    db = create_connection()
    try:
        db.execute(
            "UPDATE import_batches SET row_count = ? WHERE id = ?",
            (row_count, batch_id),
        )
        db.commit()
    finally:
        db.close()

