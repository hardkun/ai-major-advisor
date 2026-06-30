"""Project health check for ai-major-advisor portfolio demo."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db import DATABASE_PATH, create_connection


REQUIRED_TABLES = {
    "schools",
    "majors",
    "admissions",
    "raw_admission_records",
    "raw_data_sources",
    "reports",
    "collector_runs",
}


def scalar(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    value = conn.execute(sql, params).fetchone()[0]
    return int(value or 0)


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def run_project_check() -> dict:
    database_ok = DATABASE_PATH.exists()
    result = {
        "database_path": str(DATABASE_PATH),
        "database_ok": database_ok,
        "tables_ok": False,
        "missing_tables": sorted(REQUIRED_TABLES),
        "recommend_data_ok": False,
        "verified_records_count": 0,
        "real_school_count": 0,
        "demo_sources_count": 0,
        "has_demo_or_test_sources": False,
        "ready_for_demo": False,
    }

    if not database_ok:
        result["message"] = "Database file does not exist. Start the backend once or import demo data first."
        return result

    conn = create_connection()
    try:
        existing_tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        missing_tables = sorted(REQUIRED_TABLES - existing_tables)
        result["missing_tables"] = missing_tables
        result["tables_ok"] = not missing_tables

        if not result["tables_ok"]:
            result["message"] = "Some required tables are missing."
            return result

        result["verified_records_count"] = scalar(
            conn,
            "SELECT COUNT(*) FROM admissions WHERE COALESCE(is_verified, 0) = 1",
        )
        result["real_school_count"] = scalar(
            conn,
            """
            SELECT COUNT(DISTINCT schools.name)
            FROM admissions
            JOIN schools ON schools.id = admissions.school_id
            WHERE COALESCE(admissions.is_verified, 0) = 1
            """,
        )
        result["demo_sources_count"] = scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM raw_data_sources
            WHERE COALESCE(is_demo, 0) = 1
               OR COALESCE(source_type, '') = 'local_static'
               OR COALESCE(url, '') LIKE '%127.0.0.1%'
               OR COALESCE(url, '') LIKE '%localhost%'
               OR COALESCE(name, '') LIKE '%测试%'
               OR COALESCE(name, '') LIKE '%示例%'
               OR COALESCE(description, '') LIKE '%测试%'
               OR COALESCE(description, '') LIKE '%示例%'
            """,
        )
        result["has_demo_or_test_sources"] = result["demo_sources_count"] > 0

        admissions_count = scalar(conn, "SELECT COUNT(*) FROM admissions")
        schools_count = scalar(conn, "SELECT COUNT(*) FROM schools")
        majors_count = scalar(conn, "SELECT COUNT(*) FROM majors")
        result["recommend_data_ok"] = admissions_count > 0 and schools_count > 0 and majors_count > 0

        result["ready_for_demo"] = (
            result["database_ok"]
            and result["tables_ok"]
            and result["recommend_data_ok"]
            and result["verified_records_count"] > 0
            and result["real_school_count"] >= 1
        )
        result["message"] = (
            "Project is ready for portfolio demo."
            if result["ready_for_demo"]
            else "Project can run, but demo data should be checked before presentation."
        )
        return result
    finally:
        conn.close()


if __name__ == "__main__":
    print(json.dumps(run_project_check(), ensure_ascii=False, indent=2))
