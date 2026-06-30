from db import create_connection
from schemas.raw_data_sources import RawDataSourceCreate, RawDataSourceResponse


def _row_to_response(row) -> RawDataSourceResponse:
    data = dict(row)
    data["enabled"] = bool(data["enabled"])
    data["is_demo"] = bool(data.get("is_demo") or 0)
    data["is_candidate"] = bool(data.get("is_candidate") or 0)
    data["reference_only"] = bool(data.get("reference_only") or 0)
    return RawDataSourceResponse(**data)


def create_raw_data_source(data: RawDataSourceCreate) -> RawDataSourceResponse:
    """新增原始数据采集来源配置。"""
    db = create_connection()
    try:
        cursor = db.execute(
            """
            INSERT INTO raw_data_sources
                (name, source_type, url, parser_type, enabled, description,
                 school_name, discovery_score, discovery_mode, is_demo, is_candidate,
                 candidate_status,
                 official_check_status, official_check_message, official_score,
                 candidate_reject_reason, reference_only,
                 field_mapping_json, parser_config_json, parent_source_id,
                 file_type, local_file_path, file_size, file_download_status,
                 file_download_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.name,
                data.source_type,
                data.url,
                data.parser_type,
                int(data.enabled),
                data.description,
                data.school_name,
                data.discovery_score,
                data.discovery_mode or ("local_test" if data.source_type == "local_static" else None),
                int(data.is_demo or data.source_type == "local_static" or ("127.0.0.1" in (data.url or ""))),
                int(data.is_candidate),
                data.candidate_status or ("pending" if data.is_candidate else None),
                data.official_check_status,
                data.official_check_message,
                data.official_score,
                data.candidate_reject_reason,
                int(data.reference_only),
                data.field_mapping_json,
                data.parser_config_json,
                data.parent_source_id,
                data.file_type,
                data.local_file_path,
                data.file_size,
                data.file_download_status,
                data.file_download_message,
            ),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM raw_data_sources WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return _row_to_response(row)
    finally:
        db.close()


def list_raw_data_sources() -> list[RawDataSourceResponse]:
    """查询原始数据采集来源配置列表。"""
    db = create_connection()
    try:
        rows = db.execute(
            "SELECT * FROM raw_data_sources ORDER BY id DESC"
        ).fetchall()
        return [_row_to_response(row) for row in rows]
    finally:
        db.close()


def get_raw_data_source_by_id(source_id: int) -> RawDataSourceResponse | None:
    db = create_connection()
    try:
        row = db.execute(
            "SELECT * FROM raw_data_sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        return _row_to_response(row) if row else None
    finally:
        db.close()


def update_raw_data_source(
    source_id: int,
    data: dict,
) -> RawDataSourceResponse | None:
    """按传入字段更新一个原始数据源配置。"""
    allowed_fields = {
        "name",
        "source_type",
        "url",
        "parser_type",
        "enabled",
        "description",
        "school_name",
        "discovery_score",
        "discovery_mode",
        "is_demo",
        "is_candidate",
        "candidate_status",
        "official_check_status",
        "official_check_message",
        "official_score",
        "candidate_reject_reason",
        "reference_only",
        "field_mapping_json",
        "parser_config_json",
        "parent_source_id",
        "file_type",
        "local_file_path",
        "file_size",
        "file_download_status",
        "file_download_message",
    }
    update_data = {
        key: value
        for key, value in data.items()
        if key in allowed_fields
    }

    if "enabled" in update_data:
        update_data["enabled"] = int(update_data["enabled"])
    if "is_demo" in update_data:
        update_data["is_demo"] = int(update_data["is_demo"])
    if "is_candidate" in update_data:
        update_data["is_candidate"] = int(update_data["is_candidate"])
    if "reference_only" in update_data:
        update_data["reference_only"] = int(update_data["reference_only"])

    db = create_connection()
    try:
        exists = db.execute(
            "SELECT id FROM raw_data_sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        if not exists:
            return None

        if update_data:
            set_parts = [f"{field} = ?" for field in update_data]
            set_parts.append("updated_at = CURRENT_TIMESTAMP")
            values = list(update_data.values())
            values.append(source_id)
            db.execute(
                f"""
                UPDATE raw_data_sources
                SET {", ".join(set_parts)}
                WHERE id = ?
                """,
                values,
            )
            db.commit()

        row = db.execute(
            "SELECT * FROM raw_data_sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        return _row_to_response(row) if row else None
    finally:
        db.close()


def update_source_check_result(
    source_id: int,
    last_check_status: str,
    last_check_message: str | None,
    last_content_type: str | None,
    last_detected_type: str | None,
    last_table_count: int,
    last_file_links_json: str | None,
) -> None:
    """更新数据源可采性检测结果。"""
    db = create_connection()
    try:
        db.execute(
            """
            UPDATE raw_data_sources
            SET last_check_status = ?,
                last_check_message = ?,
                last_content_type = ?,
                last_detected_type = ?,
                last_table_count = ?,
                last_file_links_json = ?,
                last_checked_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                last_check_status,
                last_check_message,
                last_content_type,
                last_detected_type,
                last_table_count,
                last_file_links_json,
                source_id,
            ),
        )
        db.commit()
    finally:
        db.close()
