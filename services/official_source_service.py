"""候选数据源官方性判断与过滤。"""

import csv
from urllib.parse import urlparse

from db import BASE_DIR, create_connection, init_db


SEED_PATH = BASE_DIR / "data_sources" / "sichuan_2025_school_seed.csv"

THIRD_PARTY_KEYWORDS = [
    "baidu",
    "zhihu",
    "sohu",
    "sina",
    "163",
    "toutiao",
    "bilibili",
    "youzy",
    "gaokao.cn",
    "eol",
    "掌上高考",
    "优志愿",
    "高考志愿",
    "志愿填报",
    "大学生必备网",
    "高考升学网",
    "中国教育在线",
]


def load_school_domain_map() -> dict:
    """读取 seed 中的 official_domain / admission_domain 映射。"""
    if not SEED_PATH.exists():
        return {}

    result = {}
    with SEED_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            school_name = (row.get("school_name") or "").strip()
            if not school_name:
                continue
            result[school_name] = {
                "official_domain": (row.get("official_domain") or "").strip(),
                "admission_domain": (row.get("admission_domain") or "").strip(),
                "official_site": (row.get("official_site") or "").strip(),
                "admission_site": (row.get("admission_site") or "").strip(),
            }
    return result


def extract_domain(url: str) -> str:
    try:
        domain = urlparse(url or "").netloc.lower()
    except Exception:
        return ""
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def is_same_or_subdomain(domain: str, root_domain: str) -> bool:
    domain = (domain or "").lower().strip()
    root_domain = (root_domain or "").lower().strip()
    if not domain or not root_domain:
        return False
    return domain == root_domain or domain.endswith("." + root_domain)


def is_third_party_blocked(
    url: str,
    title: str = "",
    snippet: str = "",
) -> tuple[bool, str]:
    text = f"{url} {title} {snippet}".lower()
    for keyword in THIRD_PARTY_KEYWORDS:
        if keyword.lower() in text:
            return True, "第三方志愿/资讯平台，不作为正式数据源"
    return False, ""


def score_official_source(
    school_name: str,
    url: str,
    title: str = "",
    snippet: str = "",
) -> dict:
    blocked, reason = is_third_party_blocked(url, title=title, snippet=snippet)
    if blocked:
        return {
            "official_check_status": "rejected",
            "official_score": -100,
            "reference_only": 1,
            "message": reason,
        }

    domain_map = load_school_domain_map().get(school_name, {})
    official_domain = domain_map.get("official_domain")
    admission_domain = domain_map.get("admission_domain")
    domain = extract_domain(url)
    text = f"{url} {title} {snippet}"
    lower_url = (url or "").lower()
    score = 0
    reasons = []

    if admission_domain and is_same_or_subdomain(domain, admission_domain):
        score += 80
        reasons.append("命中招生官网域名")
    elif official_domain and is_same_or_subdomain(domain, official_domain):
        score += 60
        reasons.append("命中学校主域名")
    else:
        score -= 30
        reasons.append("未命中 seed 官方域名")

    if "edu.cn" in domain:
        score += 20
        reasons.append("edu.cn 域名")
    if any(word in text for word in ["本科招生", "招生网", "招生信息网"]):
        score += 20
        reasons.append("包含招生官网相关词")
    if any(word in text for word in ["录取分数", "分专业录取", "最低分", "位次"]):
        score += 20
        reasons.append("包含录取分数相关词")
    if lower_url.endswith((".xlsx", ".xls", ".pdf", ".csv")):
        score += 10
        reasons.append("URL 是常见附件类型")

    if any(word in text for word in ["招生章程", "章程"]):
        score -= 15
        reasons.append("疑似招生章程")
    if "招生计划" in text:
        score -= 10
        reasons.append("疑似招生计划")
    if any(word in text for word in ["新闻", "活动", "宣讲", "喜报"]) and not any(
        word in text for word in ["录取分数", "最低分", "位次", "分专业录取"]
    ):
        score -= 10
        reasons.append("疑似新闻宣传")

    if score >= 80:
        status = "official"
        reference_only = 0
    elif score >= 60:
        status = "likely_official"
        reference_only = 0
    elif score >= 30:
        status = "reference_only"
        reference_only = 1
    else:
        status = "rejected" if official_domain or admission_domain else "unknown"
        reference_only = 1

    return {
        "official_check_status": status,
        "official_score": score,
        "reference_only": reference_only,
        "message": "；".join(reasons) or "未获得明确官方性信号",
    }


