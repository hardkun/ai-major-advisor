"""生成数据源下一步处理队列。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.action_queue_service import generate_source_action_queue  # noqa: E402


if __name__ == "__main__":
    report = generate_source_action_queue()
    print(f"total_actions={report['total_actions']}")
    print(f"action_distribution={report['action_distribution']}")
    for item in report["actions"][:50]:
        print("-" * 80)
        print(f"priority={item.get('priority')}")
        print(f"school_name={item.get('school_name')}")
        print(f"source_name={item.get('source_name')}")
        print(f"source_id={item.get('source_id')}")
        print(f"action={item.get('action')}")
        print(f"reason={item.get('reason')}")
