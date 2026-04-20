"""
任务事件管理器
用于 V3.3 任务执行步骤的实时推送
"""

import asyncio
import json
from typing import Dict, List, Callable
from collections import defaultdict


class TaskStep:
    """任务步骤"""
    STEP_LOGIN = "login"
    STEP_SEARCH = "search"
    STEP_FILTER = "filter"
    STEP_VISION = "vision"
    STEP_EMBEDDING = "embedding"
    STEP_DECISION = "decision"
    STEP_CLICK = "click"
    STEP_VERIFY = "verify"
    STEP_SAVE = "save"

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"


class TaskEventManager:
    """
    任务事件管理器
    管理 SSE 连接并推送任务执行步骤
    """

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        """初始化"""
        self._subscriptions: Dict[int, List[asyncio.Queue]] = defaultdict(list)
        self._task_steps: Dict[int, List[Dict]] = defaultdict(list)

    async def subscribe(self, task_id: int) -> asyncio.Queue:
        """
        订阅任务事件

        Args:
            task_id: 任务ID

        Returns:
            asyncio.Queue: 事件队列
        """
        queue = asyncio.Queue(maxsize=100)
        self._subscriptions[task_id].append(queue)
        return queue

    async def unsubscribe(self, task_id: int, queue: asyncio.Queue):
        """
        取消订阅

        Args:
            task_id: 任务ID
            queue: 要移除的队列
        """
        if queue in self._subscriptions[task_id]:
            self._subscriptions[task_id].remove(queue)

    async def emit(self, task_id: int, event: Dict):
        """
        发送事件到所有订阅者

        Args:
            task_id: 任务ID
            event: 事件数据
        """
        # 保存步骤到内存（即使没有订阅者也保存）
        self._task_steps[task_id].append(event)

        # 如果没有订阅者，跳过发送
        if not self._subscriptions.get(task_id):
            return

        # 发送到所有队列
        for queue in self._subscriptions[task_id]:
            try:
                await asyncio.wait_for(queue.put(event), timeout=1.0)
            except asyncio.TimeoutError:
                # 队列满了，跳过
                pass
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

    async def emit_step(self, task_id: int, step: str, status: str, message: str = "", data: Dict = None):
        """
        发送步骤事件

        Args:
            task_id: 任务ID
            step: 步骤名称 (login, vision, embedding, etc.)
            status: 状态 (pending, running, success, failed)
            message: 状态消息
            data: 额外数据
        """
        event = {
            "task_id": task_id,
            "step": step,
            "status": status,
            "message": message,
            "data": data or {},
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.emit(task_id, event)

    def get_steps(self, task_id: int) -> List[Dict]:
        """
        获取任务的所有步骤

        Args:
            task_id: 任务ID

        Returns:
            步骤列表
        """
        return self._task_steps.get(task_id, [])

    def clear_steps(self, task_id: int):
        """
        清除任务步骤记录

        Args:
            task_id: 任务ID
        """
        self._task_steps.pop(task_id, None)


# 全局实例
task_event_manager = TaskEventManager()


async def emit_task_step(task_id: int, step: str, status: str, message: str = "", data: Dict = None):
    """快捷函数：发送任务步骤"""
    await task_event_manager.emit_step(task_id, step, status, message, data)
