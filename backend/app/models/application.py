from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    ALREADY_APPLIED = "already_applied"
    FAILED = "failed"
    REJECTED = "rejected"

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    platform = Column(String(50))

    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING)
    applied_at = Column(DateTime, nullable=True)
    failed_reason = Column(Text, nullable=True)

    # 投递详情
    apply_url = Column(String(500))
    apply_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    user = relationship("User", back_populates="applications")
    job = relationship("Job")
