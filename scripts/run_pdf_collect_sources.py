"""批量预览或采集 parser_type=pdf 的 raw_data_sources。

示例：
python scripts/run_pdf_collect_sources.py --limit 10 --preview-only
python scripts/run_pdf_collect_sources.py --limit 10
"""

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from collectors.pdf_collector import collect_pdf_source  # noqa: E402
from db import create_connection, init_db  # noqa: E402


def list_pdf_sources(limit: int) -> list[dict]:
    conn = create_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM raw_data_sources
            WHERE enabled = 1
              AND parser_type = 'pdf'
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="批量预览或采集 PDF 数据源")
    parser.add_argument("--limit", type=int, default=10, help="最多处理多少个 PDF 数据源")
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="只预览解析，不写入 raw_admission_records",
    )
    args = parser.parse_args()

    init_db()
    sources = list_pdf_sources(args.limit)
    print(f"待处理 PDF 数据源数量：{len(sources)}")

    for source in sources:
        print("-" * 80)
        print(f"source_id={source['id']} name={source.get('name')}")
        try:
            result = collect_pdf_source(source, preview=args.preview_only)
            print(f"parser_type={result.get('parser_type')}")
            print(f"preview={result.get('preview')}")
            print(f"would_insert_count={result.get('would_insert_count')}")
            print(f"inserted_count={result.get('inserted_count')}")
            print(f"skipped_count={result.get('skipped_count')}")
            print(f"duplicate_skipped_count={result.get('duplicate_skipped_count')}")
            print(f"filter_skipped_count={result.get('filter_skipped_count')}")
            print(f"empty_major_skipped_count={result.get('empty_major_skipped_count')}")
            print(f"error_count={result.get('error_count')}")
            print(f"detected_headers={result.get('detected_headers')}")
            print(f"message={result.get('message')}")
        except Exception as exc:
            print(f"PDF 数据源处理失败：{exc}")


if __name__ == "__main__":
    main()
