from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import asyncio
import sys


class BasePlatform(ABC):
    """招聘平台基类"""

    def __init__(self, name: str):
        self.name = name
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def init(self, headless: bool = False, channel: str = 'msedge'):
        """初始化浏览器 - 使用系统 Edge/Chrome"""
        # Windows asyncio fix - must use ProactorEventLoop for subprocess support
        if sys.platform == 'win32':
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
        self.playwright = await async_playwright().start()
        # 使用系统已安装的浏览器
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            channel=channel,  # 'msedge' 或 'chrome'
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        )

    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def new_page(self) -> Page:
        """创建新页面"""
        return await self.context.new_page()

    @abstractmethod
    async def login(self, cookie: str = None, username: str = None, password: str = None) -> bool:
        """登录平台"""
        pass

    @abstractmethod
    async def search_jobs(self, keyword: str, city: str, page: int = 1) -> List[Dict]:
        """搜索职位"""
        pass

    @abstractmethod
    async def get_job_detail(self, job_url: str) -> Dict:
        """获取职位详情"""
        pass

    @abstractmethod
    async def apply_job(self, job_url: str) -> Dict:
        """投递职位"""
        pass
