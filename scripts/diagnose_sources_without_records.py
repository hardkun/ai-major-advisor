"""批量诊断有正式数据源但 raw_records_count=0 的数据源。"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.collect_diagnosis_service import diagnose_sources_without_records  # noqa: E402


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="诊断有源无数据的数据源")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    for item in diagnose_sources_without_records(limit=args.limit):
        print("-" * 80)
        print(f"source_id={item.get('source_id')}")
        print(f"school_name={item.get('school_name')}")
        print(f"source_name={item.get('source_name')}")
        print(f"parser_type={item.get('parser_type')}")
        print(f"status={item.get('status')}")
        print(f"message={item.get('message')}")
