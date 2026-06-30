import json

from pydantic import ValidationError

from schemas.ai_explain import AIExplanation
from schemas.recommend import RecommendItem, RecommendRequest
from services.chat_service import generate_answer


RISK_NOTICE = "本结果仅基于公开历史数据和专业方向生成，不构成最终志愿填报建议。"


def _default_explanation(
    item: RecommendItem,
    request: RecommendRequest,
) -> AIExplanation:
    """AI 不可用或输出异常时使用的默认解释。"""
    return AIExplanation(
        recommend_reason=item.reason,
        study_focus=(
            f"建议重点了解{item.direction_tags or request.target_direction}相关课程、"
            "培养方案和实践项目。"
        ),
        suitable_for=(
            "适合对数学、编程和人工智能应用感兴趣，并愿意持续学习和实践的学生。"
        ),
        career_suggestions=(
            item.career_paths
            or "可关注算法、软件开发、数据分析及人工智能应用等相关岗位。"
        ),
        risk_notice=RISK_NOTICE,
    )


def _parse_json_answer(answer: str) -> dict:
    """兼容纯 JSON、Markdown JSON 代码块和带少量说明文字的响应。"""
    text = answer.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("AI 返回内容中没有 JSON 对象")

    return json.loads(text[start : end + 1])


def generate_ai_explanation(
    item: RecommendItem,
    request: RecommendRequest,
) -> AIExplanation:
    """为规则推荐结果生成解释；任何异常都会降级为默认解释。"""
    prompt = f"""
请根据以下高考志愿参考信息生成自然、克制且易懂的中文解释。
推荐院校和专业已经由规则算法确定，请勿改变推荐结果或匹配类型。

用户信息：
- 省份：{request.province}
- 分数：{request.score}
- 位次：{request.rank}
- 科类：{request.subject_type}
- 目标 AI 方向：{request.target_direction}

推荐信息：
- 学校名称：{item.school_name}
- 专业名称：{item.major_name}
- 匹配类型：{item.match_type}
- 往年最低分：{item.min_score}
- 往年最低位次：{item.min_rank}
- 专业方向标签：{item.direction_tags}
- 就业方向：{item.career_paths}

请只返回一个 JSON 对象，不要返回 Markdown。JSON 必须包含以下字符串字段：
- recommend_reason：推荐理由
- study_focus：专业学习重点
- suitable_for：适合人群
- career_suggestions：就业方向建议
- risk_notice：风险提示

risk_notice 必须包含原句：{RISK_NOTICE}
""".strip()

    messages = [
        {
            "role": "system",
            "content": (
                "你是谨慎的高考志愿信息解释助手。你只解释已有规则推荐，"
                "不决定院校排序，不承诺录取结果。"
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        answer = generate_answer(messages)
        data = _parse_json_answer(answer)
        explanation = AIExplanation.model_validate(data)

        if RISK_NOTICE not in explanation.risk_notice:
            explanation.risk_notice = f"{explanation.risk_notice} {RISK_NOTICE}".strip()

        return explanation
    except (ValueError, RuntimeError, ValidationError, json.JSONDecodeError, TypeError):
        return _default_explanation(item, request)

