import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.coverage_report_service import generate_coverage_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--province", default="四川")
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()
    print(generate_coverage_report(province=args.province, year=args.year))
