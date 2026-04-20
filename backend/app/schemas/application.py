from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ApplicationBase(BaseModel):
    pass

class ApplicationCreate(ApplicationBase):
    user_id: int
    job_id: int
    platform: str
    apply_url: Optional[str] = None

class ApplicationResponse(ApplicationBase):
    id: int
    user_id: int
    job_id: int
    platform: str
    status: str
    applied_at: Optional[datetime] = None
    failed_reason: Optional[str] = None
    apply_url: Optional[str] = None
    apply_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
