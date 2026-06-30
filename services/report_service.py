from schemas.recommend import RecommendItem, RecommendRequest


def build_free_report(
    items: list[RecommendItem],
    disclaimer: str,
) -> dict:
    """构建只包含核心推荐信息的免费版报告。"""
    report_items = [
        {
            "school_name": item.school_name,
            "major_name": item.major_name,
            "city": item.city,
            "school_level": item.school_level,
            "match_type": item.match_type,
            "min_score": item.min_score,
            "min_rank": item.min_rank,
            "reason": item.reason,
        }
        for item in items
    ]

    return {
        "title": "AI相关专业择校参考报告",
        "summary": "以下结果基于公开历史数据、专业方向标签和规则算法生成，仅供参考。",
        "items": report_items,
        "disclaimer": disclaimer,
    }


def build_paid_report(
    items: list[RecommendItem],
    request: RecommendRequest,
    disclaimer: str,
) -> dict:
    """构建包含完整专业信息和 AI 解释的付费版报告。"""
    report_items = [
        {
            "school_name": item.school_name,
            "major_name": item.major_name,
            "city": item.city,
            "school_level": item.school_level,
            "match_type": item.match_type,
            "min_score": item.min_score,
            "min_rank": item.min_rank,
            "direction_tags": item.direction_tags,
            "career_paths": item.career_paths,
            "reason": item.reason,
            "ai_explanation": (
                item.ai_explanation.model_dump(mode="json")
                if item.ai_explanation
                else None
            ),
        }
        for item in items
    ]

    return {
        "title": "AI相关专业完整分析报告",
        "user_input": {
            "province": request.province,
            "score": request.score,
            "rank": request.rank,
            "subject_type": request.subject_type,
            "target_direction": request.target_direction,
        },
        "items": report_items,
        "extra_suggestions": [
            "建议结合本省官方志愿填报系统核对招生计划、选科要求、学费和校区。",
            "建议同时准备冲、稳、保不同层次的院校专业组合。",
            "AI 相关专业差异较大，应结合数学、编程、工程实践兴趣综合判断。",
        ],
        "disclaimer": disclaimer,
    }

