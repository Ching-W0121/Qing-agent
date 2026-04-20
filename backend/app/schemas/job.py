from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class JobBase(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    job_type: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    skills: Optional[List[str]] = None
    industry: Optional[str] = None
    source_url: Optional[str] = None

class JobCreate(JobBase):
    platform: str
    platform_job_id: str

class JobResponse(JobBase):
    id: int
    platform: str
    platform_job_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
