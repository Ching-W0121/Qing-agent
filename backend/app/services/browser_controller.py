"""
全局浏览器控制器注册表
用于在任务运行时注册浏览器控制回调
"""

from typing import Optional, Dict, Callable, Any
import asyncio

class BrowserControllerRegistry:
    """
    浏览器控制器注册表
    单例模式，管理全局浏览器控制回调
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._controller = None
            cls._instance._platform_name = None
            cls._instance._lock = asyncio.Lock()
            cls._instance._last_error = None
        return cls._instance

    async def register(self, platform_name: str, controller: Callable):
        """注册浏览器控制器"""
        async with self._lock:
            self._controller = controller
            self._platform_name = platform_name
            self._last_error = None
            print(f"[BrowserController] 已注册 {platform_name} 的浏览器控制器")

    async def unregister(self):
        """取消注册"""
        async with self._lock:
            self._controller = None
            self._platform_name = None
            print(f"[BrowserController] 已取消注册")

    async def get_controller(self) -> Optional[Callable]:
        """获取控制器"""
        return self._controller

    async def get_platform_name(self) -> Optional[str]:
        """获取平台名称"""
        return self._platform_name

    async def get_last_error(self) -> Optional[str]:
        """获取最后的错误信息"""
        return self._last_error

    def is_ready(self) -> bool:
        """检查控制器是否就绪"""
        return self._controller is not None

    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """执行浏览器控制操作"""
        if not self._controller:
            self._last_error = "没有已注册的控制器"
            print(f"[BrowserController] {self._last_error}")
            return None

        try:
            result = await self._controller(action, params)
            self._last_error = None  # 清除错误
            return result
        except AttributeError as e:
            self._last_error = f"属性错误: {str(e)}"
            print(f"[BrowserController] 执行 {action} 时发生属性错误: {e}")
            print(f"[BrowserController] 这通常意味着浏览器页面已关闭或未初始化")
            return None
        except TypeError as e:
            self._last_error = f"类型错误: {str(e)}"
            print(f"[BrowserController] 执行 {action} 时发生类型错误: {e}")
            return None
        except Exception as e:
            self._last_error = f"执行失败: {str(e)}"
            print(f"[BrowserController] 执行 {action} 失败: {e}")
            import traceback
            traceback.print_exc()
            return None

# 全局实例
browser_controller_registry = BrowserControllerRegistry()
