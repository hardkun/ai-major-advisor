"""高校种子表导入与状态查询服务。"""

import csv
from pathlib import Path

from db import BASE_DIR, create_connection, init_db


DEFAULT_SEED_PATH = BASE_DIR / "data_sources" / "sichuan_2025_school_seed.csv"


def _to_bool(value) -> bool:
    return str(value).strip().lower() not in {"0", "false", "否", "no", ""}


def _task_exists(conn, school_name: str, query: str) -> bool:
    row = conn.execute(
        """
        SELECT id FROM source_discovery_tasks
        WHERE school_name = ? AND query = ?
        LIMIT 1
        """,
        (school_name, query),
    ).fetchone()
    return row is not None


def _raw_source_exists(conn, school_name: str) -> bool:
    row = conn.execute(
        """
        SELECT id FROM raw_data_sources
        WHERE name LIKE ?
        LIMIT 1
        """,
        (f"%{school_name}%",),
    ).fetchone()
    return row is not None


def import_school_seed_csv(path: str | Path = DEFAULT_SEED_PATH) -> dict:
    """读取高校种子 CSV，为 enabled 学校生成数据源发现任务。

    该函数不抓取网页，只把后续发现任务放进 source_discovery_tasks。
    """
    init_db()
    csv_path = Path(path)
    if not csv_path.is_absolute():
        csv_path = BASE_DIR / csv_path

    created_tasks = 0
    skipped_tasks = 0
    total_enabled_schools = 0
    total_rows = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    conn = create_connection()
    try:
        for row in rows:
            total_rows += 1
            school_name = (row.get("school_name") or "").strip()
            if not school_name:
                skipped_tasks += 1
                continue

            enabled = _to_bool(row.get("enabled", "1"))
            if not enabled:
                continue

            total_enabled_schools += 1
            admission_site = (row.get("admission_site") or "").strip() or None
            query = f"{school_name} 四川 2025 专业录取分数"

            if _task_exists(conn, school_name, query):
                skipped_tasks += 1
                continue

            message = None
            if not admission_site:
                message = "缺少招生官网入口，需要人工补充 admission_site"

            conn.execute(
                """
                INSERT INTO source_discovery_tasks
                    (school_name, admission_site, query, status, message)
                VALUES (?, ?, ?, 'pending', ?)
                """,
                (school_name, admission_site, query, message),
            )
            created_tasks += 1

        conn.commit()
    finally:
        conn.close()

    return {
        "seed_path": str(csv_path),
        "total_rows": total_rows,
        "total_enabled_schools": total_enabled_schools,
        "created_tasks": created_tasks,
        "skipped_tasks": skipped_tasks,
    }


def list_school_seed_status(path: str | Path = DEFAULT_SEED_PATH) -> list[dict]:
    """返回种子表中每所学校的数据源、采集和核验状态。"""
    init_db()
    csv_path = Path(path)
    if not csv_path.is_absolute():
        csv_path = BASE_DIR / csv_path

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    conn = create_connection()
    try:
        result = []
        for row in rows:
            school_name = (row.get("school_name") or "").strip()
            if not school_name:
                continue

            raw_records_count = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM raw_admission_records
                WHERE school_name = ?
                """,
                (school_name,),
            ).fetchone()["count"]
            verified_records_count = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM admissions
                JOIN schools ON schools.id = admissions.school_id
                WHERE schools.name = ?
                """,
                (school_name,),
            ).fetchone()["count"]
            has_successful_collect_run = conn.execute(
                """
                SELECT 1
                FROM collector_runs
                WHERE source_name LIKE ?
                  AND status IN ('success', 'partial', 'skipped')
                LIMIT 1
                """,
                (f"%{school_name}%",),
            ).fetchone() is not None

            result.append(
                {
                    "school_name": school_name,
                    "admission_site": (row.get("admission_site") or "").strip() or None,
                    "has_raw_data_source": _raw_source_exists(conn, school_name),
                    "has_successful_collect_run": has_successful_collect_run,
                    "raw_records_count": raw_records_count,
                    "verified_records_count": verified_records_count,
                }
            )

        return result
    finally:
        conn.close()
