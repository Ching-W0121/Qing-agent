from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Enum
from datetime import datetime
import enum
from app.core.database import Base

class TaskType(str, enum.Enum):
    SEARCH = "search"
    APPLY = "apply"
    VERIFY = "verify"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    task_type = Column(Enum(TaskType))
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    result_data = Column(JSON, nullable=True)  # 任务结果数据

    # 统计
    jobs_found = Column(Integer, default=0)
    jobs_filtered = Column(Integer, default=0)
    applications_submitted = Column(Integer, default=0)
    applications_failed = Column(Integer, default=0)

    # 详情
    details = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
