from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.bulk_source_pipeline import run_import_school_seed


if __name__ == "__main__":
    print(run_import_school_seed())
