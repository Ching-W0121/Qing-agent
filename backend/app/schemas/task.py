from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class TaskBase(BaseModel):
    pass

class TaskCreate(TaskBase):
    user_id: int
    task_type: str  # "search", "apply", "verify"

class TaskResponse(TaskBase):
    id: int
    user_id: int
    task_type: str
    status: str
    jobs_found: int
    jobs_filtered: int
    applications_submitted: int
    applications_failed: int
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
