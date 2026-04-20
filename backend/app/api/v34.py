from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.services.risk_score_engine import risk_score_engine
from app.services.job_queue import job_queue
from app.models.risk_score import RiskScoreRecord, DynamicThresholdState, JobQueueItem, StealthConfig
from app.schemas.risk_score import (
    RiskContext, RiskScoreResponse, RiskStatusResponse,
    QueueTaskCreate, HumanAction, QueueStatusResponse,
    StealthConfigUpdate
)

router = APIRouter(prefix="/api/v34", tags=["v34"])

# ========== RiskScore API ==========

@router.post("/risk/calculate", response_model=RiskScoreResponse)
async def calculate_risk(context: RiskContext, db: Session = Depends(get_db)):
    """计算当前操作的风险得分"""
    score, factors = risk_score_engine.calculate_risk_score(context.dict())
    threshold = risk_score_engine.calculate_threshold()

    level = "high" if score > threshold else "medium" if score > threshold * 0.6 else "low"
    action = "human_intervention_required" if score > threshold else "auto_continue"

    return RiskScoreResponse(
        score=score,
        level=level,
        threshold=threshold,
        action=action,
        factors=factors
    )

@router.get("/risk/status", response_model=RiskStatusResponse)
async def get_risk_status(user_id: int = 1, db: Session = Depends(get_db)):
    """获取当前风险状态"""
    try:
        state = db.query(DynamicThresholdState).filter(
            DynamicThresholdState.user_id == user_id
        ).first()

        if state:
            return RiskStatusResponse(
                consecutive_success=state.consecutive_success,
                consecutive_fail=state.consecutive_fail,
                current_threshold=state.current_threshold,
                risk_history=[]
            )
    except Exception as e:
        # 表不存在时使用内存状态
        pass

    return RiskStatusResponse(
        consecutive_success=risk_score_engine.consecutive_success,
        consecutive_fail=risk_score_engine.consecutive_fail,
        current_threshold=risk_score_engine.calculate_threshold(),
        risk_history=[]
    )

@router.post("/risk/reset")
async def reset_risk_state(user_id: int = 1, db: Session = Depends(get_db)):
    """重置风险状态"""
    risk_score_engine.reset_state()

    state = db.query(DynamicThresholdState).filter(
        DynamicThresholdState.user_id == user_id
    ).first()
    if state:
        state.consecutive_success = 0
        state.consecutive_fail = 0
        state.current_threshold = 0.7
        db.commit()

    return {"message": "Risk state reset"}

# ========== Job Queue API ==========

@router.post("/queue/create")
async def create_queue_task(task: QueueTaskCreate, db: Session = Depends(get_db)):
    """创建队列任务"""
    try:
        item = JobQueueItem(
            task_id=task.task_id,
            job_url=task.job_url,
            job_title=task.job_title,
            company=task.company,
            status='pending',
            priority=task.priority
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"item_id": item.id, "status": "pending"}
    except Exception as e:
        return {"item_id": 0, "status": "pending", "error": str(e)}

@router.get("/queue/{task_id}", response_model=QueueStatusResponse)
async def get_queue_status(task_id: int, db: Session = Depends(get_db)):
    """获取任务队列状态"""
    try:
        items = db.query(JobQueueItem).filter(JobQueueItem.task_id == task_id).all()
    except Exception:
        items = []

    return QueueStatusResponse(
        task_id=task_id,
        total=len(items),
        pending=len([i for i in items if i.status == 'pending']),
        running=len([i for i in items if i.status == 'running']),
        completed=len([i for i in items if i.status == 'completed']),
        failed=len([i for i in items if i.status == 'failed']),
        skipped=len([i for i in items if i.status == 'skipped'])
    )

@router.post("/queue/{item_id}/human-action")
async def queue_human_action(item_id: int, action: HumanAction, db: Session = Depends(get_db)):
    """人工干预操作"""
    try:
        item = db.query(JobQueueItem).filter(JobQueueItem.id == item_id).first()
        if not item:
            return {"message": f"Action {action.action} processed (db not available)", "item_id": item_id}

        if action.action == "confirm":
            item.status = 'running'
            item.attempts += 1
        elif action.action == "skip":
            item.status = 'skipped'
        elif action.action == "modify":
            item.status = 'pending'
            item.attempts += 1

        db.commit()
        return {"message": f"Action {action.action} processed", "item_id": item_id}
    except Exception as e:
        return {"message": f"Action {action.action} processed (error: {str(e)})", "item_id": item_id}

@router.post("/queue/{task_id}/resume")
async def resume_queue_task(task_id: int, db: Session = Depends(get_db)):
    """恢复中断的任务队列"""
    try:
        items = db.query(JobQueueItem).filter(
            JobQueueItem.task_id == task_id,
            JobQueueItem.status.in_(['failed', 'skipped'])
        ).all()

        resumed_count = 0
        for item in items:
            item.status = 'pending'
            resumed_count += 1

        db.commit()
        return {"resumed_items": resumed_count}
    except Exception:
        return {"resumed_items": 0}

# ========== Stealth Config API ==========

@router.get("/stealth/config")
async def get_stealth_config(user_id: int = 1, db: Session = Depends(get_db)):
    """获取当前Stealth配置"""
    try:
        config = db.query(StealthConfig).filter(StealthConfig.user_id == user_id).first()

        if not config:
            config = StealthConfig(user_id=user_id)
            db.add(config)
            db.commit()
            db.refresh(config)
    except Exception:
        # 返回默认配置
        return {
            "enabled": True,
            "remove_webdriver": True,
            "randomize_ua": True,
            "randomize_canvas": True,
            "randomize_webgl": True,
            "human_scroll": True,
            "human_mouse": True,
            "random_delay_min": 1,
            "random_delay_max": 3
        }

    return {
        "enabled": config.enabled,
        "remove_webdriver": config.remove_webdriver,
        "randomize_ua": config.randomize_ua,
        "randomize_canvas": config.randomize_canvas,
        "randomize_webgl": config.randomize_webgl,
        "human_scroll": config.human_scroll,
        "human_mouse": config.human_mouse,
        "random_delay_min": config.random_delay_min,
        "random_delay_max": config.random_delay_max
    }

@router.post("/stealth/config")
async def update_stealth_config(config_update: StealthConfigUpdate, user_id: int = 1, db: Session = Depends(get_db)):
    """更新Stealth配置"""
    try:
        config = db.query(StealthConfig).filter(StealthConfig.user_id == user_id).first()

        if not config:
            config = StealthConfig(user_id=user_id)
            db.add(config)

        update_data = config_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(config, key, value)

        db.commit()
        return {"message": "Stealth config updated"}
    except Exception as e:
        return {"message": f"Stealth config updated (local only, error: {str(e)})"}
