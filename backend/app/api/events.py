from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter(prefix="/api/events", tags=["events"])

# 存储活跃的任务状态订阅
active_subscriptions = {}


@router.get("/task-status/{task_id}")
async def task_status_stream(task_id: int, request: Request):
    """SSE endpoint for real-time task status updates (polling-based)"""
    async def event_generator():
        last_status = None
        while True:
            # 检查客户端是否断开连接
            if await request.is_disconnected():
                break

            # 从数据库获取最新任务状态
            from app.core.database import SessionLocal
            from app.models.task_run import TaskRun, TaskStatus

            db = SessionLocal()
            try:
                task = db.query(TaskRun).filter(TaskRun.id == task_id).first()
                if task:
                    status_data = {
                        'id': task.id,
                        'status': task.status.value if hasattr(task.status, 'value') else task.status,
                        'jobs_found': task.jobs_found,
                        'jobs_filtered': task.jobs_filtered,
                        'applications_submitted': task.applications_submitted,
                        'applications_failed': getattr(task, 'applications_failed', 0),
                    }

                    # 只有状态变化时才发送
                    if status_data['status'] != last_status:
                        last_status = status_data['status']
                        yield f"data: {json.dumps(status_data)}\n\n"

                    # 如果任务完成或失败，发送最终状态后关闭
                    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        yield f"data: {json.dumps({**status_data, 'done': True})}\n\n"
                        break
            finally:
                db.close()

            await asyncio.sleep(1)  # 每秒检查一次

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/task-steps/{task_id}")
async def task_steps_stream(task_id: int, request: Request):
    """
    SSE endpoint for real-time V3.3 task step updates

    This endpoint pushes detailed step-by-step execution information:
    - login: 登录状态
    - search: 职位搜索
    - filter: 职位过滤
    - vision: Vision 模型分析
    - embedding: Embedding 相似度计算
    - decision: 决策引擎选择
    - click: 点击执行
    - verify: 投递验证

    Each event contains:
    {
        "task_id": 123,
        "step": "vision",
        "status": "success",
        "message": "Vision检测到6个按钮",
        "data": {"buttons": 6, "apply_button": "立即投递"},
        "timestamp": 1234567890.123
    }
    """
    from app.services.task_event_manager import task_event_manager

    queue = await task_event_manager.subscribe(task_id)

    async def event_generator():
        try:
            while True:
                # 检查客户端是否断开连接
                if await request.is_disconnected():
                    break

                try:
                    # 等待事件，最多等待5秒
                    event = await asyncio.wait_for(queue.get(), timeout=5.0)
                    yield f"data: {json.dumps(event, default=str)}\n\n"

                    # 如果收到 complete 事件，发送 done 并关闭连接
                    if event.get('step') == 'complete':
                        yield f"data: {json.dumps({'type': 'done', 'task_id': task_id})}\n\n"
                        break
                except asyncio.TimeoutError:
                    # 发送心跳
                    yield f"data: {json.dumps({'type': 'heartbeat', 'task_id': task_id})}\n\n"

        finally:
            await task_event_manager.unsubscribe(task_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/task-steps-history/{task_id}")
async def get_task_steps_history(task_id: int):
    """
    获取任务的历史步骤（用于前端获取错过的步骤）

    Returns:
        List[Dict]: 步骤列表
    """
    from app.services.task_event_manager import task_event_manager
    steps = task_event_manager.get_steps(task_id)
    return {
        "task_id": task_id,
        "steps": steps,
        "count": len(steps)
    }
