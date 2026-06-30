"""根据覆盖缺口和采集诊断生成下一步处理队列。"""

from db import create_connection, init_db
from services.source_backfill_service import load_seed_school_names


DIAGNOSIS_ACTIONS = {
    "preview_success": ("run_collect_source", 1, "预览成功，可以直接采集"),
    "field_mapping_or_header_error": ("adjust_parser_config", 2, "表头或字段映射错误，需要查看 preview sample_rows"),
    "no_ai_match_or_filter_too_strict": ("review_major_keywords", 3, "有表格但没有命中 AI 相关专业，可能关键词过严或该校无相关专业"),
    "unsupported": ("implement_parser", 4, "当前 parser_type 暂不支持预览或采集"),
    "preview_failed": ("manual_review_source", 5, "预览失败，需要人工检查数据源可访问性或解析配置"),
}


def generate_source_action_queue() -> dict:
    init_db()
    seed_school_names = load_seed_school_names()
    actions = []

    conn = create_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, school_name, name, parser_type, collect_diagnosis_status,
                   collect_diagnosis_message
            FROM raw_data_sources
            WHERE COALESCE(is_demo, 0) != 1
              AND COALESCE(is_candidate, 0) != 1
              AND COALESCE(collect_diagnosis_status, '') != ''
            """
        ).fetchall()
        for row in rows:
            item = dict(row)
            mapping = DIAGNOSIS_ACTIONS.get(item.get("collect_diagnosis_status"))
            if not mapping:
                continue
            action, priority, reason = mapping
            actions.append(
                {
                    "priority": priority,
                    "school_name": item.get("school_name"),
                    "source_name": item.get("name"),
                    "source_id": item.get("id"),
                    "parser_type": item.get("parser_type"),
                    "diagnosis_status": item.get("collect_diagnosis_status"),
                    "action": action,
                    "reason": reason,
                    "message": item.get("collect_diagnosis_message"),
                }
            )

        for school_name in seed_school_names:
            has_source = conn.execute(
                """
                SELECT 1
                FROM raw_data_sources
                WHERE school_name = ?
                  AND COALESCE(is_demo, 0) != 1
                  AND COALESCE(is_candidate, 0) != 1
                LIMIT 1
                """,
                (school_name,),
            ).fetchone()
            if not has_source:
                actions.append(
                    {
                        "priority": 6,
                        "school_name": school_name,
                        "source_name": None,
                        "source_id": None,
                        "parser_type": None,
                        "diagnosis_status": "missing_source",
                        "action": "improve_search_or_fill_site",
                        "reason": "该 seed 学校尚无正式数据源，需要继续搜索或补充招生官网入口",
                        "message": None,
                    }
                )
    finally:
        conn.close()

    actions.sort(key=lambda item: (item["priority"], item.get("school_name") or ""))
    distribution = {}
    for item in actions:
        distribution[item["action"]] = distribution.get(item["action"], 0) + 1

    return {
        "total_actions": len(actions),
        "action_distribution": distribution,
        "actions": actions,
    }
