"""可配置搜索 API Provider。

本服务不抓取搜索引擎 HTML 页面，只调用用户配置的搜索 API。
未配置 SEARCH_PROVIDER 或 SEARCH_API_KEY 时，直接返回空列表。
"""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import (
    SEARCH_API_KEY,
    SEARCH_API_URL,
    SEARCH_DEBUG,
    SEARCH_PROVIDER,
    SEARCH_RESULT_LIMIT,
)


BOCHA_MAX_RETRIES = 3
BOCHA_TIMEOUT_SECONDS = 30
BOCHA_RETRY_SLEEP_SECONDS = 2
BOCHA_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
BOCHA_NO_RETRY_STATUS_CODES = {401, 403}


def _normalize_result(item: dict, source: str) -> dict | None:
    title = item.get("title") or item.get("name") or ""
    url = item.get("link") or item.get("url") or item.get("href") or ""
    snippet = item.get("snippet") or item.get("description") or item.get("summary") or ""
    if not url:
        return None
    return {
        "title": title,
        "url": url,
        "snippet": snippet,
        "source": source,
    }


def _extract_items(data: dict) -> list[dict]:
    for key in ["organic", "results", "items"]:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def _post_json(url: str, headers: dict, payload: dict, timeout: int = 20) -> dict:
    """优先使用 requests.post；如果环境未安装 requests，则回退到 urllib。"""
    try:
        import requests  # type: ignore

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except ModuleNotFoundError:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=timeout) as response:
            content = response.read().decode("utf-8", errors="ignore")
        return json.loads(content)


def _search_serper(query: str, limit: int) -> list[dict]:
    payload = _post_json(
        SEARCH_API_URL,
        {
            "X-API-KEY": SEARCH_API_KEY,
            "Content-Type": "application/json",
        },
        {"q": query, "num": limit},
    )
    results = []
    for item in payload.get("organic", []):
        normalized = _normalize_result(item, "serper")
        if normalized:
            results.append(normalized)
    return results


def _search_generic(query: str, limit: int) -> list[dict]:
    payload = _post_json(
        SEARCH_API_URL,
        {
            "Authorization": f"Bearer {SEARCH_API_KEY}",
            "Content-Type": "application/json",
        },
        {"query": query, "limit": limit},
    )
    results = []
    for item in _extract_items(payload):
        normalized = _normalize_result(item, "generic")
        if normalized:
            results.append(normalized)
    return results


