"""
手机验证码登录 API
用于交互式手机验证码登录流程

流程:
1. 前端输入手机号 → 后端控制浏览器输入手机号、点击发送
2. 前端显示"等待验证码"
3. 用户输入验证码 → 后端控制浏览器输入验证码、点击登录
4. 前端显示"登录成功"
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.user import User
from app.services.phone_login_manager import phone_login_manager, PhoneLoginState
from app.services.browser_controller import browser_controller_registry

router = APIRouter(prefix="/api/auth/phone-login", tags=["phone-login"])

class StartPhoneLoginRequest(BaseModel):
    user_id: int
    platform: str = "zhilian"

class SubmitPhoneRequest(BaseModel):
    user_id: int
    phone: str
    platform: str = "zhilian"

class SubmitCodeRequest(BaseModel):
    user_id: int
    code: str
    platform: str = "zhilian"

@router.get("/status/{user_id}")
async def get_phone_login_status(user_id: int):
    """
    获取手机登录状态
    前端轮询此接口获取当前登录状态
    """
    status = await phone_login_manager.get_status(user_id)
    return status

@router.post("/start")
async def start_phone_login(req: StartPhoneLoginRequest, db: Session = Depends(get_db)):
    """
    开始手机登录流程
    创建登录会话，准备接收手机号
    """
    # 验证用户存在
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 创建会话
    session = await phone_login_manager.create_session(req.user_id, req.platform)
    await phone_login_manager.set_state(
        req.user_id,
        PhoneLoginState.WAITING_PHONE,
        phone=None
    )

    # 触发浏览器打开登录页
    controller = await browser_controller_registry.get_controller()
    if controller:
        try:
            await browser_controller_registry.execute("open_login_page", {"platform": req.platform})
        except Exception as e:
            print(f"[手机登录] 触发浏览器打开登录页失败: {e}")

    return {
        "success": True,
        "message": "请在下方输入手机号",
        "state": "waiting_phone"
    }

@router.post("/submit-phone")
async def submit_phone(req: SubmitPhoneRequest, db: Session = Depends(get_db)):
    """
    用户提交手机号
    后端控制浏览器在登录页输入手机号并点击发送验证码
    """
    # 验证手机号格式
    if not req.phone or len(req.phone) != 11:
        return {
            "success": False,
            "error": "手机号格式不正确"
        }

    # 更新会话
    session = await phone_login_manager.update_session(
        req.user_id,
        phone=req.phone,
        state=PhoneLoginState.SENDING_CODE
    )

    if not session:
        raise HTTPException(status_code=404, detail="无活跃登录会话")

    print(f"[手机登录] 用户 {req.user_id} 提交手机号: {req.phone}")

    # 检查控制器是否就绪
    if not browser_controller_registry.is_ready():
        print("[手机登录] 错误: controller未注册或未就绪!")
        await phone_login_manager.set_state(
            req.user_id,
            PhoneLoginState.FAILED,
            error="浏览器控制器未就绪，请重启任务"
        )
        return {
            "success": False,
            "error": "浏览器控制器未就绪，请重启任务",
            "state": "error",
            "require_task_restart": True
        }

    # 触发浏览器输入手机号并发送验证码
    print(f"[手机登录] 获取到的controller: {browser_controller_registry.get_controller()}")

    browser_result = False
    try:
        browser_result = await browser_controller_registry.execute("input_phone", {"phone": req.phone})
        print(f"[手机登录] input_phone执行结果: {browser_result}")

        # 获取详细错误信息
        last_error = await browser_controller_registry.get_last_error()
        if last_error:
            print(f"[手机登录] 浏览器执行错误详情: {last_error}")

    except Exception as e:
        print(f"[手机登录] 触发浏览器输入手机号失败: {e}")
        await phone_login_manager.set_state(
            req.user_id,
            PhoneLoginState.FAILED,
            error=f"浏览器异常: {str(e)}"
        )
        return {
            "success": False,
            "error": "网络异常，请刷新页面重试",
            "state": "error",
            "detail": str(e)
        }

    # 检查浏览器执行结果
    if browser_result is False or browser_result is None:
        print(f"[手机登录] 浏览器输入手机号失败或返回None")
        last_error = await browser_controller_registry.get_last_error()
        error_msg = "浏览器操作失败"
        if last_error:
            if "NoneType" in last_error or "_login_page" in last_error:
                error_msg = "浏览器登录页面未就绪，请重启任务"
                await phone_login_manager.set_state(
                    req.user_id,
                    PhoneLoginState.FAILED,
                    error=error_msg
                )
                return {
                    "success": False,
                    "error": error_msg,
                    "state": "failed",
                    "require_task_restart": True
                }
            error_msg = last_error

        await phone_login_manager.set_state(
            req.user_id,
            PhoneLoginState.FAILED,
            error=error_msg
        )
        return {
            "success": False,
            "error": error_msg,
            "state": "failed"
        }

    # 更新状态为等待验证码
    await phone_login_manager.set_state(
        req.user_id,
        PhoneLoginState.WAITING_CODE,
        phone=req.phone
    )

    return {
        "success": True,
        "message": "已发送验证码，请注意查收",
        "state": "waiting_code",
        "phone": req.phone
    }

@router.post("/submit-code")
async def submit_code(req: SubmitCodeRequest, db: Session = Depends(get_db)):
    """
    用户提交验证码
    后端控制浏览器在登录页输入验证码并点击登录
    """
    if not req.code or len(req.code) != 6:
        return {
            "success": False,
            "error": "验证码格式不正确"
        }

    session = await phone_login_manager.get_session(req.user_id)

    if not session:
        raise HTTPException(status_code=404, detail="无活跃登录会话")

    if session.state != PhoneLoginState.WAITING_CODE:
        return {
            "success": False,
            "error": f"当前状态不支持验证: {session.state.value}"
        }

    print(f"[手机登录] 用户 {req.user_id} 提交验证码: {req.code}")

    # 更新状态为验证中
    await phone_login_manager.set_state(
        req.user_id,
        PhoneLoginState.VERIFYING
    )

    # 触发浏览器输入验证码并登录
    browser_result = None
    controller = await browser_controller_registry.get_controller()
    if controller:
        try:
            browser_result = await browser_controller_registry.execute("input_code", {"code": req.code})
            print(f"[手机登录] 浏览器登录结果: {browser_result}")
        except Exception as e:
            print(f"[手机登录] 触发浏览器登录失败: {e}")
            await phone_login_manager.set_state(
                req.user_id,
                PhoneLoginState.WAITING_CODE  # 重置状态，让用户可以重试
            )
            return {
                "success": False,
                "error": f"验证失败: {str(e)}",
                "state": "waiting_code"
            }

    # 检查浏览器返回结果
    if browser_result is False:
        print(f"[手机登录] 验证码错误")
        await phone_login_manager.set_state(
            req.user_id,
            PhoneLoginState.WAITING_CODE  # 重置状态，让用户可以重试
        )
        return {
            "success": False,
            "error": "验证码错误，请重新输入",
            "state": "waiting_code"
        }

    # 验证成功，更新用户凭证
    user = db.query(User).filter(User.id == req.user_id).first()
    if user and user.profile:
        credentials = user.profile.platform_credentials or {}
        platform_cred = credentials.get(req.platform, {})
        platform_cred["phone"] = session.phone
        platform_cred["phone_verified"] = True
        credentials[req.platform] = platform_cred
        user.profile.platform_credentials = credentials
        db.commit()

    # 更新状态为完成
    await phone_login_manager.set_state(
        req.user_id,
        PhoneLoginState.COMPLETED
    )

    return {
        "success": True,
        "message": "登录成功",
        "state": "completed"
    }

@router.post("/cancel")
async def cancel_phone_login(user_id: int):
    """
    取消手机登录流程
    """
    await phone_login_manager.clear_session(user_id)
    # 触发关闭登录页
    controller = await browser_controller_registry.get_controller()
    if controller:
        try:
            await browser_controller_registry.execute("close_login_page", {})
        except Exception as e:
            print(f"[手机登录] 触发关闭登录页失败: {e}")
    return {
        "success": True,
        "message": "已取消"
    }
