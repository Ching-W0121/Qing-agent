# backend/app/services/job_pool.py
from app.core.database import SessionLocal
from app.models.job import Job
from datetime import datetime, timedelta

class JobPool:
    """Job Pool 管理：只保留最近3天的职位"""

    @staticmethod
    def get_recent_jobs(days: int = 3):
        """获取最近N天的职位"""
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            jobs = db.query(Job).filter(
                Job.publish_time >= cutoff
            ).order_by(Job.publish_time.desc()).all()
            return jobs
        finally:
            db.close()

    @staticmethod
    def clean_old_jobs(days: int = 7):
        """清理超过N天的职位"""
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            db.query(Job).filter(
                Job.publish_time < cutoff
            ).delete()
            db.commit()
        finally:
            db.close()
