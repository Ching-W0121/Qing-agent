from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, UniqueConstraint
from datetime import datetime
from app.core.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), index=True)
    platform_job_id = Column(String(255), index=True)
    title = Column(String(255))
    company = Column(String(255))
    city = Column(String(100))
    area = Column(String(100))
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    experience = Column(String(100))
    education = Column(String(50))
    job_type = Column(String(50))
    description = Column(Text)
    requirements = Column(Text)
    skills = Column(JSON, default=list)
    industry = Column(String(100))
    source_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    publish_time = Column(DateTime, default=datetime.utcnow)  # 发布时间
    tags = Column(JSON, default=list)  # 职位标签
    source = Column(String(50), default="zhilian")  # 来源平台
    is_exposed = Column(Boolean, default=False)  # 是否已推送给用户
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 复合唯一索引（平台+平台ID）
    __table_args__ = (
        UniqueConstraint('platform', 'platform_job_id', name='uq_platform_job_id'),
    )
