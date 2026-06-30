import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402
    SEARCH_API_KEY,
    SEARCH_API_URL,
    SEARCH_PROVIDER,
    SEARCH_RESULT_LIMIT,
)
from services.school_site_discovery_service import (  # noqa: E402
    build_school_site_queries,
    discover_school_admission_site_by_search,
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("school_name")
    args = parser.parse_args()

    print("query 列表：")
    for query in build_school_site_queries(args.school_name):
        print("-", query)

    result = discover_school_admission_site_by_search(args.school_name)
    print("\nbest_admission_site:", result.get("best_admission_site"))
    print("score:", result.get("score"))
    print("message:", result.get("message"))
    print("\ncandidates:")
    for candidate in result.get("candidates", []):
        print(candidate)

    if not result.get("candidates"):
        print("\n未返回搜索候选结果，请检查：")
        print("1. SEARCH_PROVIDER 是否为 bocha")
        print("2. SEARCH_API_KEY 是否正确")
        print("3. SEARCH_API_URL 是否为 https://api.bochaai.com/v1/web-search")
        print("4. 博查账户余额 / 权限 / 额度是否正常")
        print("5. 当前网络是否可以访问博查 API")
        print("\n当前搜索配置：")
        print("SEARCH_PROVIDER:", SEARCH_PROVIDER)
        print("SEARCH_API_URL:", SEARCH_API_URL)
        print("SEARCH_API_KEY 已读取:", bool(SEARCH_API_KEY))
        print("SEARCH_RESULT_LIMIT:", SEARCH_RESULT_LIMIT)
