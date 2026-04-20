"""
V3.3 Recovery Engine - 自动错误恢复引擎
自动错误恢复用于浏览器自动化

基于 agent-V3.html 架构:
- 页面异常处理
- 基于视觉的错误识别
- 嵌入降级
- 远程对话

Author: Recovery Engine Team
Version: 3.3
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import logging

# 配置日志
logger = logging.getLogger(__name__)


class RecoveryAction(Enum):
    """恢复动作枚举"""
    CLOSE_POPUP = "close_popup"
    AUTO_LOGIN = "auto_login_flow"
    VISION_REPARSE = "vision_reparse"
    EMBEDDING_FALLBACK = "embedding_fallback"
    ASK_REMOTE = "ask_remote"
    RETRY = "retry"
    ABORT = "abort"
    SCROLL = "scroll"
    REFRESH = "refresh"
    SKIP = "skip"  # 跳过当前职位（用于招聘者页面或无投递按钮情况）


class PageState(Enum):
    """页面状态枚举 - 触发恢复的状态"""
    LOGIN = "login"
    POPUP = "popup"
    CAPTCHA = "captcha"
    UNKNOWN = "unknown"
    NORMAL = "normal"
    ERROR = "error"
    RECRUITER_PAGE = "recruiter_page"  # 招聘者页面（HR视角）- 应该跳过
    NO_APPLY_BUTTON = "no_apply_button"  # 没有投递按钮 - 应该跳过


# 常见的弹窗关闭选择器
CLOSE_SELECTORS = [
    '.close',
    '.modal-close',
    '.dialog-close',
    '[class*="close"]',
    '[class*="modal"] [class*="close"]',
    '.popup-close',
    '.tips-close',
    'button.close',
    '.btn-close',
    '[aria-label="Close"]',
    '[aria-label="close"]',
    '.close-btn',
    '.modal-header .close',
    '.modal-footer .close',
]

# 登录表单选择器
LOGIN_SELECTORS = {
    'username': [
        'input[name="username"]',
        'input[id="username"]',
        'input[type="text"]',
        'input[placeholder*="user" i]',
        'input[placeholder*="账号" i]',
        '#username',
    ],
    'password': [
        'input[name="password"]',
        'input[id="password"]',
        'input[type="password"]',
        'input[placeholder*="pass" i]',
        'input[placeholder*="密码" i]',
        '#password',
    ],
    'submit': [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("登录")',
        'button:has-text("登录" i)',
        'button:has-text("Sign" i)',
        '.login-btn',
        '#login-btn',
    ]
}


@dataclass
class RecoveryResult:
    """恢复尝试的结果"""
    success: bool
    action: RecoveryAction
    message: str
    next_state: Optional[PageState] = None
    requires_remote: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.next_state is None:
            self.next_state = PageState.NORMAL if self.success else PageState.ERROR


class RecoveryEngine:
    """
    V3.3 恢复引擎
    用于浏览器自动化的自动错误恢复

    支持的恢复策略:
    - 弹窗关闭
    - 自动登录
    - 验证码处理
    - 未知状态视觉重新解析
    - 嵌入服务降级
    - 远程人工干预

    使用示例:
        engine = RecoveryEngine()
        engine.register_handler(PageState.POPUP, custom_popup_handler)

        result = await engine.recover(PageState.POPUP, {'page': page})
        if result.requires_remote:
            # 请求远程人工帮助
            pass
    """

    def __init__(self):
        """初始化恢复引擎"""
        self.recovery_handlers: Dict[PageState, Callable] = {}
        self.max_retries = 3
        self.retry_delays = [1, 2, 5]  # 秒
        self._vision_service = None
        self._embedding_service = None
        self._credentials: Dict[str, str] = {}
        self._last_error: Optional[Exception] = None

        # 注册默认处理器
        self._register_default_handlers()

        logger.info("RecoveryEngine V3.3 初始化完成")

    def _register_default_handlers(self):
        """注册默认的恢复处理器"""
        self.register_handler(PageState.POPUP, self.handle_popup)
        self.register_handler(PageState.LOGIN, self.handle_login)
        self.register_handler(PageState.CAPTCHA, self.handle_captcha)
        self.register_handler(PageState.UNKNOWN, self.handle_unknown)
        self.register_handler(PageState.RECRUITER_PAGE, self.handle_recruiter_page)
        self.register_handler(PageState.NO_APPLY_BUTTON, self.handle_no_apply_button)

    def set_vision_service(self, vision_service: Any):
        """设置视觉服务用于页面重新解析"""
        self._vision_service = vision_service
        logger.debug("视觉服务已设置")

    def set_embedding_service(self, embedding_service: Any):
        """设置嵌入服务用于状态分类"""
        self._embedding_service = embedding_service
        logger.debug("嵌入服务已设置")

    def set_credentials(self, username: str, password: str):
        """设置登录凭据"""
        self._credentials = {
            'username': username,
            'password': password
        }
        logger.debug("登录凭据已设置")

    def register_handler(self, state: PageState, handler: Callable):
        """
        为指定状态注册恢复处理器

        Args:
            state: 页面状态
            handler: 异步处理函数，接收 (page, context) 返回 RecoveryResult
        """
        self.recovery_handlers[state] = handler
        logger.debug(f"已注册处理器: {state.value} -> {handler.__name__}")

    def unregister_handler(self, state: PageState) -> bool:
        """
        注销指定状态的处理器

        Args:
            state: 页面状态

        Returns:
            bool: 是否成功注销
        """
        if state in self.recovery_handlers:
            del self.recovery_handlers[state]
            logger.debug(f"已注销处理器: {state.value}")
            return True
        return False

    async def recover(self, state: PageState, context: Dict) -> RecoveryResult:
        """
        执行给定状态的恢复

        Args:
            state: 页面状态
            context: 恢复上下文，包含 page 对象和其他信息

        Returns:
            RecoveryResult: 恢复结果
        """
        logger.info(f"开始恢复流程: 状态={state.value}")

        # 查找注册的处理器
        handler = self.recovery_handlers.get(state)

        if handler is None:
            logger.warning(f"未找到状态 {state.value} 的处理器")
            return RecoveryResult(
                success=False,
                action=RecoveryAction.ABORT,
                message=f"未注册状态 {state.value} 的处理器",
                next_state=PageState.ERROR
            )

        try:
            # 执行恢复处理
            result = await handler(context.get('page'), context)
            logger.info(f"恢复完成: success={result.success}, action={result.action.value}")
            return result

        except Exception as e:
            logger.error(f"恢复过程异常: {e}", exc_info=True)
            self._last_error = e
            return RecoveryResult(
                success=False,
                action=RecoveryAction.ABORT,
                message=f"恢复异常: {str(e)}",
                next_state=PageState.ERROR,
                metadata={'exception': str(e)}
            )

    async def handle_popup(self, page, context: Dict) -> RecoveryResult:
        """
        处理弹窗状态

        策略:
        1. 尝试使用视觉服务定位关闭按钮
        2. 尝试常见选择器
        3. 按 ESC 键
        4. 尝试点击遮罩层关闭

        Args:
            page: Playwright page 对象
            context: 上下文信息

        Returns:
            RecoveryResult: 恢复结果
        """
        logger.info("处理弹窗状态")

        # 策略1: 尝试视觉服务定位关闭按钮
        if self._vision_service and page:
            try:
                vision_result = await self._try_vision_close(page)
                if vision_result.success:
                    return vision_result
            except Exception as e:
                logger.debug(f"视觉服务关闭失败: {e}")

        # 策略2: 尝试常见选择器
        if page:
            for selector in CLOSE_SELECTORS:
                try:
                    # 检查元素是否存在
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=1000):
                        await element.click(timeout=2000)
                        logger.info(f"成功点击关闭按钮: {selector}")
                        return RecoveryResult(
                            success=True,
                            action=RecoveryAction.CLOSE_POPUP,
                            message=f"成功关闭弹窗: {selector}",
                            next_state=PageState.NORMAL,
                            metadata={'selector': selector}
                        )
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue

        # 策略3: 按 ESC 键
        if page:
            try:
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
                logger.info("已发送 ESC 键")

                # 验证弹窗是否关闭
                # 简单检查 - 实际应用中可能需要更复杂的验证
                return RecoveryResult(
                    success=True,
                    action=RecoveryAction.CLOSE_POPUP,
                    message="已尝试 ESC 键关闭",
                    next_state=PageState.NORMAL,
                    metadata={'method': 'escape_key'}
                )
            except Exception as e:
                logger.debug(f"ESC 键失败: {e}")

        # 策略4: 请求远程帮助
        logger.warning("所有本地关闭策略失败，需要远程干预")
        return RecoveryResult(
            success=False,
            action=RecoveryAction.ASK_REMOTE,
            message="无法自动关闭弹窗，请人工干预",
            next_state=PageState.POPUP,
            requires_remote=True,
            metadata={
                'tried_selectors': CLOSE_SELECTORS[:5],  # 只记录前5个
                'reason': 'all_local_strategies_failed'
            }
        )

    async def _try_vision_close(self, page) -> RecoveryResult:
        """
        使用视觉服务尝试关闭弹窗

        Args:
            page: Playwright page 对象

        Returns:
            RecoveryResult: 视觉服务尝试结果
        """
        try:
            # 调用视觉服务分析页面
            analysis = await self._vision_service.analyze_page(page)

            if analysis and hasattr(analysis, 'popup_close_button'):
                button = analysis.popup_close_button
                if button:
                    await page.click(button, timeout=2000)
                    return RecoveryResult(
                        success=True,
                        action=RecoveryAction.CLOSE_POPUP,
                        message="通过视觉服务定位关闭弹窗",
                        next_state=PageState.NORMAL
                    )

        except Exception as e:
            logger.debug(f"视觉关闭异常: {e}")

        return RecoveryResult(
            success=False,
            action=RecoveryAction.VISION_REPARSE,
            message="视觉服务未能关闭弹窗",
            next_state=PageState.POPUP
        )

    async def handle_login(self, page, context: Dict) -> RecoveryResult:
        """
        处理登录状态

        策略:
        1. 检查是否已有有效会话
        2. 填充用户名和密码
        3. 点击登录按钮
        4. 等待登录完成

        Args:
            page: Playwright page 对象
            context: 上下文信息

        Returns:
            RecoveryResult: 恢复结果
        """
        logger.info("处理登录状态")

        if not page:
            return RecoveryResult(
                success=False,
                action=RecoveryAction.ABORT,
                message="页面对象不可用",
                next_state=PageState.ERROR
            )

        # 检查凭据是否可用
        if not self._credentials:
            logger.warning("未配置登录凭据，尝试从上下文获取")
            self._credentials = context.get('credentials', {})

        if not self._credentials.get('username') or not self._credentials.get('password'):
            return RecoveryResult(
                success=False,
                action=RecoveryAction.ASK_REMOTE,
                message="缺少登录凭据，请提供用户名和密码",
                next_state=PageState.LOGIN,
                requires_remote=True,
                metadata={'reason': 'missing_credentials'}
            )

        # 策略1: 填充用户名
        username_filled = False
        for selector in LOGIN_SELECTORS['username']:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=1000):
                    await element.fill(self._credentials['username'])
                    username_filled = True
                    logger.debug(f"用户名已填充: {selector}")
                    break
            except Exception:
                continue

        if not username_filled:
            return RecoveryResult(
                success=False,
                action=RecoveryAction.ABORT,
                message="无法找到用户名输入框",
                next_state=PageState.LOGIN,
                metadata={'phase': 'username'}
            )

        # 策略2: 填充密码
        password_filled = False
        for selector in LOGIN_SELECTORS['password']:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=1000):
                    await element.fill(self._credentials['password'])
                    password_filled = True
                    logger.debug(f"密码已填充: {selector}")
                    break
            except Exception:
                continue

        if not password_filled:
            return RecoveryResult(
                success=False,
                action=RecoveryAction.ABORT,
                message="无法找到密码输入框",
                next_state=PageState.LOGIN,
                metadata={'phase': 'password'}
            )

        # 策略3: 点击登录按钮
        login_clicked = False
        for selector in LOGIN_SELECTORS['submit']:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=1000):
                    await element.click(timeout=3000)
                    login_clicked = True
                    logger.info(f"已点击登录按钮: {selector}")
                    break
            except Exception:
                continue

        if not login_clicked:
            return RecoveryResult(
                success=False,
                action=RecoveryAction.ABORT,
                message="无法找到登录按钮",
                next_state=PageState.LOGIN,
                metadata={'phase': 'submit'}
            )

        # 等待登录完成
        await asyncio.sleep(1)

        return RecoveryResult(
            success=True,
            action=RecoveryAction.AUTO_LOGIN,
            message="自动登录流程完成",
            next_state=PageState.NORMAL,
            metadata={
                'username': self._credentials.get('username', '')[:3] + '***'  # 脱敏
            }
        )

    async def handle_captcha(self, page, context: Dict) -> RecoveryResult:
        """
        处理验证码状态

        验证码需要人工干预，此方法会请求远程帮助

        Args:
            page: Playwright page 对象
            context: 上下文信息

        Returns:
            RecoveryResult: 恢复结果，requires_remote=True
        """
        logger.warning("检测到验证码，需要人工干预")

        captcha_type = context.get('captcha_type', 'unknown')

        # 生成人工解决说明
        instructions = self._generate_captcha_instructions(captcha_type, page)

        return RecoveryResult(
            success=False,
            action=RecoveryAction.ASK_REMOTE,
            message="验证码检测，需要人工解决",
            next_state=PageState.CAPTCHA,
            requires_remote=True,
            metadata={
                'captcha_type': captcha_type,
                'instructions': instructions,
                'page_title': context.get('page_title', ''),
                'url': context.get('url', '')
            }
        )

    def _generate_captcha_instructions(self, captcha_type: str, page) -> str:
        """
        生成验证码解决说明

        Args:
            captcha_type: 验证码类型
            page: Playwright page 对象

        Returns:
            str: 解决说明
        """
        base_instructions = {
            'image': "请识别图片中的字符并在输入框中填写",
            'slider': "请滑动滑块完成验证",
            'click': "请按照提示点击相应图片区域",
            'sms': "请查收短信并将验证码填写到输入框",
            'email': "请查收邮件并将验证码填写到输入框",
        }

        instruction = base_instructions.get(captcha_type, "请根据页面提示完成验证")

        # 获取页面标题帮助定位
        try:
            title = page.title() if page else ''
        except Exception:
            title = ''

        return f"{instruction} (页面: {title})"

    async def handle_unknown(self, page, context: Dict) -> RecoveryResult:
        """
        处理未知状态

        策略:
        1. 使用视觉服务重新解析页面
        2. 使用嵌入服务分类页面状态
        3. 如果仍无法确定，请求远程帮助

        Args:
            page: Playwright page 对象
            context: 上下文信息

        Returns:
            RecoveryResult: 恢复结果
        """
        logger.info("处理未知状态，触发视觉+嵌入分析")

        detected_state = PageState.UNKNOWN
        analysis_details = {}

        # 策略1: 视觉服务重新解析
        if self._vision_service and page:
            try:
                logger.debug("调用视觉服务分析页面")
                vision_analysis = await self._retry_with_backoff(
                    self._vision_service.analyze_page,
                    page
                )

                if vision_analysis:
                    analysis_details['vision'] = {
                        'page_type': getattr(vision_analysis, 'page_type', None),
                        'confidence': getattr(vision_analysis, 'confidence', 0),
                        'has_popup': getattr(vision_analysis, 'has_popup', False),
                        'is_login': getattr(vision_analysis, 'is_login', False),
                    }

                    # 根据视觉分析更新状态
                    if vision_analysis.is_login:
                        detected_state = PageState.LOGIN
                    elif vision_analysis.has_popup:
                        detected_state = PageState.POPUP

            except Exception as e:
                logger.debug(f"视觉分析失败: {e}")
                analysis_details['vision_error'] = str(e)

        # 策略2: 嵌入服务分类
        if self._embedding_service and page:
            try:
                logger.debug("调用嵌入服务分类页面")
                # 获取页面文本/截图
                page_text = await page.content() if page else ""

                embedding_result = await self._retry_with_backoff(
                    self._embedding_service.classify,
                    page_text
                )

                if embedding_result:
                    analysis_details['embedding'] = {
                        'category': getattr(embedding_result, 'category', None),
                        'confidence': getattr(embedding_result, 'confidence', 0),
                    }

                    # 尝试映射到已知状态
                    state_mapping = {
                        'login': PageState.LOGIN,
                        'popup': PageState.POPUP,
                        'captcha': PageState.CAPTCHA,
                        'error': PageState.ERROR,
                    }

                    if detected_state == PageState.UNKNOWN:
                        mapped = state_mapping.get(embedding_result.category)
                        if mapped:
                            detected_state = mapped

            except Exception as e:
                logger.debug(f"嵌入分类失败: {e}")
                analysis_details['embedding_error'] = str(e)

        # 策略3: 如果仍是未知状态，尝试常见模式匹配
        if detected_state == PageState.UNKNOWN and page:
            detected_state = await self._detect_state_by_selectors(page)

        # 决定下一步
        if detected_state != PageState.UNKNOWN:
            logger.info(f"状态识别成功: {detected_state.value}")

            # 尝试执行该状态的恢复
            handler = self.recovery_handlers.get(detected_state)
            if handler:
                try:
                    result = await handler(page, context)
                    result.metadata['detected_state'] = detected_state.value
                    result.metadata['analysis'] = analysis_details
                    return result
                except Exception as e:
                    logger.debug(f"状态 {detected_state.value} 恢复失败: {e}")

            return RecoveryResult(
                success=True,
                action=RecoveryAction.VISION_REPARSE,
                message=f"状态已识别为 {detected_state.value}",
                next_state=detected_state,
                metadata={
                    'detected_state': detected_state.value,
                    'analysis': analysis_details
                }
            )

        # 无法识别，请求远程帮助
        logger.warning("无法自动识别页面状态，请求远程干预")
        return RecoveryResult(
            success=False,
            action=RecoveryAction.ASK_REMOTE,
            message="无法自动识别页面状态，请人工确认",
            next_state=PageState.UNKNOWN,
            requires_remote=True,
            metadata={
                'analysis': analysis_details,
                'reason': 'cannot_identify_state'
            }
        )

    async def handle_recruiter_page(self, page, context: Dict) -> RecoveryResult:
        """
        处理招聘者页面（HR/雇主视角）

        策略:
        - 检测到招聘者页面时，应该跳过当前职位
        - 因为这不是求职者视角，无法进行投递操作

        Args:
            page: Playwright page 对象
            context: 上下文信息

        Returns:
            RecoveryResult: 恢复结果，指示跳过当前职位
        """
        logger.info("检测到招聘者页面（HR视角），跳过当前职位")

        return RecoveryResult(
            success=True,
            action=RecoveryAction.SKIP,
            message="招聘者页面（HR视角），跳过投递",
            next_state=PageState.RECRUITER_PAGE,
            metadata={
                'reason': 'recruiter_page_detected',
                'action': 'skip_current_job',
                'suggestion': '该页面是HR/雇主视角，不是求职者视角，无法投递'
            }
        )

    async def handle_no_apply_button(self, page, context: Dict) -> RecoveryResult:
        """
        处理没有投递按钮的情况

        策略:
        - 检测到没有投递按钮时，应该跳过当前职位
        - 可能职位已过期、已下架、或不需要投递

        Args:
            page: Playwright page 对象
            context: 上下文信息（应包含job_url）

        Returns:
            RecoveryResult: 恢复结果，指示跳过当前职位
        """
        job_url = context.get('job_url', 'unknown')
        logger.info(f"检测到没有投递按钮，跳过职位: {job_url}")

        return RecoveryResult(
            success=True,
            action=RecoveryAction.SKIP,
            message=f"没有找到投递按钮，跳过该职位",
            next_state=PageState.NO_APPLY_BUTTON,
            metadata={
                'reason': 'no_apply_button',
                'action': 'skip_current_job',
                'job_url': job_url,
                'suggestion': '该职位可能已过期、已下架，或不在招聘状态'
            }
        )

    async def _detect_state_by_selectors(self, page) -> PageState:
        """
        使用常见选择器检测页面状态

        Args:
            page: Playwright page 对象

        Returns:
            PageState: 检测到的状态
        """
        try:
            # 检查登录表单
            for selector in LOGIN_SELECTORS['username']:
                if await page.locator(selector).first.is_visible(timeout=500):
                    return PageState.LOGIN

            # 检查弹窗
            for selector in CLOSE_SELECTORS:
                if await page.locator(selector).first.is_visible(timeout=500):
                    return PageState.POPUP

        except Exception as e:
            logger.debug(f"选择器检测失败: {e}")

        return PageState.UNKNOWN

    async def retry_with_backoff(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        使用指数退避重试函数

        Args:
            func: 要重试的异步函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果

        Raises:
            最后一次执行的异常
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.debug(f"重试成功 (尝试 {attempt + 1}/{self.max_retries})")
                return result

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"尝试 {attempt + 1}/{self.max_retries} 失败: {e}"
                )

                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt] if attempt < len(self.retry_delays) else self.retry_delays[-1]
                    logger.debug(f"等待 {delay} 秒后重试...")
                    await asyncio.sleep(delay)

        # 所有尝试都失败
        logger.error(f"重试次数耗尽，最后异常: {last_exception}")
        raise last_exception

    async def scroll_page(self, page, direction: str = 'down', amount: int = 1) -> RecoveryResult:
        """
        滚动页面

        Args:
            page: Playwright page 对象
            direction: 滚动方向 ('up' 或 'down')
            amount: 滚动次数

        Returns:
            RecoveryResult: 滚动结果
        """
        try:
            for _ in range(amount):
                if direction == 'down':
                    await page.evaluate('window.scrollBy(0, window.innerHeight)')
                else:
                    await page.evaluate('window.scrollBy(0, -window.innerHeight)')
                await asyncio.sleep(0.3)

            return RecoveryResult(
                success=True,
                action=RecoveryAction.SCROLL,
                message=f"页面已向{direction}滚动 {amount} 次",
                next_state=PageState.NORMAL,
                metadata={'direction': direction, 'amount': amount}
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                action=RecoveryAction.SCROLL,
                message=f"滚动失败: {e}",
                next_state=PageState.NORMAL,
                metadata={'error': str(e)}
            )

    async def refresh_page(self, page) -> RecoveryResult:
        """
        刷新页面

        Args:
            page: Playwright page 对象

        Returns:
            RecoveryResult: 刷新结果
        """
        try:
            await page.reload(timeout=10000)
            await asyncio.sleep(1)  # 等待页面稳定

            return RecoveryResult(
                success=True,
                action=RecoveryAction.REFRESH,
                message="页面已刷新",
                next_state=PageState.NORMAL
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                action=RecoveryAction.REFRESH,
                message=f"刷新失败: {e}",
                next_state=PageState.ERROR,
                metadata={'error': str(e)}
            )

    def get_last_error(self) -> Optional[Exception]:
        """获取最后一次错误"""
        return self._last_error

    def get_registered_handlers(self) -> List[PageState]:
        """获取已注册的处理状态列表"""
        return list(self.recovery_handlers.keys())

    async def execute_recovery_chain(
        self,
        initial_state: PageState,
        context: Dict,
        chain: Optional[List[PageState]] = None
    ) -> RecoveryResult:
        """
        执行恢复链

        如果一个状态恢复失败，尝试链中的下一个状态

        Args:
            initial_state: 初始状态
            context: 上下文信息
            chain: 状态链，默认为 [初始状态, UNKNOWN, ERROR]

        Returns:
            RecoveryResult: 最终恢复结果
        """
        if chain is None:
            chain = [initial_state, PageState.UNKNOWN, PageState.ERROR]

        page = context.get('page')

        for state in chain:
            logger.info(f"尝试恢复状态: {state.value}")
            result = await self.recover(state, context)

            if result.success:
                logger.info(f"状态 {state.value} 恢复成功")
                return result

            # 如果需要远程干预，立即返回
            if result.requires_remote:
                logger.warning("需要远程干预，停止恢复链")
                return result

            # 尝试刷新页面后继续
            if page:
                await self.refresh_page(page)

        # 所有链都失败
        logger.error("恢复链执行完毕，全部失败")
        return RecoveryResult(
            success=False,
            action=RecoveryAction.ABORT,
            message="恢复链执行完毕，全部状态恢复失败",
            next_state=PageState.ERROR
        )

    async def handle_apply_failure(
        self,
        page: Any,
        job_url: str,
        error_context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        处理投递失败
        当投递失败时调用，记录错误并返回失败结果

        Args:
            page: Playwright page 对象（可能为None）
            job_url: 职位URL
            error_context: 错误上下文信息

        Returns:
            RecoveryResult: 投递失败的处理结果
        """
        logger.error(f"投递失败: job_url={job_url}, error={error_context}")
        self._last_error = Exception(f"投递失败: {job_url}")

        return RecoveryResult(
            success=False,
            action=RecoveryAction.SKIP,
            message=f"投递失败: {job_url}",
            next_state=PageState.ERROR,
            metadata={
                "job_url": job_url,
                "error_context": error_context
            }
        )


# 便捷函数
async def quick_recover(page, state: PageState, **kwargs) -> RecoveryResult:
    """
    快速恢复函数

    Args:
        page: Playwright page 对象
        state: 页面状态
        **kwargs: 其他上下文信息

    Returns:
        RecoveryResult: 恢复结果
    """
    engine = RecoveryEngine()
    context = {'page': page, **kwargs}
    return await engine.recover(state, context)


# 导出
__all__ = [
    'RecoveryEngine',
    'RecoveryResult',
    'RecoveryAction',
    'PageState',
    'CLOSE_SELECTORS',
    'LOGIN_SELECTORS',
    'quick_recover',
]
