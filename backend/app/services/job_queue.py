"""
V3.4 Job Queue Engine
Job队列管理 - 支持任务中断恢复、人工干预
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.risk_score import JobQueueItem
from app.schemas.risk_score import HumanAction

class JobQueue:
    """
    Job队列管理器
    """

    def __init__(self):
        pass

    def create_item(self, db: Session, task_id: int, job_url: str,
                    job_title: str = None, company: str = None,
                    priority: int = 0, job_id: int = None) -> JobQueueItem:
        """
        创建队列项
        """
        item = JobQueueItem(
            task_id=task_id,
            job_id=job_id,
            job_url=job_url,
            job_title=job_title,
            company=company,
            status='pending',
            priority=priority,
            attempts=0
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def get_task_items(self, db: Session, task_id: int) -> List[JobQueueItem]:
        """
        获取任务的所有队列项
        """
        return db.query(JobQueueItem).filter(
            JobQueueItem.task_id == task_id
        ).order_by(JobQueueItem.priority.desc(), JobQueueItem.created_at).all()

    def get_next_pending(self, db: Session, task_id: int) -> Optional[JobQueueItem]:
        """
        获取下一个待处理的队列项
        """
        return db.query(JobQueueItem).filter(
            and_(
                JobQueueItem.task_id == task_id,
                JobQueueItem.status == 'pending'
            )
        ).order_by(JobQueueItem.priority.desc(), JobQueueItem.created_at).first()

    def mark_running(self, db: Session, item_id: int) -> JobQueueItem:
        """
        标记为运行中
        """
        item = db.query(JobQueueItem).filter(JobQueueItem.id == item_id).first()
        if item:
            item.status = 'running'
            item.started_at = datetime.utcnow()
            db.commit()
        return item

    def mark_completed(self, db: Session, item_id: int, risk_score: float = None,
                       risk_level: str = None, result: str = None) -> JobQueueItem:
        """
        标记为已完成
        """
        item = db.query(JobQueueItem).filter(JobQueueItem.id == item_id).first()
        if item:
            item.status = 'completed'
            item.completed_at = datetime.utcnow()
            item.risk_score = risk_score
            item.risk_level = risk_level
            item.result = result
            db.commit()
        return item

    def mark_failed(self, db: Session, item_id: int, error_message: str = None,
                     stack_trace: str = None, risk_score: float = None) -> JobQueueItem:
        """
        标记为失败
        """
        item = db.query(JobQueueItem).filter(JobQueueItem.id == item_id).first()
        if item:
            item.status = 'failed'
            item.completed_at = datetime.utcnow()
            item.error_message = error_message
            item.stack_trace = stack_trace
            item.risk_score = risk_score
            item.attempts += 1
            db.commit()
        return item

    def mark_skipped(self, db: Session, item_id: int, reason: str = None) -> JobQueueItem:
        """
        标记为跳过
        """
        item = db.query(JobQueueItem).filter(JobQueueItem.id == item_id).first()
        if item:
            item.status = 'skipped'
            item.completed_at = datetime.utcnow()
            item.error_message = reason
            db.commit()
        return item

    def mark_relocated(self, db: Session, item_id: int, new_job_url: str,
                       similarity_score: float = None) -> JobQueueItem:
        """
        标记为已重定位
        """
        item = db.query(JobQueueItem).filter(JobQueueItem.id == item_id).first()
        if item:
            item.relocator_source = item.job_url  # 保存原始URL
            item.job_url = new_job_url
            item.status = 'relocated'
            item.similarity_score = similarity_score
            item.attempts += 1
            db.commit()
        return item

    def process_human_action(self, db: Session, item_id: int, action: HumanAction) -> Dict[str, Any]:
        """
        处理人工干预操作
        """
        item = db.query(JobQueueItem).filter(JobQueueItem.id == item_id).first()
        if not item:
            return {"success": False, "error": "Item not found"}

        if action.action == "confirm":
            # 确认执行
            item.status = 'pending'  # 重新放回队列
            item.attempts += 1
            db.commit()
            return {"success": True, "message": "Item requeued for execution"}

        elif action.action == "skip":
            # 跳过
            item.status = 'skipped'
            item.completed_at = datetime.utcnow()
            item.error_message = "Skipped by user"
            db.commit()
            return {"success": True, "message": "Item skipped"}

        elif action.action == "modify":
            # 修改参数重试
            item.status = 'pending'
            item.attempts += 1
            # 参数保存在error_message中
            item.error_message = f"User modified params: {action.params}"
            db.commit()
            return {"success": True, "message": "Item requeued with modified params"}

        return {"success": False, "error": "Unknown action"}

    def resume_task(self, db: Session, task_id: int) -> int:
        """
        恢复任务 - 将所有failed/skipped项重新设为pending
        """
        items = db.query(JobQueueItem).filter(
            and_(
                JobQueueItem.task_id == task_id,
                JobQueueItem.status.in_(['failed', 'skipped'])
            )
        ).all()

        count = 0
        for item in items:
            item.status = 'pending'
            count += 1

        db.commit()
        return count

    def get_queue_status(self, db: Session, task_id: int) -> Dict[str, Any]:
        """
        获取队列状态
        """
        items = db.query(JobQueueItem).filter(
            JobQueueItem.task_id == task_id
        ).all()

        status = {
            "total": len(items),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0,
            "relocated": 0
        }

        for item in items:
            if item.status in status:
                status[item.status] += 1

        return status


# 全局单例
job_queue = JobQueue()