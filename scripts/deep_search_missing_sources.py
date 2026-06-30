"""深度搜索缺失学校候选数据源。"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.deep_missing_source_service import deep_search_missing_school_sources  # noqa: E402


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="深度搜索缺失学校候选数据源")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--min-candidate-score", type=int, default=35)
    args = parser.parse_args()

    results = deep_search_missing_school_sources(
        limit=args.limit,
        min_candidate_score=args.min_candidate_score,
    )
    for item in results:
        print("-" * 80)
        print(f"school_name={item.get('school_name')}")
        print(f"candidates_found={item.get('candidates_found')}")
        print(f"candidates_created={item.get('candidates_created')}")
        for candidate in item.get("top_candidates", [])[:3]:
            print(f"  score={candidate.get('score')} url={candidate.get('url')}")
