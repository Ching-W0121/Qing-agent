"""
手机验证码登录管理器
处理交互式手机登录流程
"""

import asyncio
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

class PhoneLoginState(Enum):
    IDLE = "idle"                    # 空闲
    WAITING_PHONE = "waiting_phone"   # 等待用户输入手机号
    SENDING_CODE = "sending_code"     # 正在发送验证码
    WAITING_CODE = "waiting_code"    # 等待用户输入验证码
    VERIFYING = "verifying"          # 验证中
    COMPLETED = "completed"          # 完成
    FAILED = "failed"                # 失败

@dataclass
class PhoneLoginSession:
    """手机登录会话"""
    user_id: int
    platform: str
    phone: Optional[str] = None
    state: PhoneLoginState = PhoneLoginState.IDLE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    # 回调函数，用于通知浏览器执行操作
    browser_action_callback: Optional[callable] = None

class PhoneLoginManager:
    """
    手机验证码登录管理器
    单例模式，管理所有手机登录会话
    """

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sessions = {}  # user_id -> PhoneLoginSession
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    async def create_session(self, user_id: int, platform: str = 'zhilian') -> PhoneLoginSession:
        """创建新的登录会话"""
        async with self._lock:
            session = PhoneLoginSession(
                user_id=user_id,
                platform=platform
            )
            self._sessions[user_id] = session
            return session

    async def get_session(self, user_id: int) -> Optional[PhoneLoginSession]:
        """获取用户的登录会话"""
        async with self._lock:
            return self._sessions.get(user_id)

    async def update_session(self, user_id: int, **kwargs) -> Optional[PhoneLoginSession]:
        """更新会话状态"""
        async with self._lock:
            session = self._sessions.get(user_id)
            if session:
                for key, value in kwargs.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                session.updated_at = time.time()
            return session

    async def set_state(self, user_id: int, state: PhoneLoginState, **kwargs) -> Optional[PhoneLoginSession]:
        """设置会话状态"""
        return await self.update_session(user_id, state=state, **kwargs)

    async def clear_session(self, user_id: int):
        """清除会话"""
        async with self._lock:
            if user_id in self._sessions:
                del self._sessions[user_id]

    async def get_status(self, user_id: int) -> Dict[str, Any]:
        """获取登录状态"""
        session = await self.get_session(user_id)
        if not session:
            return {
                "state": "no_session",
                "message": "无活跃登录会话"
            }

        state_messages = {
            PhoneLoginState.IDLE: "空闲",
            PhoneLoginState.WAITING_PHONE: "请输入手机号",
            PhoneLoginState.SENDING_CODE: "正在发送验证码...",
            PhoneLoginState.WAITING_CODE: "验证码已发送，请输入验证码",
            PhoneLoginState.VERIFYING: "验证中...",
            PhoneLoginState.COMPLETED: "登录成功",
            PhoneLoginState.FAILED: f"登录失败: {session.error}" if session.error else "登录失败"
        }

        return {
            "state": session.state.value,
            "message": state_messages.get(session.state, "未知状态"),
            "phone": session.phone,
            "error": session.error,
            "created_at": session.created_at,
            "updated_at": session.updated_at
        }

# 全局实例
phone_login_manager = PhoneLoginManager()
