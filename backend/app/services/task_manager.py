"""
任务管理器
用于跟踪和管理运行中的任务，支持任务取消
"""

import asyncio
from typing import Dict, Optional, Set
from datetime import datetime

class TaskManager:
    """
    全局任务管理器
    跟踪运行中的任务，支持任务取消
    """

    def __init__(self):
        # 任务ID -> 取消事件
        self._running_tasks: Dict[int, asyncio.Event] = {}
        # 任务ID -> 任务信息
        self._task_info: Dict[int, dict] = {}
        # 锁
        self._lock = asyncio.Lock()

    async def register_task(self, task_id: int) -> asyncio.Event:
        """
        注册一个新任务

        Args:
            task_id: 任务ID

        Returns:
            asyncio.Event: 取消事件对象
        """
        async with self._lock:
            cancel_event = asyncio.Event()
            cancel_event.set()  # 默认不取消状态
            self._running_tasks[task_id] = cancel_event
            self._task_info[task_id] = {
                'task_id': task_id,
                'started_at': datetime.now(),
                'status': 'RUNNING'
            }
            return cancel_event

    async def unregister_task(self, task_id: int):
        """
        注销任务

        Args:
            task_id: 任务ID
        """
        async with self._lock:
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
            if task_id in self._task_info:
                self._task_info[task_id]['status'] = 'COMPLETED'
                self._task_info[task_id]['ended_at'] = datetime.now()

    async def stop_task(self, task_id: int) -> bool:
        """
        请求停止任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功请求停止
        """
        async with self._lock:
            if task_id in self._running_tasks:
                # 清除事件，触发取消
                self._running_tasks[task_id].clear()
                self._task_info[task_id]['status'] = 'STOPPING'
                return True
            return False

    def is_task_running(self, task_id: int) -> bool:
        """
        检查任务是否仍在运行

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否运行中
        """
        return task_id in self._running_tasks

    def is_cancel_requested(self, task_id: int) -> bool:
        """
        检查是否请求了取消

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否请求了取消
        """
        if task_id not in self._running_tasks:
            return False
        # is_set() 返回 False 表示已被清除（请求取消）
        return not self._running_tasks[task_id].is_set()

    async def wait_for_cancel(self, task_id: int, timeout: float = None) -> bool:
        """
        等待取消请求

        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）

        Returns:
            bool: 是否收到取消请求
        """
        if task_id not in self._running_tasks:
            return False

        try:
            if timeout:
                await asyncio.wait_for(
                    self._running_tasks[task_id].wait(),
                    timeout=timeout
                )
            else:
                await self._running_tasks[task_id].wait()
            return True
        except asyncio.TimeoutError:
            return False

    def get_running_tasks(self) -> Dict[int, dict]:
        """
        获取所有运行中的任务

        Returns:
            Dict: 运行中的任务信息
        """
        return self._task_info.copy()


# 全局单例
task_manager = TaskManager()
