from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    auth0_id = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    username = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    applications = relationship("Application", back_populates="user")
