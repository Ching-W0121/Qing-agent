"""
职位匹配与投递 API
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.application import Application, ApplicationStatus
from app.services.job_filter import JobFilterService, match_jobs_for_user
from app.schemas.job import JobResponse

router = APIRouter(prefix="/api/matching", tags=["matching"])


@router.post("/match/{user_id}")
def match_jobs(
    user_id: int,
    raw_jobs: List[dict],
    db: Session = Depends(get_db)
):
    """
    根据用户画像过滤职位，返回匹配结果

    raw_jobs 格式:
    [
        {
            "platform": "zhilian",
            "platform_job_id": "123456",
            "title": "品牌策划",
            "company": "某公司",
            "city": "深圳",
            "area": "南山区",
            "salary_min": 8000,
            "salary_max": 15000,
            "description": "职位描述...",
            "requirements": "职位要求...",
            "source_url": "https://..."
        },
        ...
    ]
    """
    # 验证用户存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 执行匹配
    matched = match_jobs_for_user(db, user_id, raw_jobs)

    return {
        "total_raw": len(raw_jobs),
        "total_matched": len(matched),
        "jobs": matched[:50],  # 最多返回50个
    }


@router.get("/matched/{user_id}")
def get_matched_jobs(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取用户已匹配的职位列表"""
    # 获取用户的画像配置
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    filter_service = JobFilterService(db, user_id)

    # 获取所有活跃职位
    jobs = db.query(Job).filter(Job.is_active == True).offset(skip).limit(limit).all()

    # 过滤
    matched = filter_service.filter_jobs(jobs)

    return {
        "total": len(matched),
        "jobs": [
            {
                "job_id": item['job'].id,
                "platform": item['job'].platform,
                "title": item['job'].title,
                "company": item['job'].company,
                "city": item['job'].city,
                "area": item['job'].area,
                "salary": f"{item['job'].salary_min/1000:.0f}K-{item['job'].salary_max/1000:.0f}K" if item['job'].salary_min else '面议',
                "score": item['score'],
                "reason": item['reason'],
            }
            for item in matched
        ]
    }


@router.post("/apply")
def apply_job(
    user_id: int,
    job_id: int,
    db: Session = Depends(get_db)
):
    """投递职位"""
    # 检查用户
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查职位
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="职位不存在")

    # 检查是否已投递
    existing = db.query(Application).filter(
        Application.user_id == user_id,
        Application.job_id == job_id
    ).first()

    if existing:
        return {
            "success": False,
            "message": "已经投递过该职位",
            "status": existing.status.value,
            "applied_at": existing.applied_at,
        }

    # 创建投递记录
    application = Application(
        user_id=user_id,
        job_id=job_id,
        platform=job.platform,
        status=ApplicationStatus.PENDING,
        apply_url=job.source_url,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    return {
        "success": True,
        "message": "投递成功",
        "application_id": application.id,
        "status": application.status.value,
        "platform": job.platform,
        "job_title": job.title,
        "company": job.company,
    }


@router.get("/applications/{user_id}")
def get_applications(
    user_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取用户的投递记录"""
    query = db.query(Application).filter(Application.user_id == user_id)

    if status:
        query = query.filter(Application.status == status)

    applications = query.order_by(Application.created_at.desc()).all()

    return {
        "total": len(applications),
        "applications": [
            {
                "id": app.id,
                "job_id": app.job_id,
                "platform": app.platform,
                "job_title": app.job.title if app.job else "未知",
                "company": app.job.company if app.job else "未知",
                "city": app.job.city if app.job else "未知",
                "status": app.status.value,
                "applied_at": app.applied_at,
                "failed_reason": app.failed_reason,
                "created_at": app.created_at,
            }
            for app in applications
        ]
    }


@router.put("/application/{application_id}")
def update_application(
    application_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    """更新投递状态"""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="投递记录不存在")

    try:
        application.status = ApplicationStatus(status)
        if status in ['submitted', 'already_applied']:
            application.applied_at = datetime.utcnow()
        db.commit()

        return {
            "success": True,
            "message": f"状态已更新为 {status}",
            "application_id": application_id,
            "new_status": status,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的状态值: {status}")
