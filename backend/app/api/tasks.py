from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.task_run import TaskRun, TaskType, TaskStatus
from app.schemas.task import TaskCreate, TaskResponse
from app.services.crawler_runner import run_job_collect_task, run_v3_login, run_v3_auto_apply, run_v3_full_flow
from app.services.task_manager import task_manager
from pydantic import BaseModel
import asyncio

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

class LoginRequest(BaseModel):
    user_id: int
    platform: str = "zhilian"  # zhilian, boss, job51

class LoginResponse(BaseModel):
    success: bool
    message: str
    platform: str

class AutoApplyRequest(BaseModel):
    user_id: int
    job_url: str
    platform: str = "zhilian"

class V3FullFlowRequest(BaseModel):
    user_id: int
    platform: str = "zhilian"

@router.post("/run", response_model=TaskResponse)
async def trigger_task(task: TaskCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """触发任务"""
    # 创建任务记录
    task_run = TaskRun(
        user_id=task.user_id,
        task_type=TaskType(task.task_type),
        status=TaskStatus.RUNNING
    )
    db.add(task_run)
    db.commit()
    db.refresh(task_run)

    # 后台执行
    background_tasks.add_task(execute_task, task_run.id, task.user_id, task.task_type, db)

    return task_run

@router.post("/login", response_model=LoginResponse)
async def trigger_login(login_req: LoginRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """触发平台登录任务"""
    # 创建任务记录
    task_run = TaskRun(
        user_id=login_req.user_id,
        task_type=TaskType.SEARCH,  # 使用 SEARCH 类型（登录也是一种搜索准备）
        status=TaskStatus.RUNNING
    )
    db.add(task_run)
    db.commit()
    db.refresh(task_run)

    # 后台执行登录
    background_tasks.add_task(execute_login, task_run.id, login_req.user_id, login_req.platform, db)

    return LoginResponse(
        success=True,
        message=f"登录任务已启动 (任务ID: {task_run.id})",
        platform=login_req.platform
    )

@router.post("/v3/login")
async def trigger_v3_login(login_req: LoginRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    V3.3 智能登录接口
    使用 Vision + Embedding + Decision Engine 进行智能登录
    """
    # 创建任务记录
    task_run = TaskRun(
        user_id=login_req.user_id,
        task_type=TaskType.SEARCH,
        status=TaskStatus.RUNNING
    )
    db.add(task_run)
    db.commit()
    db.refresh(task_run)

    # 后台执行 V3.3 登录
    background_tasks.add_task(execute_v3_login, task_run.id, login_req.user_id, login_req.platform, db)

    return {
        "success": True,
        "message": f"V3.3 登录任务已启动 (任务ID: {task_run.id})",
        "platform": login_req.platform,
        "task_id": task_run.id
    }

@router.post("/v3/auto-apply")
async def trigger_v3_auto_apply(apply_req: AutoApplyRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    V3.3 自动投递接口
    使用 Vision + Embedding + Decision Engine 进行智能投递
    """
    # 创建任务记录
    task_run = TaskRun(
        user_id=apply_req.user_id,
        task_type=TaskType.APPLY,
        status=TaskStatus.RUNNING
    )
    db.add(task_run)
    db.commit()
    db.refresh(task_run)

    # 后台执行 V3.3 投递
    background_tasks.add_task(
        execute_v3_auto_apply,
        task_run.id,
        apply_req.user_id,
        apply_req.job_url,
        apply_req.platform,
        db
    )

    return {
        "success": True,
        "message": f"V3.3 投递任务已启动 (任务ID: {task_run.id})",
        "job_url": apply_req.job_url,
        "platform": apply_req.platform,
        "task_id": task_run.id
    }

@router.post("/v3/full-flow")
async def trigger_v3_full_flow(flow_req: V3FullFlowRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    V3.3 完整流程接口
    1. V3.3 智能登录
    2. 搜索并匹配职位
    3. 自动投递匹配职位
    4. 学习投递结果
    """
    # 创建任务记录
    task_run = TaskRun(
        user_id=flow_req.user_id,
        task_type=TaskType.APPLY,
        status=TaskStatus.RUNNING
    )
    db.add(task_run)
    db.commit()
    db.refresh(task_run)

    # 后台执行 V3.3 完整流程
    background_tasks.add_task(execute_v3_full_flow, task_run.id, flow_req.user_id, flow_req.platform, db)

    return {
        "success": True,
        "message": f"V3.3 完整流程已启动 (任务ID: {task_run.id})",
        "platform": flow_req.platform,
        "task_id": task_run.id
    }

@router.post("/{task_id}/stop")
async def stop_task(task_id: int, db: Session = Depends(get_db)):
    """
    停止运行中的任务

    Args:
        task_id: 任务ID

    Returns:
        dict: 停止操作结果
    """
    # 查询任务
    task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
    if not task_run:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task_run.status != TaskStatus.RUNNING:
        return {
            "success": False,
            "message": f"任务状态为 {task_run.status}，无法停止",
            "task_id": task_id
        }

    # 请求停止任务
    success = await task_manager.stop_task(task_id)

    if success:
        # 更新任务状态
        task_run.status = TaskStatus.FAILED
        task_run.result_data = {
            'success': False,
            'error': '用户主动停止任务',
            'stopped_by_user': True
        }
        db.commit()

        return {
            "success": True,
            "message": f"已请求停止任务 {task_id}",
            "task_id": task_id
        }
    else:
        return {
            "success": False,
            "message": f"任务 {task_id} 不在运行中",
            "task_id": task_id
        }

async def execute_login(task_id: int, user_id: int, platform: str, db_session: Session):
    """执行平台登录"""
    from app.models.task_run import TaskRun, TaskStatus
    from app.core.database import SessionLocal
    from app.models.user import User

    db = SessionLocal()

    try:
        # 获取用户凭证
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.profile:
            raise Exception("用户或用户画像不存在")

        credentials = user.profile.platform_credentials or {}
        platform_cred = credentials.get(platform, {})

        # 导入平台类
        import sys
        from pathlib import Path
        playwright_root = Path(__file__).parent.parent.parent.parent / 'playwright' / 'src'
        sys.path.insert(0, str(playwright_root))

        if platform == 'zhilian':
            from platforms.zhilian import ZhilianPlatform
            platform_class = ZhilianPlatform
        elif platform == 'boss':
            from platforms.boss import BossPlatform
            platform_class = BossPlatform
        elif platform == 'job51':
            from platforms.job51 import Job51Platform
            platform_class = Job51Platform
        else:
            raise Exception(f"不支持的平台: {platform}")

        # 初始化平台并登录
        p = platform_class()
        await p.init(headless=True)

        login_success = False
        if platform_cred.get('cookie'):
            login_success = await p.login(cookie=platform_cred['cookie'])
            login_msg = "Cookie登录"
        elif platform_cred.get('username') and platform_cred.get('password'):
            login_success = await p.login(
                username=platform_cred['username'],
                password=platform_cred['password']
            )
            login_msg = "账号密码登录"
        else:
            login_msg = "无有效凭证"

        await p.close()

        # 更新任务状态
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            task_run.status = TaskStatus.COMPLETED if login_success else TaskStatus.FAILED
            task_run.result_data = {
                'success': login_success,
                'message': f"{login_msg} - {'成功' if login_success else '失败'}",
                'platform': platform
            }
            db.commit()

    except Exception as e:
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            task_run.status = TaskStatus.FAILED
            task_run.result_data = {'success': False, 'error': str(e), 'platform': platform}
            db.commit()
    finally:
        db.close()

async def execute_task(task_id: int, user_id: int, task_type: str, db_session: Session):
    """执行任务"""
    from app.models.task_run import TaskRun, TaskStatus
    from app.core.database import SessionLocal

    # 创建新的数据库 session
    db = SessionLocal()

    try:
        # 运行爬虫(采集)
        result = await run_job_collect_task(db, user_id, 'zhilian')

        # 更新任务状态
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            task_run.status = TaskStatus.COMPLETED if result.get('success') else TaskStatus.FAILED
            task_run.result_data = result
            # 填充统计字段
            task_run.jobs_found = result.get('searched', 0)
            task_run.jobs_filtered = result.get('matched', 0)
            task_run.applications_submitted = result.get('collected', 0)
            # results 是列表，转为 dict 存储
            task_run.details = {'results': result.get('results', [])}
            db.commit()

    except Exception as e:
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            task_run.status = TaskStatus.FAILED
            task_run.result_data = {'error': str(e)}
            db.commit()
    finally:
        db.close()

async def execute_v3_login(task_id: int, user_id: int, platform: str, db_session: Session):
    """执行 V3.3 智能登录"""
    from app.models.task_run import TaskRun, TaskStatus
    from app.core.database import SessionLocal

    db = SessionLocal()

    try:
        result = await run_v3_login(db, user_id, platform)

        # 更新任务状态
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            task_run.status = TaskStatus.COMPLETED if result.get('success') else TaskStatus.FAILED
            task_run.result_data = result
            db.commit()

    except Exception as e:
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            task_run.status = TaskStatus.FAILED
            task_run.result_data = {'success': False, 'error': str(e), 'platform': platform}
            db.commit()
    finally:
        db.close()

async def execute_v3_auto_apply(task_id: int, user_id: int, job_url: str, platform: str, db_session: Session):
    """执行 V3.3 智能投递"""
    from app.models.task_run import TaskRun, TaskStatus
    from app.core.database import SessionLocal

    db = SessionLocal()

    try:
        result = await run_v3_auto_apply(db, user_id, job_url, platform)

        # 更新任务状态
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            task_run.status = TaskStatus.COMPLETED if result.get('success') else TaskStatus.FAILED
            task_run.result_data = result
            db.commit()

    except Exception as e:
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            task_run.status = TaskStatus.FAILED
            task_run.result_data = {'success': False, 'error': str(e), 'platform': platform}
            db.commit()
    finally:
        db.close()

async def execute_v3_full_flow(task_id: int, user_id: int, platform: str, db_session: Session):
    """执行 V3.3 完整流程"""
    from app.models.task_run import TaskRun, TaskStatus
    from app.core.database import SessionLocal

    db = SessionLocal()
    cancel_event = None

    try:
        # 注册任务，获取取消事件
        cancel_event = await task_manager.register_task(task_id)

        # 检查是否已请求取消
        if task_manager.is_cancel_requested(task_id):
            raise Exception("任务被用户取消")

        result = await run_v3_full_flow(db, user_id, platform, task_id, cancel_event)

        # 检查是否被取消
        if task_manager.is_cancel_requested(task_id):
            result['stopped'] = True
            result['stopped_by_user'] = True

        # 更新任务状态
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            task_run.status = TaskStatus.COMPLETED if result.get('success') else TaskStatus.FAILED
            task_run.result_data = result
            task_run.jobs_found = result.get('jobs_found', 0)
            task_run.jobs_filtered = result.get('jobs_matched', 0)
            task_run.applications_submitted = result.get('applied_count', 0)
            db.commit()

        # 发送完成事件
        from app.services.task_event_manager import emit_task_step
        await emit_task_step(task_id, "complete", "success", "任务完成", result)

    except Exception as e:
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            task_run.status = TaskStatus.FAILED
            task_run.result_data = {'success': False, 'error': str(e), 'platform': platform}
            db.commit()

        # 发送失败事件
        from app.services.task_event_manager import emit_task_step
        await emit_task_step(task_id, "complete", "failed", f"任务失败: {str(e)}", None)

    finally:
        # 注销任务
        if cancel_event:
            await task_manager.unregister_task(task_id)
        db.close()

@router.get("/user/{user_id}")
def get_user_tasks(user_id: int, db: Session = Depends(get_db)):
    """获取用户的所有任务"""
    tasks = db.query(TaskRun).filter(TaskRun.user_id == user_id).order_by(TaskRun.created_at.desc()).limit(10).all()
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskRun).filter(TaskRun.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
