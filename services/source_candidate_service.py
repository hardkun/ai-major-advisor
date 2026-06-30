"""候选数据源列表、确认和驳回服务。"""

from fastapi import HTTPException

from db import create_connection, init_db


def _row_to_dict(row) -> dict | None:
    return dict(row) if row else None


def list_source_candidates(limit: int = 100, include_all: bool = False) -> list[dict]:
    """列出搜索发现的候选数据源。

    默认只展示 pending 且通过官方来源过滤的候选源，避免管理员被第三方页面噪声淹没。
    include_all=True 时展示 reference_only / rejected 等全部候选，便于排查。
    """
    init_db()
    limit = min(max(int(limit), 1), 300)
    conn = create_connection()
    try:
        where = """
            COALESCE(is_candidate, 0) = 1
            AND COALESCE(is_demo, 0) != 1
        """
        if not include_all:
            where += """
                AND candidate_status = 'pending'
                AND official_check_status IN ('official', 'likely_official')
                AND COALESCE(reference_only, 0) != 1
            """
        rows = conn.execute(
            f"""
            SELECT id, school_name, name, url, parser_type, discovery_score,
                   discovery_mode, enabled, is_candidate, candidate_status,
                   official_check_status, official_score, official_check_message,
                   candidate_reject_reason, reference_only,
                   description, created_at
            FROM raw_data_sources
            WHERE {where}
            ORDER BY official_score DESC, discovery_score DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _get_source(conn, source_id: int) -> dict | None:
    return _row_to_dict(
        conn.execute(
            "SELECT * FROM raw_data_sources WHERE id = ?",
            (source_id,),
        ).fetchone()
    )


def approve_source_candidate(source_id: int) -> dict:
    """人工确认候选源。

    只有 official / likely_official 且不是 reference_only 的候选源才能被确认启用。
    """
    init_db()
    conn = create_connection()
    try:
        source = _get_source(conn, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="候选数据源不存在")
        if int(source.get("is_candidate") or 0) != 1:
            return {"message": "该数据源不是候选源，无需确认", "source": source}
        if source.get("official_check_status") not in {"official", "likely_official"}:
            raise HTTPException(
                status_code=400,
                detail="该候选源未通过官方来源校验，不能启用为正式数据源",
            )
        if int(source.get("reference_only") or 0) == 1:
            raise HTTPException(
                status_code=400,
                detail="该候选源仅可作为线索 reference_only，不能启用为正式数据源",
            )

        description = source.get("description") or ""
        note = "人工确认启用的搜索候选源"
        if note not in description:
            description = f"{description}；{note}".strip("；")

        conn.execute(
            """
            UPDATE raw_data_sources
            SET is_candidate = 0,
                enabled = 1,
                source_type = 'school',
                candidate_status = 'approved',
                description = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (description, source_id),
        )
        conn.commit()
        updated = _get_source(conn, source_id)
        return {"message": "候选源已确认启用", "source": updated}
    finally:
        conn.close()


def reject_source_candidate(source_id: int, reason: str | None = None) -> dict:
    """人工驳回候选源。"""
    init_db()
    conn = create_connection()
    try:
        source = _get_source(conn, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="候选数据源不存在")

        reject_reason = reason or "管理员人工驳回"
        description = source.get("description") or ""
        reject_note = f"已驳回：{reject_reason}"
        if reject_note not in description:
            description = f"{description}；{reject_note}".strip("；")

        conn.execute(
            """
            UPDATE raw_data_sources
            SET enabled = 0,
                is_candidate = 1,
                candidate_status = 'rejected',
                candidate_reject_reason = ?,
                description = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (reject_reason, description, source_id),
        )
        conn.commit()
        updated = _get_source(conn, source_id)
        return {"message": "候选源已驳回", "source": updated}
    finally:
        conn.close()
