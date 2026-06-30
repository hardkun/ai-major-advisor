"""对候选源执行官方性过滤，并每校只保留 Top N。"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.official_source_service import (  # noqa: E402
    apply_official_filter_to_candidates,
    keep_top_official_candidates_per_school,
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="过滤官方候选源")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--top", type=int, default=3)
    args = parser.parse_args()

    filter_result = apply_official_filter_to_candidates(limit=args.limit)
    top_result = keep_top_official_candidates_per_school(max_per_school=args.top)
    print("official_filter:", filter_result)
    print("keep_top:", top_result)
