"""回填 raw_data_sources.school_name，并标记测试/示例源。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.source_backfill_service import backfill_raw_data_source_school_names  # noqa: E402


if __name__ == "__main__":
    result = backfill_raw_data_source_school_names()
    print(result)
