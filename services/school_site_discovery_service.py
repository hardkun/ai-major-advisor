"""通过可配置搜索 API 发现高校本科招生官网。"""

from urllib.parse import urlparse

from config import SEARCH_API_KEY, SEARCH_PROVIDER, SEARCH_RESULT_LIMIT
from services.search_provider_service import search_web


BAD_URL_KEYWORDS = [
    "baike.baidu",
    "zhihu",
    "weibo",
    "bilibili",
    "sohu",
    "sina",
    "163.com",
    "toutiao",
]

THIRD_PARTY_KEYWORDS = [
    "gaokao.cn",
    "youzy",
    "eol",
    "掌上高考",
    "chinadaily",
    "kaoyan",
]


def build_school_site_queries(school_name: str) -> list[str]:
    return [
        f"{school_name} 本科招生网",
        f"{school_name} 招生信息网",
        f"{school_name} 本科招生",
        f"{school_name} 招生网",
        f"{school_name} 2025 四川 分专业录取分数",
        f"{school_name} 2025 四川 专业录取分数",
        f"{school_name} 2025 录取分数统计",
    ]


def build_direct_score_page_queries(
    school_name: str,
    province: str = "四川",
    year: int = 2025,
) -> list[str]:
    """构造直接搜索分数页面/附件的查询词。"""
    return [
        f"{school_name} {year} {province} 分专业录取分数",
        f"{school_name} {year} {province} 专业录取分数",
        f"{school_name} {year} {province} 录取分数统计",
        f"{school_name} {year} {province} 最低分 最低位次",
        f"{school_name} {year} {province} 本科批 录取情况",
        f"{school_name} {year} {province} 分专业录取情况",
        f"{school_name} {year} {province} 录取分数 xlsx",
        f"{school_name} {year} {province} 录取分数 pdf",
        f"{school_name} {year} 各省分专业录取分数",
        f"{school_name} 历年录取分数 四川",
    ]


def build_deep_score_source_queries(
    school_name: str,
    province: str = "四川",
    year: int = 2025,
) -> list[str]:
    """为缺失学校构造更强的分数页/附件搜索 query。"""
    return [
        f"{school_name} {year} {province} 分专业录取分数",
        f"{school_name} {year} {province} 专业录取分数",
        f"{school_name} {year} {province} 录取分数统计",
        f"{school_name} {year} {province} 最低分 位次",
        f"{school_name} {year} {province} 本科批 录取情况",
        f"{school_name} {year} {province} 分专业录取情况",
        f"{school_name} {year} 各省分专业录取分数",
        f"{school_name} {year} 各省录取分数线",
        f"{school_name} 历年录取分数 四川",
        f"{school_name} 招生网 四川 录取分数",
        f"{school_name} 本科招生 四川 录取分数",
        f"{school_name} 录取查询 四川 2025",
        f"{school_name} 四川 xlsx 录取分数",
        f"{school_name} 四川 pdf 录取分数",
        f"site:edu.cn {school_name} 四川 分专业录取分数",
        f"site:edu.cn {school_name} 2025 录取分数",
        f"site:edu.cn {school_name} 最低位次",
        f"site:edu.cn {school_name} 招生网 录取分数",
    ]


def _contains_any(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in keywords)