def _post_bocha_once(request_body: dict, headers: dict) -> tuple[dict | None, bool]:
    """调用一次博查 API，返回 (payload, should_retry)。"""
    try:
        import requests  # type: ignore

        response = requests.post(
            SEARCH_API_URL,
            headers=headers,
            json=request_body,
            timeout=BOCHA_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            print(
                f"Bocha 搜索 HTTP 状态码：{response.status_code}，"
                f"响应：{response.text[:500]}"
            )
            if response.status_code in BOCHA_NO_RETRY_STATUS_CODES:
                return None, False
            return None, response.status_code in BOCHA_RETRY_STATUS_CODES

        return response.json(), False
    except ModuleNotFoundError:
        request = Request(
            SEARCH_API_URL,
            data=json.dumps(request_body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=BOCHA_TIMEOUT_SECONDS) as response:
                response_text = response.read().decode("utf-8", errors="ignore")
                return json.loads(response_text), False
        except HTTPError as exc:
            response_text = exc.read().decode("utf-8", errors="ignore")
            print(
                f"Bocha 搜索 HTTP 状态码：{exc.code}，"
                f"响应：{response_text[:500]}"
            )
            if exc.code in BOCHA_NO_RETRY_STATUS_CODES:
                return None, False
            return None, exc.code in BOCHA_RETRY_STATUS_CODES


def _extract_bocha_items(payload: dict) -> list[dict]:
    if payload.get("code") is not None and payload.get("code") != 200:
        print(f"Bocha 搜索返回 code={payload.get('code')}，msg={payload.get('msg')}")
        return []

    root = payload.get("data") or payload

    if SEARCH_DEBUG:
        print("Bocha payload keys:", list(payload.keys()))
        if isinstance(root, dict):
            print("Bocha data keys:", list(root.keys()))

    items = []
    if isinstance(root, dict):
        items = root.get("webPages", {}).get("value", [])
        if not items:
            items = root.get("webpages", {}).get("value", [])
        if not items:
            items = root.get("results", [])
        if not items:
            items = root.get("organic", [])
        if not items:
            items = root.get("items", [])

    if SEARCH_DEBUG:
        print("Bocha items count:", len(items) if isinstance(items, list) else 0)

    return items if isinstance(items, list) else []


def _bocha_items_to_results(items: list[dict]) -> list[dict]:
    results = []
    for item in items:
        url = item.get("url") or item.get("link") or ""
        if not url:
            continue
        results.append(
            {
                "title": item.get("name") or item.get("title") or "",
                "url": url,
                "snippet": (
                    item.get("snippet")
                    or item.get("summary")
                    or item.get("description")
                    or ""
                ),
                "source": "bocha",
                "site_name": item.get("siteName") or item.get("site_name"),
                "date_published": item.get("datePublished")
                or item.get("date_published"),
            }
        )
    return results


def search_bocha(query: str, limit: int = 10) -> list[dict]:
    """调用博查 Bocha Web Search API，带轻量重试。"""
    api_key = (SEARCH_API_KEY or "").strip()
    api_url = (SEARCH_API_URL or "").strip()
    safe_limit = max(1, min(int(limit or SEARCH_RESULT_LIMIT or 10), 50))

    if not api_key or not api_url:
        print("Bocha 搜索配置缺失")
        return []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    request_body = {
        "query": query,
        "freshness": "oneYear",
        "summary": True,
        "count": safe_limit,
    }

    for attempt in range(1, BOCHA_MAX_RETRIES + 1):
        try:
            payload, should_retry = _post_bocha_once(request_body, headers)
            if not payload:
                if should_retry and attempt < BOCHA_MAX_RETRIES:
                    time.sleep(BOCHA_RETRY_SLEEP_SECONDS)
                    continue
                return []

            items = _extract_bocha_items(payload)
            results = _bocha_items_to_results(items)
            return results
        except (TimeoutError, ConnectionError, URLError, OSError) as exc:
            print(f"Bocha 搜索第 {attempt} 次失败：{exc}")
            if attempt < BOCHA_MAX_RETRIES:
                time.sleep(BOCHA_RETRY_SLEEP_SECONDS)
                continue
            return []
        except Exception as exc:
            print(f"Bocha 搜索第 {attempt} 次失败：{exc}")
            if attempt < BOCHA_MAX_RETRIES:
                time.sleep(BOCHA_RETRY_SLEEP_SECONDS)
                continue
            return []

    return []


def search_web(query: str, limit: int = 10) -> list[dict]:
    """调用配置的搜索 API，返回统一格式结果。

    未配置时返回空列表，不抛异常，方便批量任务安全运行。
    """
    provider = (SEARCH_PROVIDER or "").strip().lower()
    api_key = (SEARCH_API_KEY or "").strip()
    api_url = (SEARCH_API_URL or "").strip()
    safe_limit = max(1, min(int(limit or SEARCH_RESULT_LIMIT or 10), 50))

    if not provider or not api_key or not api_url:
        return []

    try:
        if provider == "serper":
            return _search_serper(query, safe_limit)
        if provider == "generic":
            return _search_generic(query, safe_limit)
        if provider == "bocha":
            return search_bocha(query, safe_limit)

        print(f"不支持的 SEARCH_PROVIDER：{provider}")
        return []
    except Exception as exc:
        print(f"搜索 API 调用失败：{exc}")
        return []