def _update_candidate(conn, source_id: int, scored: dict) -> None:
    status = scored["official_check_status"]
    candidate_status = "pending"
    reject_reason = None
    enabled = 0

    if status == "rejected":
        candidate_status = "rejected"
        reject_reason = scored["message"]
    elif status == "reference_only":
        candidate_status = "reference_only"
    elif status == "unknown":
        candidate_status = "reference_only"

    conn.execute(
        """
        UPDATE raw_data_sources
        SET official_check_status = ?,
            official_score = ?,
            official_check_message = ?,
            reference_only = ?,
            candidate_reject_reason = ?,
            candidate_status = ?,
            enabled = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            status,
            int(scored.get("official_score") or 0),
            scored.get("message"),
            int(scored.get("reference_only") or 0),
            reject_reason,
            candidate_status,
            enabled,
            source_id,
        ),
    )


def apply_official_filter_to_candidates(limit: int = 500) -> dict:
    """对候选源执行官方性过滤，并写回状态。"""
    init_db()
    stats = {
        "total": 0,
        "official": 0,
        "likely_official": 0,
        "reference_only": 0,
        "rejected": 0,
        "unknown": 0,
    }
    conn = create_connection()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM raw_data_sources
            WHERE COALESCE(is_candidate, 0) = 1
              AND COALESCE(is_demo, 0) != 1
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        for row in rows:
            source = dict(row)
            scored = score_official_source(
                school_name=source.get("school_name") or "",
                url=source.get("url") or "",
                title=source.get("name") or "",
                snippet=source.get("description") or "",
            )
            _update_candidate(conn, source["id"], scored)
            status = scored["official_check_status"]
            stats["total"] += 1
            stats[status if status in stats else "unknown"] += 1
        conn.commit()
        return stats
    finally:
        conn.close()


def keep_top_official_candidates_per_school(max_per_school: int = 3) -> dict:
    """每所学校只保留 Top N 个 official/likely_official pending 候选。"""
    init_db()
    conn = create_connection()
    rejected_count = 0
    processed_schools = 0
    try:
        schools = [
            row["school_name"]
            for row in conn.execute(
                """
                SELECT DISTINCT school_name
                FROM raw_data_sources
                WHERE COALESCE(is_candidate, 0) = 1
                  AND candidate_status = 'pending'
                  AND official_check_status IN ('official', 'likely_official')
                  AND COALESCE(school_name, '') != ''
                """
            ).fetchall()
        ]
        for school_name in schools:
            rows = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, official_score, discovery_score
                    FROM raw_data_sources
                    WHERE school_name = ?
                      AND COALESCE(is_candidate, 0) = 1
                      AND candidate_status = 'pending'
                      AND official_check_status IN ('official', 'likely_official')
                    """,
                    (school_name,),
                ).fetchall()
            ]
            rows.sort(
                key=lambda item: int(item.get("official_score") or 0)
                + int(item.get("discovery_score") or 0),
                reverse=True,
            )
            for item in rows[max_per_school:]:
                conn.execute(
                    """
                    UPDATE raw_data_sources
                    SET candidate_status = 'rejected',
                        enabled = 0,
                        candidate_reject_reason = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (f"同校候选过多，仅保留Top {max_per_school}官方候选", item["id"]),
                )
                rejected_count += 1
            processed_schools += 1
        conn.commit()
        return {
            "processed_schools": processed_schools,
            "rejected_overflow_candidates": rejected_count,
            "max_per_school": max_per_school,
        }
    finally:
        conn.close()
