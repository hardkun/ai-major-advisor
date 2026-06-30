"""Prepare the local database for portfolio/demo presentation.

This script does not delete data. It only marks obvious demo/test data sources
with is_demo=1 so coverage reports and admin review can focus on verified real
school data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db import DATABASE_PATH, create_connection, init_db


DEMO_SOURCE_WHERE = """
    COALESCE(source_type, '') = 'local_static'
    OR COALESCE(url, '') LIKE '%127.0.0.1%'
    OR COALESCE(url, '') LIKE '%localhost%'
    OR COALESCE(name, '') LIKE '%测试%'
    OR COALESCE(description, '') LIKE '%测试%'
    OR COALESCE(name, '') LIKE '%示例%'
    OR (
        COALESCE(parser_type, '') = 'manual_upload'
        AND COALESCE(description, '') LIKE '%示例%'
    )
"""


def scalar(conn, sql: str, params: tuple = ()) -> int:
    value = conn.execute(sql, params).fetchone()[0]
    return int(value or 0)


def prepare_demo_dataset() -> dict:
    init_db()
    conn = create_connection()
    try:
        conn.execute(
            f"""
            UPDATE raw_data_sources
            SET is_demo = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE {DEMO_SOURCE_WHERE}
            """
        )
        conn.commit()

        demo_sources_count = scalar(
            conn,
            "SELECT COUNT(*) FROM raw_data_sources WHERE COALESCE(is_demo, 0) = 1",
        )
        real_sources_count = scalar(
            conn,
            "SELECT COUNT(*) FROM raw_data_sources WHERE COALESCE(is_demo, 0) != 1",
        )
        verified_admissions_count = scalar(
            conn,
            "SELECT COUNT(*) FROM admissions WHERE COALESCE(is_verified, 0) = 1",
        )
        raw_records_count = scalar(conn, "SELECT COUNT(*) FROM raw_admission_records")
        schools_in_verified_admissions = scalar(
            conn,
            """
            SELECT COUNT(DISTINCT schools.name)
            FROM admissions
            JOIN schools ON schools.id = admissions.school_id
            WHERE COALESCE(admissions.is_verified, 0) = 1
            """,
        )

        return {
            "database": str(DATABASE_PATH),
            "demo_sources_count": demo_sources_count,
            "real_sources_count": real_sources_count,
            "verified_admissions_count": verified_admissions_count,
            "raw_records_count": raw_records_count,
            "schools_in_verified_admissions": schools_in_verified_admissions,
            "note": "Only marked demo/test sources with is_demo=1. No records were deleted.",
        }
    finally:
        conn.close()


if __name__ == "__main__":
    print(json.dumps(prepare_demo_dataset(), ensure_ascii=False, indent=2))
