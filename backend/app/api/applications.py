from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.core.database import get_db
from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from app.schemas.application import ApplicationResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/applications", tags=["applications"])

# 扩展响应包含job信息
class ApplicationWithJobResponse(BaseModel):
    id: int
    user_id: int
    job_id: int
    platform: str
    status: str
    applied_at: Optional[str] = None
    failed_reason: Optional[str] = None
    apply_url: Optional[str] = None
    apply_note: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    # Job信息
    company: Optional[str] = None
    job_title: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    salary: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None

    class Config:
        from_attributes = True

@router.get("/user/{user_id}", response_model=List[ApplicationWithJobResponse])
def list_user_applications(
    user_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Application).filter(Application.user_id == user_id)
    if status:
        query = query.filter(Application.status == status)

    applications = query.order_by(Application.created_at.desc()).all()

    # 转换为包含job信息的响应
    result = []
    for app in applications:
        job = db.query(Job).filter(Job.id == app.job_id).first() if app.job_id else None
        salary_str = None
        if job and job.salary_min and job.salary_max:
            if job.salary_min >= 10000:
                salary_str = f"{job.salary_min//10000}-{job.salary_max//10000}万"
            else:
                salary_str = f"{job.salary_min//1000}-{job.salary_max//1000}K"
        result.append({
            "id": app.id,
            "user_id": app.user_id,
            "job_id": app.job_id,
            "platform": app.platform,
            "status": app.status.value if hasattr(app.status, 'value') else app.status,
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "failed_reason": app.failed_reason,
            "apply_url": app.apply_url,
            "apply_note": app.apply_note,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            "company": job.company if job else None,
            "job_title": job.title if job else None,
            "city": job.city if job else None,
            "area": job.area if job else None,
            "salary": salary_str,
            "salary_min": job.salary_min if job else None,
            "salary_max": job.salary_max if job else None,
        })
    return result

@router.get("/user/{user_id}/stats")
def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    apps = db.query(Application).filter(Application.user_id == user_id).all()
    return {
        "total": len(apps),
        "submitted": len([a for a in apps if a.status == ApplicationStatus.SUBMITTED]),
        "pending": len([a for a in apps if a.status == ApplicationStatus.PENDING]),
        "failed": len([a for a in apps if a.status == ApplicationStatus.FAILED]),
    }

class ApplicationCreate(BaseModel):
    user_id: int
    job_id: int
    platform: str = "zhilian"
    status: str = "submitted"  # submitted, failed
    apply_url: Optional[str] = None
    apply_note: Optional[str] = None
    failed_reason: Optional[str] = None

@router.post("/", response_model=ApplicationWithJobResponse)
def create_application(app: ApplicationCreate, db: Session = Depends(get_db)):
    """创建投递记录"""
    # 检查是否已存在
    existing = db.query(Application).filter(
        Application.user_id == app.user_id,
        Application.job_id == app.job_id,
        Application.platform == app.platform
    ).first()

    if existing:
        # 更新已有记录
        existing.status = ApplicationStatus(app.status)
        existing.apply_url = app.apply_url
        existing.apply_note = app.apply_note
        existing.failed_reason = app.failed_reason
        db.commit()
        db.refresh(existing)
        return existing

    # 创建新记录
    new_app = Application(
        user_id=app.user_id,
        job_id=app.job_id,
        platform=app.platform,
        status=ApplicationStatus(app.status),
        apply_url=app.apply_url,
        apply_note=app.apply_note,
        failed_reason=app.failed_reason
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)
    return new_app
