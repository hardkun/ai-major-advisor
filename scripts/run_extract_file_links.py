import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.bulk_source_pipeline import run_extract_file_links_for_html_with_files  # noqa: E402


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    for item in run_extract_file_links_for_html_with_files(limit=args.limit):
        print(item)
