from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.job import Job
from app.schemas.job import JobResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("/", response_model=List[JobResponse])
def list_jobs(
    skip: int = 0,
    limit: int = 20,
    platform: Optional[str] = None,
    city: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Job).filter(Job.is_active == True)
    if platform:
        query = query.filter(Job.platform == platform)
    if city:
        query = query.filter(Job.city == city)
    return query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
