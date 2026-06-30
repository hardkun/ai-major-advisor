"""raw_data_sources 学校归属与测试源标记回填。"""

import csv
from pathlib import Path

from db import BASE_DIR, create_connection, init_db


SEED_PATH = BASE_DIR / "data_sources" / "sichuan_2025_school_seed.csv"


def load_seed_school_names(path: Path = SEED_PATH) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return [
            (row.get("school_name") or "").strip()
            for row in reader
            if (row.get("school_name") or "").strip()
            and str(row.get("enabled", "1")).strip() != "0"
        ]


def _is_demo_source(source: dict) -> bool:
    text = " ".join(
        str(source.get(field) or "")
        for field in ["name", "url", "description", "source_type"]
    )
    lower = text.lower()
    return (
        source.get("source_type") == "local_static"
        or "127.0.0.1" in lower
        or "localhost" in lower
        or "示例" in text
        or "测试" in text
        or "demo" in lower
        or "example" in lower
    )


def _match_school_name(source: dict, school_names: list[str]) -> str | None:
    haystack = " ".join(
        str(source.get(field) or "")
        for field in ["name", "url", "description"]
    )
    for school_name in school_names:
        if school_name and school_name in haystack:
            return school_name
    return None


def backfill_raw_data_source_school_names() -> dict:
    """回填 raw_data_sources.school_name，并标记本地测试/示例源。"""
    init_db()
    school_names = load_seed_school_names()
    conn = create_connection()
    updated_school_name_count = 0
    marked_demo_count = 0
    marked_candidate_count = 0
    try:
        rows = [dict(row) for row in conn.execute("SELECT * FROM raw_data_sources").fetchall()]
        for source in rows:
            updates = {}

            if not source.get("school_name"):
                matched_school_name = _match_school_name(source, school_names)
                if matched_school_name:
                    updates["school_name"] = matched_school_name
                    updated_school_name_count += 1

            if _is_demo_source(source) and int(source.get("is_demo") or 0) != 1:
                updates["is_demo"] = 1
                if not source.get("discovery_mode"):
                    updates["discovery_mode"] = "local_test"
                marked_demo_count += 1

            description = source.get("description") or ""
            if "搜索候选" in description and int(source.get("is_candidate") or 0) != 1:
                updates["is_candidate"] = 1
                marked_candidate_count += 1

            if updates:
                set_parts = [f"{key} = ?" for key in updates]
                set_parts.append("updated_at = CURRENT_TIMESTAMP")
                values = list(updates.values())
                values.append(source["id"])
                conn.execute(
                    f"""
                    UPDATE raw_data_sources
                    SET {", ".join(set_parts)}
                    WHERE id = ?
                    """,
                    values,
                )

        conn.commit()
        return {
            "seed_school_count": len(school_names),
            "updated_school_name_count": updated_school_name_count,
            "marked_demo_count": marked_demo_count,
            "marked_candidate_count": marked_candidate_count,
        }
    finally:
        conn.close()
