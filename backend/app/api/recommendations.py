# backend/app/api/recommendations.py
# V3.1 阶段2: 增强匹配与推荐API
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.recommendation import RecommendationEngine

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("/recommend/{user_id}")
def get_recommendations(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    min_score: float = Query(default=0.3, ge=0, le=1),
    db: Session = Depends(get_db)
):
    """
    V3.1: 获取推荐职位列表
    - limit: 返回数量限制
    - min_score: 最低匹配分数过滤
    """
    engine = RecommendationEngine(user_id)
    try:
        recommendations = engine.recommend(limit=limit, min_score=min_score)
        return {
            'jobs': recommendations,
            'count': len(recommendations),
            'weights': engine.weights,  # V3.1: 返回当前使用的权重
        }
    finally:
        engine.close()

@router.get("/recommend/{user_id}/feed")
def get_recommendations_feed(
    user_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    V3.1: 为Job Feed获取推荐（分页支持）
    - 专为前端Job Feed设计
    - 支持分页
    """
    engine = RecommendationEngine(user_id)
    try:
        result = engine.recommend_for_feed(limit=limit, offset=offset)
        return result
    finally:
        engine.close()

@router.get("/recommend/{user_id}/explain/{job_id}")
def get_recommendation_explanation(
    user_id: int,
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    V3.1: 获取职位的详细推荐解释
    - 为什么推荐这个职位
    - 分数构成
    - 推荐提示
    """
    engine = RecommendationEngine(user_id)
    try:
        explanation = engine.get_recommendation_explanation(job_id)
        return explanation
    finally:
        engine.close()

@router.post("/action")
def record_action(job_id: int, user_id: int, action: str, db: Session = Depends(get_db)):
    """V3.1: 记录用户行为"""
    engine = RecommendationEngine(user_id)
    try:
        engine.record_behavior(job_id, action)
        return {"success": True}
    finally:
        engine.close()

@router.get("/recommend/{user_id}/weights")
def get_recommendation_weights(user_id: int, db: Session = Depends(get_db)):
    """V3.1: 获取当前推荐权重（基于用户行为学习）"""
    engine = RecommendationEngine(user_id)
    try:
        return {
            'weights': engine.weights,
            'base_weights': engine.BASE_WEIGHTS,
        }
    finally:
        engine.close()
