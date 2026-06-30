"""列出需要人工确认的搜索候选 raw_data_sources。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db import create_connection, init_db  # noqa: E402


def main() -> None:
    init_db()
    conn = create_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, name, url, description
            FROM raw_data_sources
            WHERE enabled = 0
              AND description LIKE '%搜索候选%'
            ORDER BY id DESC
            """
        ).fetchall()
    finally:
        conn.close()

    print(f"待确认搜索候选数量：{len(rows)}")
    for row in rows:
        data = dict(row)
        description = data.get("description") or ""
        score = ""
        for part in description.split("；"):
            if part.startswith("score="):
                score = part.replace("score=", "")
                break
        print("-" * 80)
        print(f"id={data.get('id')}")
        print(f"name={data.get('name')}")
        print(f"url={data.get('url')}")
        print(f"score={score}")
        print(f"description={description}")


if __name__ == "__main__":
    main()
