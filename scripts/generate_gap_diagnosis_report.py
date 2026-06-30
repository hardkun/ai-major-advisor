from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.gap_diagnosis_service import generate_gap_diagnosis_report  # noqa: E402


if __name__ == "__main__":
    report = generate_gap_diagnosis_report()

    print("缺口诊断概览：")
    print("total_schools:", report["total_schools"])
    print("schools_with_sources:", report["schools_with_sources"])
    print("schools_with_raw:", report["schools_with_raw"])
    print("schools_with_verified:", report["schools_with_verified"])
    print("missing_source_schools:", len(report["missing_source_schools"]))
    print("source_but_no_raw_schools:", len(report["source_but_no_raw_schools"]))
    print("failed_sources:", len(report["failed_sources"]))

    print("\n数据源类型分布：")
    for key, value in report["detected_type_distribution"].items():
        print(f"- {key}: {value}")

    print("\n优先处理队列前 20 条：")
    for item in report["priority_actions"][:20]:
        print(
            f"[P{item['priority']}] {item['action']} | "
            f"{item.get('school_name') or '-'} | "
            f"{item.get('source_name') or '-'} | "
            f"{item['reason']}"
        )
