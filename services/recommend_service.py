import json

from crud.recommendation_logs import create_recommendation_log
from crud.reports import create_report
from db import create_connection
from schemas.recommend import RecommendItem, RecommendRequest, RecommendResponse
from services.ai_explain_service import generate_ai_explanation
from services.report_service import build_free_report, build_paid_report
from utils.subject_type import get_subject_type_aliases


DISCLAIMER = "本结果仅基于公开历史数据和规则算法生成，不构成最终志愿填报建议。"
EMPTY_DISCLAIMER = f"暂未匹配到合适结果。{DISCLAIMER}"

MATCH_ORDER = {"稳": 0, "保": 1, "冲": 2}

MATCH_REASONS = {
    "稳": "你的位次接近该专业往年最低录取位次，属于相对稳妥的参考选择。",
    "保": "你的位次明显优于该专业往年最低录取位次，属于保底参考选择。",
    "冲": "你的位次略低于该专业往年最低录取位次，可以作为冲刺参考选择。",
}


def _get_match_type(user_rank: int, min_rank: int) -> str | None:
    """根据用户位次与往年最低录取位次判断保、稳、冲。"""
    if user_rank <= min_rank * 0.80:
        return "保"
    if user_rank <= min_rank:
        return "稳"
    if user_rank <= min_rank * 1.10:
        return "冲"
    return None


def recommend_majors(
    request: RecommendRequest,
    use_ai: bool = False,
) -> RecommendResponse:
    """查询历史录取数据，并按规则返回最多 5 条推荐。"""
    subject_type_aliases = get_subject_type_aliases(request.subject_type)
    subject_type_placeholders = ", ".join(["?"] * len(subject_type_aliases))

    db = create_connection()
    try:
        rows = db.execute(
            f"""
            SELECT
                schools.name AS school_name,
                schools.city AS city,
                schools.level AS school_level,
                majors.name AS major_name,
                majors.direction_tags AS direction_tags,
                majors.career_paths AS career_paths,
                admissions.year AS year,
                admissions.min_score AS min_score,
                admissions.min_rank AS min_rank,
                admissions.school_code AS school_code,
                admissions.major_group_code AS major_group_code,
                admissions.major_code AS major_code,
                admissions.elective_requirement AS elective_requirement,
                admissions.campus AS campus,
                admissions.is_verified AS is_verified,
                data_sources.name AS source_name
            FROM admissions
            JOIN schools ON schools.id = admissions.school_id
            JOIN majors ON majors.id = admissions.major_id
            LEFT JOIN data_sources ON data_sources.id = admissions.source_id
            WHERE admissions.province = ?
              AND admissions.subject_type IN ({subject_type_placeholders})
              AND admissions.min_rank IS NOT NULL
              AND instr(COALESCE(majors.direction_tags, ''), ?) > 0
            """,
            (
                request.province,
                *subject_type_aliases,
                request.target_direction,
            ),
        ).fetchall()
    finally:
        db.close()

    candidates: list[tuple[RecommendItem, int]] = []

    for row in rows:
        min_rank = row["min_rank"]
        match_type = _get_match_type(request.rank, min_rank)
        if match_type is None:
            continue

        reason = (
            MATCH_REASONS[match_type]
            + f"该专业方向标签与用户选择的 {request.target_direction} 相关。"
        )
        item = RecommendItem(
            school_name=row["school_name"],
            major_name=row["major_name"],
            city=row["city"],
            school_level=row["school_level"],
            match_type=match_type,
            min_score=row["min_score"],
            min_rank=min_rank,
            direction_tags=row["direction_tags"],
            career_paths=row["career_paths"],
            reason=reason,
            year=row["year"],
            school_code=row["school_code"],
            major_group_code=row["major_group_code"],
            major_code=row["major_code"],
            elective_requirement=row["elective_requirement"],
            campus=row["campus"],
            source_name=row["source_name"],
            is_verified=bool(row["is_verified"]),
        )
        candidates.append((item, abs(min_rank - request.rank)))

    candidates.sort(key=lambda candidate: (MATCH_ORDER[candidate[0].match_type], candidate[1]))
    items = [candidate[0] for candidate in candidates[:5]]

    if request.use_ai or use_ai:
        for item in items:
            try:
                item.ai_explanation = generate_ai_explanation(item, request)
            except Exception as exc:
                # AI 解释属于可选增强，不能影响规则推荐结果。
                print("AI 解释生成失败：", exc)
                item.ai_explanation = None

    disclaimer = DISCLAIMER if items else EMPTY_DISCLAIMER
    log_id = None
    report_id = None

    try:
        result_json = json.dumps(
            [item.model_dump(mode="json") for item in items],
            ensure_ascii=False,
        )
        log_id = create_recommendation_log(request, result_json)

        free_report = build_free_report(items, disclaimer)
        paid_report = build_paid_report(items, request, disclaimer)
        report_id = create_report(
            log_id=log_id,
            free_result_json=json.dumps(free_report, ensure_ascii=False),
            paid_result_json=json.dumps(paid_report, ensure_ascii=False),
        )
    except Exception as exc:
        # 保存失败不能影响推荐结果正常返回。
        print("推荐记录或报告保存失败：", exc)

    return RecommendResponse(
        items=items,
        disclaimer=disclaimer,
        log_id=log_id,
        report_id=report_id,
    )
