from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None

class UserCreate(UserBase):
    auth0_id: str

class UserProfileResponse(BaseModel):
    id: int
    directions: Optional[List[str]] = None
    planning_daily_limit: Optional[int] = None
    design_daily_limit: Optional[int] = None
    total_daily_limit: Optional[int] = None
    include_keywords: Optional[List[str]] = None
    prefer_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    prefer_companies: Optional[List[str]] = None
    exclude_companies: Optional[List[str]] = None
    prefer_industries: Optional[List[str]] = None
    exclude_industries: Optional[List[str]] = None
    fuzzy_keywords: Optional[List[str]] = None
    scoring_threshold: Optional[float] = None
    target_cities: Optional[List[str]] = None
    exclude_areas: Optional[List[str]] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    platform_credentials: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    # 求职方向（支持多选）
    directions: Optional[List[str]] = None

    # 每个方向的投递上限
    planning_daily_limit: Optional[int] = None
    design_daily_limit: Optional[int] = None
    total_daily_limit: Optional[int] = None

    # 职位关键词
    include_keywords: Optional[List[str]] = None
    prefer_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None

    # 公司边界
    prefer_companies: Optional[List[str]] = None
    exclude_companies: Optional[List[str]] = None

    # 行业边界
    prefer_industries: Optional[List[str]] = None
    exclude_industries: Optional[List[str]] = None

    # 模糊岗位二次打分
    fuzzy_keywords: Optional[List[str]] = None
    scoring_threshold: Optional[float] = None

    # 基础配置
    target_cities: Optional[List[str]] = None
    exclude_areas: Optional[List[str]] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    platform_credentials: Optional[Dict[str, Any]] = None

class UserResponse(UserBase):
    id: int
    auth0_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    profile: Optional[UserProfileResponse] = None

    class Config:
        from_attributes = True
