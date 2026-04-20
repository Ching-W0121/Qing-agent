from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from app.core.database import Base
import datetime


class UserBehavior(Base):
    __tablename__ = "user_behaviors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    action = Column(String(20))  # view, click, like, dislike, apply, favorite
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
