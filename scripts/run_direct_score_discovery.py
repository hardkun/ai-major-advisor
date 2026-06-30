"""直接搜索高校四川 2025 分专业录取分数页面/附件。

示例：
python scripts/run_direct_score_discovery.py --limit 20 --retry-missing
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db import create_connection, init_db  # noqa: E402
from services.bulk_source_pipeline import _upsert_raw_data_source  # noqa: E402
from services.school_site_discovery_service import discover_score_pages_by_search  # noqa: E402


def fetch_tasks(limit: int, retry_missing: bool) -> list[dict]:
    conn = create_connection()
    try:
        if retry_missing:
            rows = conn.execute(
                """
                SELECT * FROM source_discovery_tasks
                WHERE status IN ('pending', 'skipped', 'failed')
                   OR message LIKE '%未发现数据源%'
                   OR message LIKE '%未找到可靠%'
                   OR message LIKE '%缺少招生官网入口%'
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM source_discovery_tasks
                WHERE status = 'pending'
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_task(task_id: int, data: dict) -> None:
    allowed = {
        "status",
        "discovered_url",
        "discovered_score_url",
        "score",
        "message",
        "search_candidates_json",
        "discovery_mode",
    }
    update_data = {key: value for key, value in data.items() if key in allowed}
    if not update_data:
        return

    set_parts = [f"{key} = ?" for key in update_data]
    set_parts.append("updated_at = CURRENT_TIMESTAMP")
    values = list(update_data.values())
    values.append(task_id)

    conn = create_connection()
    try:
        conn.execute(
            f"""
            UPDATE source_discovery_tasks
            SET {", ".join(set_parts)}
            WHERE id = ?
            """,
            values,
        )
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="直接搜索分数页面/附件并创建 raw_data_sources")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--retry-missing", action="store_true", help="包含 skipped/failed/pending 缺口任务")
    parser.add_argument("--province", default="四川")
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()

    init_db()
    tasks = fetch_tasks(limit=args.limit, retry_missing=args.retry_missing)
    print(f"待直接搜索任务数量：{len(tasks)}")

    for task in tasks:
        school_name = task.get("school_name") or ""
        print("-" * 80)
        print(f"task_id={task['id']} school={school_name}")
        result = discover_score_pages_by_search(
            school_name=school_name,
            province=args.province,
            year=args.year,
        )
        best_url = result.get("best_url")
        best_score = int(result.get("best_score") or 0)
        candidates = result.get("candidates", [])
        source_id = None

        if best_url and best_score >= 60:
            source_id = _upsert_raw_data_source(
                school_name=school_name,
                url=best_url,
                enabled=True,
                description="搜索 API 直接发现分数页面",
                discovery_mode="direct_score_page",
                score=best_score,
            )
            status = "success"
            message = f"{result.get('message')}，已创建/更新 enabled 数据源 #{source_id}"
        elif best_url and 40 <= best_score <= 59:
            source_id = _upsert_raw_data_source(
                school_name=school_name,
                url=best_url,
                enabled=False,
                description="搜索候选，需人工确认",
                discovery_mode="direct_score_page",
                score=best_score,
            )
            status = "skipped"
            message = f"{result.get('message')}，已创建/更新 disabled 搜索候选 #{source_id}"
        else:
            status = "skipped"
            message = result.get("message") or "未找到可靠分数页面"

        update_task(
            task["id"],
            {
                "status": status,
                "discovered_url": best_url,
                "discovered_score_url": best_url,
                "score": best_score,
                "message": message,
                "search_candidates_json": json.dumps(candidates, ensure_ascii=False),
                "discovery_mode": "direct_score_page" if best_url else "none",
            },
        )

        print(f"best_url={best_url}")
        print(f"best_score={best_score}")
        print(f"candidate_count={len(candidates)}")
        print(f"source_id={source_id}")
        print(f"status={status}")
        print(f"message={message}")


if __name__ == "__main__":
    main()
