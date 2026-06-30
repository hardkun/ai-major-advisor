"""数据覆盖率报告服务。

正式覆盖率只统计 seed 学校和正式数据源：
- 排除本地测试源、示例源、manual_upload、低置信候选源
- schools_with_sources 按 seed school_name 去重，不按 raw_data_sources 数量统计
"""

import json

from db import create_connection, init_db
from services.source_backfill_service import load_seed_school_names


def _load_ai_keywords() -> list[str]:
    from db import BASE_DIR

    path = BASE_DIR / "data_sources" / "ai_major_keywords.txt"
    if not path.exists():
        return ["人工智能", "计算机", "软件工程", "数据科学"]
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _ai_major_where_clause(keywords: list[str], table_alias: str = "") -> tuple[str, list[str]]:
    prefix = f"{table_alias}." if table_alias else ""
    parts = []
    params = []
    for keyword in keywords:
        parts.append(
            f"(COALESCE({prefix}major_name, '') LIKE ? OR COALESCE({prefix}direction_tags, '') LIKE ?)"
        )
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    return " OR ".join(parts) or "1 = 0", params


def _seed_placeholders(seed_school_names: list[str]) -> str:
    return ",".join(["?"] * len(seed_school_names)) if seed_school_names else "''"


def _formal_source_where(alias: str = "raw_data_sources") -> str:
    prefix = f"{alias}."
    return f"""
        COALESCE({prefix}is_demo, 0) != 1
        AND COALESCE({prefix}is_candidate, 0) != 1
        AND COALESCE({prefix}reference_only, 0) != 1
        AND COALESCE({prefix}candidate_status, '') != 'rejected'
        AND COALESCE({prefix}official_check_status, '') != 'rejected'
        AND COALESCE({prefix}source_type, '') != 'local_static'
        AND COALESCE({prefix}parser_type, '') != 'manual_upload'
        AND COALESCE({prefix}url, '') NOT LIKE '%127.0.0.1%'
        AND COALESCE({prefix}url, '') NOT LIKE '%localhost%'
        AND COALESCE({prefix}name, '') NOT LIKE '%示例%'
        AND COALESCE({prefix}name, '') NOT LIKE '%测试%'
        AND COALESCE({prefix}description, '') NOT LIKE '%示例%'
        AND COALESCE({prefix}description, '') NOT LIKE '%测试%'
    """


def _failed_source_is_formal(item: dict) -> bool:
    text = " ".join(
        str(item.get(field) or "")
        for field in ["source_name", "name", "description", "url", "parser_type", "source_type"]
    )
    lower = text.lower()
    return not (
        item.get("is_demo") == 1
        or item.get("is_candidate") == 1
        or item.get("reference_only") == 1
        or item.get("candidate_status") == "rejected"
        or item.get("official_check_status") == "rejected"
        or item.get("source_type") == "local_static"
        or item.get("parser_type") == "manual_upload"
        or "127.0.0.1" in lower
        or "localhost" in lower
        or "示例" in text
        or "测试" in text
        or "demo" in lower
        or "example" in lower
    )


def _count_raw_records_for_school(conn, school_name: str, province: str, year: int) -> int:
    return conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM raw_admission_records
        WHERE school_name = ?
          AND admission_province = ?
          AND admission_year = ?
        """,
        (school_name, province, year),
    ).fetchone()["count"]


def _count_verified_records_for_school(conn, school_name: str, province: str, year: int) -> int:
    return conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM admissions
        JOIN schools ON schools.id = admissions.school_id
        WHERE schools.name = ?
          AND admissions.province = ?
          AND admissions.year = ?
          AND COALESCE(admissions.is_verified, 0) = 1
          AND admissions.source_id IS NOT NULL
        """,
        (school_name, province, year),
    ).fetchone()["count"]


def _school_has_formal_source(conn, school_name: str) -> bool:
    return (
        conn.execute(
            f"""
            SELECT 1
            FROM raw_data_sources
            WHERE school_name = ?
              AND {_formal_source_where()}
            LIMIT 1
            """,
            (school_name,),
        ).fetchone()
        is not None
    )


