"""列出 pending 且通过官方性校验的候选源。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.source_candidate_service import list_source_candidates  # noqa: E402


if __name__ == "__main__":
    candidates = list_source_candidates(limit=300, include_all=False)
    print(f"pending_official_candidate_count={len(candidates)}")
    for item in candidates:
        print("-" * 80)
        print(f"id={item.get('id')}")
        print(f"school_name={item.get('school_name')}")
        print(f"official_score={item.get('official_score')}")
        print(f"discovery_score={item.get('discovery_score')}")
        print(f"parser_type={item.get('parser_type')}")
        print(f"url={item.get('url')}")
        print(f"official_check_message={item.get('official_check_message')}")