def _is_school_subdomain(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    parts = host.split(".")
    return len(parts) >= 4 and host.endswith(".edu.cn")


def score_school_site_result(school_name: str, result: dict) -> int:
    title = result.get("title") or ""
    url = result.get("url") or ""
    snippet = result.get("snippet") or ""
    text = f"{title} {snippet}"
    url_title = f"{url} {title}"

    score = 0
    if school_name in text:
        score += 30
    if "edu.cn" in url.lower():
        score += 25
    if "本科招生" in url_title:
        score += 20
    if "招生信息网" in url_title:
        score += 20
    if "招生网" in url_title:
        score += 15
    if _contains_any(url, ["zsb", "zs", "bkzs", "admission", "recruit"]):
        score += 15
    if _contains_any(text, ["录取分数", "分专业录取", "最低分", "位次"]):
        score += 20
    if _is_school_subdomain(url):
        score += 15

    if _contains_any(url, BAD_URL_KEYWORDS):
        score -= 50
    if _contains_any(url, THIRD_PARTY_KEYWORDS):
        score -= 20

    if school_name and school_name not in text and "招生" not in text:
        score -= 30

    return score


def _combined_result_text(result: dict) -> str:
    return " ".join(
        [
            result.get("title") or "",
            result.get("snippet") or "",
            result.get("url") or "",
        ]
    )


def score_score_page_result(
    school_name: str,
    result: dict,
    province: str = "四川",
    year: int = 2025,
) -> int:
    """给搜索到的分数页面或附件结果打分。"""
    title = result.get("title") or ""
    snippet = result.get("snippet") or ""
    url = result.get("url") or ""
    text = f"{title} {snippet} {url}"
    lower_url = url.lower()

    score = 0
    if school_name and school_name in text:
        score += 30
    if province and province in text:
        score += 20
    if str(year) in text:
        score += 20
    if "分专业录取" in text:
        score += 30
    if "专业录取分数" in text:
        score += 25
    if "录取分数统计" in text:
        score += 25
    if "最低分" in text:
        score += 15
    if "最低位次" in text or "位次" in text:
        score += 15
    if lower_url.endswith((".xlsx", ".xls")):
        score += 30
    if lower_url.endswith(".pdf"):
        score += 20
    if "edu.cn" in lower_url:
        score += 20
    if _contains_any(lower_url, ["zsb", "zs", "bkzs", "admission", "recruit"]):
        score += 10

    if _contains_any(lower_url, BAD_URL_KEYWORDS):
        score -= 50
    if _contains_any(lower_url, THIRD_PARTY_KEYWORDS):
        score -= 40
    if _contains_any(text, ["招生章程", "章程"]):
        score -= 20
    if _contains_any(text, ["招生计划", "招生专业目录"]) and not _contains_any(
        text, ["录取分数", "最低分", "位次"]
    ):
        score -= 15

    return score


def score_deep_source_candidate(
    school_name: str,
    result: dict,
    province: str = "四川",
    year: int = 2025,
) -> int:
    """为深度搜索候选源评分。"""
    title = result.get("title") or ""
    snippet = result.get("snippet") or ""
    url = result.get("url") or ""
    text = f"{title} {snippet} {url}"
    lower_url = url.lower()

    score = 0
    if school_name and school_name in text:
        score += 30
    if province and province in text:
        score += 20
    if str(year) in text:
        score += 15
    if "分专业录取" in text:
        score += 35
    if "专业录取分数" in text:
        score += 30
    if "录取分数统计" in text:
        score += 25
    if "录取情况" in text:
        score += 15
    if "最低分" in text:
        score += 15
    if "最低位次" in text or "位次" in text:
        score += 15
    if lower_url.endswith((".xlsx", ".xls")):
        score += 35
    if lower_url.endswith(".csv"):
        score += 25
    if lower_url.endswith(".pdf"):
        score += 20
    if "edu.cn" in lower_url:
        score += 20
    if _contains_any(lower_url, ["zsb", "zs", "bkzs", "admission", "recruit", "enroll"]):
        score += 15
    if _is_school_subdomain(url):
        score += 15

    if _contains_any(lower_url, BAD_URL_KEYWORDS):
        score -= 50
    if _contains_any(lower_url, ["youzy", "gaokao.cn", "eol", "掌上高考", "志愿填报", "高考志愿", "优志愿"]):
        score -= 60
    if _contains_any(text, ["招生章程", "章程"]):
        score -= 20
    if _contains_any(text, ["招生计划", "招生专业目录"]) and not _contains_any(
        text, ["录取分数", "最低分", "位次"]
    ):
        score -= 15
    if _contains_any(text, ["新闻", "活动", "宣讲", "喜报"]) and not _contains_any(
        text, ["录取分数", "最低分", "位次", "分专业录取"]
    ):
        score -= 15
    if school_name and school_name not in text:
        score -= 50

    return score


def _is_obvious_admission_site(result: dict) -> bool:
    url = (result.get("url") or "").lower()
    title = result.get("title") or ""
    snippet = result.get("snippet") or ""
    text = f"{title} {snippet}"
    return (
        "edu.cn" in url
        and _contains_any(url, ["zsb", "zs", "bkzs", "admission", "recruit"])
        and _contains_any(text, ["本科招生", "招生信息网", "招生网", "录取分数", "分专业录取"])
    )


def discover_school_admission_site_by_search(school_name: str) -> dict:
    queries = build_school_site_queries(school_name)

    if not (SEARCH_PROVIDER and SEARCH_API_KEY):
        return {
            "school_name": school_name,
            "best_admission_site": None,
            "score": 0,
            "queries": queries,
            "candidates": [],
            "message": "缺少搜索配置：请配置 SEARCH_PROVIDER 和 SEARCH_API_KEY",
        }

    seen_urls = set()
    candidates = []
    stop_early = False

    for query in queries:
        results = search_web(query, limit=SEARCH_RESULT_LIMIT)
        for result in results:
            url = result.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            scored = dict(result)
            scored["query"] = query
            scored["score"] = score_school_site_result(school_name, result)
            candidates.append(scored)

            if scored["score"] >= 80 or _is_obvious_admission_site(scored):
                stop_early = True

        if stop_early:
            break

    candidates.sort(key=lambda item: item.get("score", 0), reverse=True)
    best = candidates[0] if candidates else None
    if not best or int(best.get("score") or 0) < 40:
        return {
            "school_name": school_name,
            "best_admission_site": None,
            "score": int(best.get("score") or 0) if best else 0,
            "queries": queries,
            "candidates": candidates[:20],
            "message": "未找到可靠招生官网，需要人工补充 admission_site",
        }

    return {
        "school_name": school_name,
        "best_admission_site": best.get("url"),
        "score": int(best.get("score") or 0),
        "queries": queries,
        "candidates": candidates[:20],
        "message": "已通过搜索 API 发现候选招生官网",
    }


def discover_score_pages_by_search(
    school_name: str,
    province: str = "四川",
    year: int = 2025,
    limit_per_query: int = 10,
) -> dict:
    """直接通过搜索 API 发现分数页面或 Excel/PDF 附件。"""
    queries = build_direct_score_page_queries(school_name, province=province, year=year)

    if not (SEARCH_PROVIDER and SEARCH_API_KEY):
        return {
            "school_name": school_name,
            "best_url": None,
            "best_score": 0,
            "queries": queries,
            "candidates": [],
            "message": "缺少搜索配置：请配置 SEARCH_PROVIDER 和 SEARCH_API_KEY",
        }

    seen_urls = set()
    candidates = []

    for query in queries:
        results = search_web(query, limit=limit_per_query or SEARCH_RESULT_LIMIT)
        for result in results:
            url = result.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            scored = dict(result)
            scored["query"] = query
            scored["score"] = score_score_page_result(
                school_name=school_name,
                result=result,
                province=province,
                year=year,
            )
            if scored["score"] >= 40:
                candidates.append(scored)

        # 高分结果已经足够明确时，避免继续消耗 API。
        if candidates and max(int(item.get("score") or 0) for item in candidates) >= 80:
            break

    candidates.sort(key=lambda item: int(item.get("score") or 0), reverse=True)
    best = candidates[0] if candidates else None
    best_score = int(best.get("score") or 0) if best else 0

    if best_score >= 60:
        message = "已通过搜索 API 直接发现可靠分数页面"
        best_url = best.get("url")
    elif 40 <= best_score <= 59:
        message = "发现搜索候选，但需要人工确认"
        best_url = best.get("url")
    else:
        message = "未找到可靠分数页面"
        best_url = None

    return {
        "school_name": school_name,
        "best_url": best_url,
        "best_score": best_score,
        "queries": queries,
        "candidates": candidates[:30],
        "message": message,
    }
