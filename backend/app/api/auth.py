"""
验证码登录 API
用于手机号验证码登录
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import random
import time

from app.core.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 存储验证码（生产环境应使用 Redis）
verification_codes = {}

class SendCodeRequest(BaseModel):
    user_id: int
    phone: str
    platform: str = "zhilian"

class VerifyCodeRequest(BaseModel):
    user_id: int
    phone: str
    code: str
    platform: str = "zhilian"

class PhoneLoginRequest(BaseModel):
    user_id: int
    phone: str
    platform: str = "zhilian"

class LoginStatusResponse(BaseModel):
    waiting_for_code: bool
    code_sent: bool
    verified: bool
    phone: Optional[str] = None
    error: Optional[str] = None

@router.post("/send-code")
async def send_verification_code(req: SendCodeRequest, db: Session = Depends(get_db)):
    """
    发送验证码到手机号
    模拟发送验证码（实际应接入短信网关）
    """
    # 验证用户存在
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 生成6位验证码
    code = str(random.randint(100000, 999999))

    # 存储验证码（5分钟有效）
    key = f"{req.user_id}:{req.platform}:{req.phone}"
    verification_codes[key] = {
        "code": code,
        "created_at": time.time(),
        "phone": req.phone,
        "verified": False
    }

    # TODO: 实际发送短信验证码
    # 这里模拟发送成功
    print(f"[验证码] 向 {req.phone} 发送验证码: {code}")

    return {
        "success": True,
        "message": f"验证码已发送到 {req.phone}",
        "expires_in": 300  # 5分钟有效
    }

@router.post("/verify-code")
async def verify_code(req: VerifyCodeRequest, db: Session = Depends(get_db)):
    """
    验证验证码
    """
    key = f"{req.user_id}:{req.platform}:{req.phone}"
    stored = verification_codes.get(key)

    if not stored:
        return {
            "success": False,
            "error": "请先发送验证码"
        }

    # 检查是否过期（5分钟）
    if time.time() - stored["created_at"] > 300:
        del verification_codes[key]
        return {
            "success": False,
            "error": "验证码已过期，请重新发送"
        }

    # 验证验证码
    if stored["code"] != req.code:
        return {
            "success": False,
            "error": "验证码错误"
        }

    # 标记为已验证
    stored["verified"] = True

    # 更新用户凭证中的手机号
    user = db.query(User).filter(User.id == req.user_id).first()
    if user and user.profile:
        credentials = user.profile.platform_credentials or {}
        platform_cred = credentials.get(req.platform, {})
        platform_cred["phone"] = req.phone
        platform_cred["phone_verified"] = True
        credentials[req.platform] = platform_cred
        user.profile.platform_credentials = credentials
        db.commit()

    return {
        "success": True,
        "message": "验证成功",
        "phone": req.phone
    }

@router.get("/login-status/{user_id}")
async def get_login_status(user_id: int, platform: str = "zhilian", db: Session = Depends(get_db)):
    """
    获取手机登录状态
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查是否有待验证的验证码
    credentials = user.profile.platform_credentials or {} if user.profile else {}
    platform_cred = credentials.get(platform, {})
    phone = platform_cred.get("phone")

    # 检查是否有等待验证的请求
    waiting = False
    code_sent = False
    verified = platform_cred.get("phone_verified", False)

    if phone:
        key = f"{user_id}:{platform}:{phone}"
        stored = verification_codes.get(key)
        if stored and not stored.get("verified", False):
            waiting = True
            code_sent = True

    return LoginStatusResponse(
        waiting_for_code=waiting,
        code_sent=code_sent,
        verified=verified,
        phone=phone
    )

@router.post("/phone-login")
async def phone_login(req: PhoneLoginRequest, db: Session = Depends(get_db)):
    """
    请求手机验证码登录（触发发送验证码）
    """
    return await send_verification_code(SendCodeRequest(
        user_id=req.user_id,
        phone=req.phone,
        platform=req.platform
    ), db)
