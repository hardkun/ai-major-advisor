import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.bulk_source_pipeline import (  # noqa: E402
    reset_missing_site_skipped_tasks,
    run_discovery_tasks,
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "运行 source_discovery_tasks。示例：\n"
            "1. python scripts/import_school_seed.py\n"
            "2. python scripts/run_discovery_tasks.py --limit 10 --use-search --reset-missing-site-skipped\n"
            "3. python scripts/run_discovery_tasks.py --limit 10 --use-search --retry-skipped"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--use-search",
        action="store_true",
        help="允许 admission_site 为空时调用配置的搜索 API 自动寻找招生官网。",
    )
    parser.add_argument(
        "--retry-skipped",
        action="store_true",
        help="任务查询范围包含 status=pending 和 status=skipped；不会重跑 success 任务。",
    )
    parser.add_argument(
        "--reset-missing-site-skipped",
        action="store_true",
        help="执行前将 message 包含“缺少招生官网入口”的 skipped 任务重置为 pending。",
    )
    args = parser.parse_args()

    if args.reset_missing_site_skipped:
        reset_count = reset_missing_site_skipped_tasks()
        print(f"已重置缺少招生官网的 skipped 任务数量：{reset_count}")

    results = run_discovery_tasks(
        limit=args.limit,
        use_search=args.use_search,
        retry_skipped=args.retry_skipped,
    )
    for item in results:
        print("-" * 80)
        print(f"task_id={item.get('task_id')}")
        print(f"school_name={item.get('school_name')}")
        print(f"status={item.get('status')}")
        print(f"discovery_mode={item.get('discovery_mode')}")
        print(f"discovered_admission_site={item.get('discovered_admission_site')}")
        print(f"discovered_score_url={item.get('discovered_score_url') or item.get('best_url')}")
        print(f"best_score={item.get('best_score') or item.get('score')}")
        print(f"candidate_count={item.get('candidate_count')}")
        print(f"source_id={item.get('source_id')}")
        print(f"message={item.get('message')}")
