from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class RiskContext(BaseModel):
    page_type: str
    consecutive_fail: int = 0
    recent_operations: int = 0
    has_error_keywords: bool = False
    job_url: Optional[str] = None

class RiskScoreResponse(BaseModel):
    score: float
    level: str  # low/medium/high
    threshold: float
    action: str  # human_intervention_required / auto_continue
    factors: List[Dict[str, Any]] = []

class RiskStatusResponse(BaseModel):
    consecutive_success: int
    consecutive_fail: int
    current_threshold: float
    risk_history: List[Dict] = []

class QueueTaskCreate(BaseModel):
    task_id: int
    job_url: str
    job_title: Optional[str] = None
    company: Optional[str] = None
    priority: int = 0

class HumanAction(BaseModel):
    action: str  # confirm / skip / modify
    params: Optional[Dict[str, Any]] = None

class QueueStatusResponse(BaseModel):
    task_id: int
    total: int
    pending: int
    running: int
    completed: int
    failed: int
    skipped: int

class StealthConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    remove_webdriver: Optional[bool] = None
    randomize_ua: Optional[bool] = None
    randomize_canvas: Optional[bool] = None
    randomize_webgl: Optional[bool] = None
    human_scroll: Optional[bool] = None
    human_mouse: Optional[bool] = None
    random_delay_min: Optional[int] = None
    random_delay_max: Optional[int] = None
