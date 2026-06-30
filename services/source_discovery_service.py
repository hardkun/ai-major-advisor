"""公开招生官网的数据源发现服务。

发现流程：
1. 如果已有 admission_site，只访问该招生官网入口首页，提取候选链接。
2. 如果 admission_site 为空且 allow_search=True，则通过配置的搜索 API 先发现招生官网。
3. 不抓取搜索引擎 HTML，不递归爬站，不绕过登录/验证码/权限限制。
"""

import json
import time
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from db import BASE_DIR
from services.school_site_discovery_service import (
    discover_school_admission_site_by_search,
    discover_score_pages_by_search,
)


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)

KEYWORDS_PATH = BASE_DIR / "data_sources" / "source_discovery_keywords.txt"


def load_discovery_keywords(path: str | Path = KEYWORDS_PATH) -> list[str]:
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = BASE_DIR / file_path
    if not file_path.exists():
        return ["四川", "2025", "专业录取分数", "最低分", "最低位次", "位次"]

    return [
        line.strip()
        for line in file_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _download_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        content = response.read()
        charset = response.headers.get_content_charset()

    for encoding in [charset, "utf-8", "utf-8-sig", "gb18030", "gbk"]:
        if not encoding:
            continue
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _score_candidate(text: str, url: str, keywords: list[str]) -> int:
    haystack = f"{text} {url}".lower()
    score = 0
    for keyword in keywords:
        if keyword.lower() in haystack:
            score += 10

    if "2025" in haystack:
        score += 8
    if "四川" in haystack:
        score += 8
    if any(word in haystack for word in ["分专业", "专业录取", "录取分数"]):
        score += 12
    if any(word in haystack for word in ["最低分", "最低位次", "位次"]):
        score += 8
    return score


def _discover_score_page_from_site(
    school_name: str,
    admission_site: str,
) -> dict:
    keywords = load_discovery_keywords()
    try:
        # 合规限速：每个站点请求前至少等待 1 秒。
        time.sleep(1)
        html = _download_html(admission_site)
        soup = BeautifulSoup(html, "html.parser")
        candidates = []

        for link in soup.find_all("a"):
            href = link.get("href")
            if not href:
                continue
            text = link.get_text(" ", strip=True)
            absolute_url = urljoin(admission_site, href)
            score = _score_candidate(text, absolute_url, keywords)
            if score <= 0:
                continue
            candidates.append(
                {
                    "text": text,
                    "url": absolute_url,
                    "score": score,
                }
            )

        candidates.sort(key=lambda item: item["score"], reverse=True)
        best = candidates[0] if candidates else None
        return {
            "school_name": school_name,
            "admission_site": admission_site,
            "candidate_urls": candidates[:20],
            "best_url": best["url"] if best else None,
            "score": best["score"] if best else 0,
            "message": "发现候选页面" if best else "未在招生官网首页发现匹配链接，需要人工处理",
        }
    except Exception as exc:
        return {
            "school_name": school_name,
            "admission_site": admission_site,
            "candidate_urls": [],
            "best_url": None,
            "score": 0,
            "message": f"发现失败：{exc}",
        }


def discover_sources_for_school(
    school_name: str,
    admission_site: str | None = None,
    allow_search: bool = False,
    province: str = "四川",
    year: int = 2025,
) -> dict:
    """为单所高校发现可能的四川 2025 分专业录取分数页面。"""
    search_result = None
    discovered_admission_site = None
    search_candidates = []
    direct_search_result = None

    def direct_score_fallback(reason: str) -> dict:
        nonlocal direct_search_result
        if not allow_search:
            return {
                "school_name": school_name,
                "admission_site": admission_site,
                "discovered_admission_site": discovered_admission_site,
                "discovered_score_url": None,
                "search_candidates": search_candidates,
                "candidate_urls": [],
                "best_url": None,
                "score": 0,
                "best_score": 0,
                "discovery_mode": "none",
                "message": reason,
                "search_candidates_json": json.dumps(search_candidates, ensure_ascii=False),
            }

        direct_search_result = discover_score_pages_by_search(
            school_name=school_name,
            province=province,
            year=year,
        )
        direct_candidates = direct_search_result.get("candidates", [])
        all_candidates = search_candidates + direct_candidates
        best_url = direct_search_result.get("best_url")
        best_score = int(direct_search_result.get("best_score") or 0)
        mode = "direct_score_page" if best_url else "none"
        return {
            "school_name": school_name,
            "admission_site": admission_site,
            "discovered_admission_site": discovered_admission_site,
            "discovered_score_url": best_url,
            "search_candidates": all_candidates,
            "candidate_urls": [],
            "best_url": best_url,
            "score": best_score,
            "best_score": best_score,
            "discovery_mode": mode,
            "message": f"{reason}；{direct_search_result.get('message')}；direct candidates={len(direct_candidates)}",
            "search_candidates_json": json.dumps(all_candidates, ensure_ascii=False),
        }

    if not admission_site:
        if not allow_search:
            return {
                "school_name": school_name,
                "admission_site": None,
                "discovered_admission_site": None,
                "discovered_score_url": None,
                "search_candidates": [],
                "candidate_urls": [],
                "best_url": None,
                "score": 0,
                "best_score": 0,
                "discovery_mode": "none",
                "message": "缺少招生官网入口，需要人工补充 admission_site；如需自动搜索请使用 --use-search",
            }

        search_result = discover_school_admission_site_by_search(school_name)
        search_candidates = search_result.get("candidates", [])
        if search_result.get("best_admission_site") and int(search_result.get("score") or 0) >= 40:
            admission_site = search_result["best_admission_site"]
            discovered_admission_site = admission_site
        else:
            return direct_score_fallback(
                f"未找到可靠招生官网，需要人工补充 admission_site；search candidates={len(search_candidates)}"
            )

    site_discovery = _discover_score_page_from_site(school_name, admission_site)
    site_score = int(site_discovery.get("score") or 0)
    site_best_url = site_discovery.get("best_url")

    # 站内发现结果分数较低或没有候选时，使用直接搜索分数页面兜底。
    if allow_search and (not site_best_url or site_score < 40):
        return direct_score_fallback(
            f"招生官网站内未发现高可信分数页面；site_score={site_score}"
        )

    site_discovery["discovered_admission_site"] = discovered_admission_site
    site_discovery["discovered_score_url"] = site_best_url
    site_discovery["best_score"] = site_score
    site_discovery["discovery_mode"] = "mixed" if discovered_admission_site else "admission_site"
    site_discovery["search_candidates"] = search_candidates if discovered_admission_site else []
    if discovered_admission_site:
        site_discovery["message"] = (
            f"{site_discovery.get('message')}；"
            f"discovered_admission_site={discovered_admission_site}；"
            f"score={search_result.get('score') if search_result else 0}；"
            f"search candidates={len(search_candidates)}"
        )

    # 方便任务表保存可追溯搜索结果。
    site_discovery["search_candidates_json"] = json.dumps(
        site_discovery.get("search_candidates", []),
        ensure_ascii=False,
    )
    return site_discovery
