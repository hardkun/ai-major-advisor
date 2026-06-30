"""列出待人工确认的候选数据源。"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.source_candidate_service import list_source_candidates  # noqa: E402


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="列出候选数据源")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    candidates = list_source_candidates(limit=args.limit)
    print(f"candidate_count={len(candidates)}")
    for item in candidates:
        print("-" * 80)
        print(f"id={item.get('id')}")
        print(f"school_name={item.get('school_name')}")
        print(f"score={item.get('discovery_score')}")
        print(f"parser_type={item.get('parser_type')}")
        print(f"candidate_status={item.get('candidate_status')}")
        print(f"url={item.get('url')}")
        print(f"description={item.get('description')}")