def _school_has_candidate_source(conn, school_name: str) -> bool:
    return (
        conn.execute(
            """
            SELECT 1
            FROM raw_data_sources
            WHERE school_name = ?
              AND COALESCE(is_candidate, 0) = 1
            LIMIT 1
            """,
            (school_name,),
        ).fetchone()
        is not None
    )


def _school_has_failed_check_source(conn, school_name: str) -> bool:
    return (
        conn.execute(
            f"""
            SELECT 1
            FROM raw_data_sources
            WHERE school_name = ?
              AND {_formal_source_where()}
              AND last_check_status = 'failed'
            LIMIT 1
            """,
            (school_name,),
        ).fetchone()
        is not None
    )


def generate_coverage_report(province: str = "四川", year: int = 2025) -> dict:
    """生成并保存当前数据覆盖率报告。"""
    init_db()
    seed_school_names = load_seed_school_names()
    total_schools = len(seed_school_names)
    placeholders = _seed_placeholders(seed_school_names)

    conn = create_connection()
    try:
        if seed_school_names:
            schools_with_sources = conn.execute(
                f"""
                SELECT COUNT(DISTINCT school_name) AS count
                FROM raw_data_sources
                WHERE school_name IN ({placeholders})
                  AND {_formal_source_where()}
                """,
                seed_school_names,
            ).fetchone()["count"]

            sources_detected = conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM raw_data_sources
                WHERE school_name IN ({placeholders})
                  AND {_formal_source_where()}
                  AND last_check_status = 'success'
                  AND COALESCE(last_detected_type, '') != ''
                """,
                seed_school_names,
            ).fetchone()["count"]

            sources_collected = conn.execute(
                f"""
                SELECT COUNT(DISTINCT raw_data_sources.id) AS count
                FROM raw_data_sources
                WHERE raw_data_sources.school_name IN ({placeholders})
                  AND {_formal_source_where()}
                  AND EXISTS (
                        SELECT 1
                        FROM raw_admission_records
                        WHERE raw_admission_records.school_name = raw_data_sources.school_name
                  )
                  AND EXISTS (
                        SELECT 1
                        FROM collector_runs
                        WHERE collector_runs.raw_source_id = raw_data_sources.id
                          AND collector_runs.status IN ('success', 'partial', 'skipped')
                  )
                """,
                seed_school_names,
            ).fetchone()["count"]

            raw_records_count = conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM raw_admission_records
                WHERE school_name IN ({placeholders})
                  AND admission_province = ?
                  AND admission_year = ?
                  AND COALESCE(source_name, '') != ''
                  AND COALESCE(source_url, '') != ''
                """,
                [*seed_school_names, province, year],
            ).fetchone()["count"]

            verified_records_count = conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM admissions
                JOIN schools ON schools.id = admissions.school_id
                WHERE schools.name IN ({placeholders})
                  AND admissions.province = ?
                  AND admissions.year = ?
                  AND COALESCE(admissions.is_verified, 0) = 1
                  AND admissions.source_id IS NOT NULL
                """,
                [*seed_school_names, province, year],
            ).fetchone()["count"]

            ai_where, ai_params = _ai_major_where_clause(_load_ai_keywords())
            ai_major_records_count = conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM raw_admission_records
                WHERE school_name IN ({placeholders})
                  AND admission_province = ?
                  AND admission_year = ?
                  AND ({ai_where})
                """,
                [*seed_school_names, province, year, *ai_params],
            ).fetchone()["count"]
        else:
            schools_with_sources = 0
            sources_detected = 0
            sources_collected = 0
            raw_records_count = 0
            verified_records_count = 0
            ai_major_records_count = 0

        missing_schools = []
        for school_name in seed_school_names:
            raw_count = _count_raw_records_for_school(conn, school_name, province, year)
            verified_count = _count_verified_records_for_school(conn, school_name, province, year)
            has_formal_source = _school_has_formal_source(conn, school_name)
            has_candidate = _school_has_candidate_source(conn, school_name)
            has_failed_check = _school_has_failed_check_source(conn, school_name)

            if not has_formal_source and has_candidate:
                reason = "仅有待确认候选源"
            elif not has_formal_source:
                reason = "未发现数据源"
            elif raw_count + verified_count == 0 and has_failed_check:
                reason = "数据源检测失败"
            elif raw_count + verified_count == 0:
                reason = "raw_records_count = 0"
            elif raw_count > 0 and verified_count == 0:
                reason = "已有 raw 待核验"
            else:
                continue

            missing_schools.append(
                {
                    "school_name": school_name,
                    "reason": reason,
                    "raw_records_count": raw_count,
                    "verified_records_count": verified_count,
                }
            )

        failed_sources_raw = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                    id AS source_id,
                    school_name,
                    name AS source_name,
                    url,
                    parser_type,
                    source_type,
                    description,
                    is_demo,
                    is_candidate,
                    reference_only,
                    candidate_status,
                    official_check_status,
                    last_check_status,
                    last_check_message
                FROM raw_data_sources
                WHERE last_check_status = 'failed'
                ORDER BY id DESC
                """
            ).fetchall()
        ]
        failed_sources = [
            item for item in failed_sources_raw if _failed_source_is_formal(item)
        ]
        excluded_sources = [
            item for item in failed_sources_raw if not _failed_source_is_formal(item)
        ]

        failed_collects_raw = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                    collector_runs.source_name,
                    collector_runs.parser_type,
                    collector_runs.status,
                    collector_runs.message,
                    raw_data_sources.school_name,
                    raw_data_sources.url,
                    raw_data_sources.description,
                    raw_data_sources.source_type,
                    raw_data_sources.is_demo,
                    raw_data_sources.is_candidate,
                    raw_data_sources.reference_only,
                    raw_data_sources.candidate_status,
                    raw_data_sources.official_check_status
                FROM collector_runs
                LEFT JOIN raw_data_sources ON raw_data_sources.id = collector_runs.raw_source_id
                WHERE collector_runs.status IN ('failed', 'partial')
                ORDER BY collector_runs.id DESC
                LIMIT 100
                """
            ).fetchall()
        ]
        failed_sources.extend(
            item for item in failed_collects_raw if _failed_source_is_formal(item)
        )
        excluded_sources.extend(
            item for item in failed_collects_raw if not _failed_source_is_formal(item)
        )

        report = {
            "report_name": f"{province}{year} AI相关专业数据覆盖率报告",
            "province": province,
            "year": year,
            "total_schools": total_schools,
            "schools_with_sources": schools_with_sources,
            "sources_detected": sources_detected,
            "sources_collected": sources_collected,
            "raw_records_count": raw_records_count,
            "verified_records_count": verified_records_count,
            "ai_major_records_count": ai_major_records_count,
            "missing_schools": missing_schools,
            "failed_sources": failed_sources,
            "excluded_sources": excluded_sources,
        }

        cursor = conn.execute(
            """
            INSERT INTO data_coverage_reports
                (report_name, province, year, total_schools, schools_with_sources,
                 sources_detected, sources_collected, raw_records_count,
                 verified_records_count, ai_major_records_count,
                 missing_schools_json, failed_sources_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report["report_name"],
                province,
                year,
                total_schools,
                schools_with_sources,
                sources_detected,
                sources_collected,
                raw_records_count,
                verified_records_count,
                ai_major_records_count,
                json.dumps(missing_schools, ensure_ascii=False),
                json.dumps(failed_sources, ensure_ascii=False),
            ),
        )
        conn.commit()
        report["id"] = cursor.lastrowid
        return report
    finally:
        conn.close()


def list_coverage_reports(limit: int = 20) -> list[dict]:
    init_db()
    limit = min(max(int(limit), 1), 100)
    conn = create_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM data_coverage_reports
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        reports = []
        for row in rows:
            data = dict(row)
            data["missing_schools"] = json.loads(data.pop("missing_schools_json") or "[]")
            data["failed_sources"] = json.loads(data.pop("failed_sources_json") or "[]")
            reports.append(data)
        return reports
    finally:
        conn.close()
