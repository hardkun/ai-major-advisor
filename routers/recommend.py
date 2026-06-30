from fastapi import APIRouter

from schemas.recommend import RecommendRequest, RecommendResponse
from services.recommend_service import recommend_majors


router = APIRouter(tags=["recommend"])


@router.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    return recommend_majors(request, use_ai=request.use_ai)
