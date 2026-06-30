from db import create_connection
from schemas.recommend import RecommendRequest


def create_recommendation_log(
    request: RecommendRequest,
    result_json: str,
) -> int:
    """保存一次推荐查询并返回日志 ID。"""
    db = create_connection()
    try:
        cursor = db.execute(
            """
            INSERT INTO recommendation_logs
                (province, score, rank, subject_type, target_direction,
                 use_ai, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.province,
                request.score,
                request.rank,
                request.subject_type,
                request.target_direction,
                int(request.use_ai),
                result_json,
            ),
        )
        db.commit()
        return int(cursor.lastrowid)
    finally:
        db.close()

