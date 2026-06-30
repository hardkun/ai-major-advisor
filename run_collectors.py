"""运行所有启用的自动采集器。

运行命令：
    python run_collectors.py
"""

from collectors.collector_runner import run_enabled_collectors


def main() -> None:
    results = run_enabled_collectors()

    total_inserted = 0
    total_skipped = 0
    total_errors = 0

    print("自动采集器运行完成")
    for result in results:
        inserted = result.get("inserted_count", 0)
        skipped = result.get("skipped_count", 0)
        errors = result.get("error_count", 0)
        total_inserted += inserted
        total_skipped += skipped
        total_errors += errors

        print(
            f"- source_id={result.get('source_id')} "
            f"parser_type={result.get('parser_type')} "
            f"inserted={inserted} skipped={skipped} error={errors}"
        )
        if result.get("error"):
            print(f"  error_message={result['error']}")

    print("汇总：")
    print(f"inserted={total_inserted}")
    print(f"skipped={total_skipped}")
    print(f"error={total_errors}")


if __name__ == "__main__":
    main()
