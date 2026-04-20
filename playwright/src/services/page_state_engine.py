"""
V3.3 Page State Engine
页面状态引擎 - 使用 DOM + Vision 联合识别页面状态

Architecture:
    PAGE STATE ENGINE → VISION LAYER → EMBEDDING DECISION LAYER → ACTION EXECUTION
                             ↓
                       RECOVERY ENGINE
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import re


class PageType(Enum):
    """页面类型枚举"""
    LOGIN = "login"                    # 登录页面
    JOB_LIST = "job_list"             # 职位列表页
    JOB_DETAIL = "job_detail"         # 职位详情页
    JOB_APPLY_FORM = "job_apply_form" # 投递表单页
    POPUP = "popup"                   # 弹窗
    CAPTCHA = "captcha"               # 验证码页
    RECRUITER_PAGE = "recruiter_page" # 招聘者页面（HR/雇主）- 不是求职者视角
    UNKNOWN = "unknown"               # 未知


@dataclass
class PageStateResult:
    """页面状态识别结果"""
    page_type: str
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    requires_action: bool = False
    recommended_action: Optional[str] = None


# DOM 检测选择器配置
class DetectionSelectors:
    """页面检测选择器配置"""

    # Login detection selectors - 登录页面检测
    LOGIN_SELECTORS = [
        'input[type="password"]',      # 密码输入框
        'form[class*="login" i]',       # 登录表单
        'form[class*="signin" i]',      # 登录表单变体
        'form[id*="login" i]',          # 登录表单变体
        'button:has-text("登录")',       # 登录按钮
        'button:has-text("登录" i)',     # 登录按钮(不区分大小写)
        'a:has-text("登录")',            # 登录链接
        '[class*="login" i] input',     # 登录区域内的输入框
        '[class*="signin" i]',          # 登录区域
        'input[placeholder*="账号" i]',  # 账号输入框
        'input[placeholder*="密码" i]',  # 密码输入框
    ]

    # Job list detection selectors - 职位列表页检测
    JOB_LIST_SELECTORS = [
        '[class*="job-list" i]',              # 职位列表容器
        '[class*="jobList" i]',               # 职位列表容器(驼峰)
        '[class*="position-list" i]',         # 职位列表容器变体
        '[class*="job-item" i]',               # 职位项
        '[class*="jobItem" i]',                # 职位项(驼峰)
        '.job-item',                           # 职位项class
        '[class*="position" i] a[href*="job"]', # 职位链接
        '[class*="recruit" i] [class*="job"]', # 招聘下的职位
        'a[href*="/job/"]',                    # 职位链接
        '[class*="search-result" i]',          # 搜索结果
        '[class*="result-list" i]',           # 结果列表
    ]

    # Job detail detection selectors - 职位详情页检测
    JOB_DETAIL_SELECTORS = [
        '[class*="job-detail" i]',            # 职位详情容器
        '[class*="jobDetail" i]',              # 职位详情容器(驼峰)
        '[class*="job-description" i]',       # 职位描述
        '[class*="job-desc" i]',              # 职位描述简写
        '[class*="position-detail" i]',        # 职位详情变体
        '[class*="job-info" i]',               # 职位信息
        'button:has-text("投递")',              # 投递按钮
        'button:has-text("申请" i)',            # 申请按钮
        'button:has-text("立即申请" i)',         # 立即申请按钮
        '[class*="apply" i] button',          # 申请区域的按钮
        'a:has-text("投递简历")',               # 投递简历链接
        'a:has-text("申请职位" i)',             # 申请职位链接
    ]

    # Job apply form detection selectors - 投递表单页检测
    JOB_APPLY_FORM_SELECTORS = [
        'form[class*="apply" i]',              # 申请表单
        'form[class*="resume" i]',            # 简历表单
        '[class*="apply-form" i]',             # 申请表单容器
        '[class*="send-resume" i]',            # 发送简历容器
        'input[name*="resume" i]',             # 简历输入框
        'input[type="file"]',                  # 文件上传
        'textarea[name*="reason" i]',          # 原因输入框
        'button:has-text("确认投递" i)',         # 确认投递按钮
        'button:has-text("提交" i)',            # 提交按钮
    ]

    # Popup detection selectors - 弹窗检测
    POPUP_SELECTORS = [
        '.modal',                              # Bootstrap modal
        '.popup',                              # 通用popup
        '.layui-layer',                        # Layui弹层
        '[class*="dialog" i]',                 # 对话框
        '[class*="modal" i]',                  # 模态框
        '[class*="popup" i]',                  # 弹窗
        '[role="dialog"]',                     # ARIA对话框
        '[aria-modal="true"]',                 # ARIA模态
        '.el-dialog',                          # Element UI对话框
        '.ant-modal',                          # Ant Design对话框
        '[class*="layer" i][class*="layer-" i]', # layer弹层
        '.mask',                               # 遮罩层
        '[class*="overlay" i]',                 # 遮罩层变体
    ]

    # Captcha detection selectors - 验证码页检测
    CAPTCHA_SELECTORS = [
        '[class*="captcha" i]',               # 验证码容器
        '[class*="verify" i]',                # 验证容器
        '[class*="verification" i]',          # 验证容器变体
        'img[src*="captcha" i]',              # 验证码图片
        'img[src*="verify" i]',               # 验证码图片变体
        'canvas',                              # Canvas验证码
        '[class*="slider" i][class*="captcha" i]', # 滑块验证码
        '[class*="geetest" i]',                # 极验验证码
        '[class*="ws" i][class*="verify" i]',  # WS验证
    ]

    # Recruiter page detection selectors - 招聘者页面检测
    # 这是HR/雇主视角页面，不是求职者视角，应该跳过
    RECRUITER_PAGE_SELECTORS = [
        'button:has-text("我要招人")',          # 招聘者入口按钮
        'button:has-text("发布职位")',         # 发布职位按钮
        'button:has-text("人才搜索")',         # 人才搜索按钮
        'button:has-text("简历管理")',         # 简历管理按钮
        'button:has-text("职位管理")',         # 职位管理按钮
        '[class*="recruiter" i]',             # 招聘者相关class
        '[class*="employer" i]',              # 雇主相关class
        '[class*="hr-panel" i]',              # HR面板
        '[class*="company-dashboard" i]',      # 企业控制台
        '[href*="recruiter" i]',              # 招聘者链接
        '[href*="employer" i]',               # 雇主链接
        '[href*="company" i][href*="manage"]', # 企业管理链接
        # 智联特定
        '[class*="zhaopin" i][class*="vip" i]',  # 智联VIP
        '[class*="brand" i][class*="center" i]',  # 品牌中心
    ]

    # 招聘者页面负面选择器 - 这些选择器存在说明不是招聘者页面
    RECRUITER_PAGE_ABSENCE_SELECTORS = [
        'button:has-text("投递")',              # 投递按钮（求职者视角）
        'button:has-text("申请职位")',          # 申请职位（求职者视角）
        'button:has-text("立即申请")',          # 立即申请（求职者视角）
    ]


class PageStateEngine:
    """
    V3.3 Page State Engine
    页面状态引擎 - 使用 DOM + Vision 联合识别页面状态

    主要功能:
        - 检测当前页面类型(login/job_list/job_detail/popup等)
        - DOM-based 检测(快速,无API调用)
        - Vision-based 检测(作为DOM的备选方案)
        - 提供识别置信度和证据

    Architecture Flow:
        PAGE STATE ENGINE → VISION LAYER → EMBEDDING DECISION LAYER → ACTION EXECUTION
    """

    # 置信度阈值
    HIGH_CONFIDENCE_THRESHOLD = 0.8   # 高置信度阈值
    LOW_CONFIDENCE_THRESHOLD = 0.4    # 低置信度阈值
    VISION_FALLBACK_THRESHOLD = 0.5   # 使用Vision的阈值

    def __init__(self, vision_service=None, embedding_service=None):
        """
        初始化页面状态引擎

        Args:
            vision_service: Vision服务实例,用于视觉识别
            embedding_service: Embedding服务实例,用于向量检索
        """
        self.vision_service = vision_service
        self.embedding_service = embedding_service
        self.selectors = DetectionSelectors()

    async def detect_page_state(self, page) -> PageStateResult:
        """
        检测当前页面状态 - 主入口方法

        检测策略:
            1. 首先尝试基于DOM的检测(快速,无API调用)
            2. 如果DOM检测置信度低,则回退到基于Vision的检测
            3. 综合结果,返回PageStateResult

        Args:
            page: Playwright Page对象

        Returns:
            PageStateResult: 包含页面类型、置信度、证据和推荐动作
        """
        try:
            # 步骤1: DOM检测
            dom_page_type, dom_confidence = await self.detect_by_dom(page)

            # 步骤2: 如果DOM检测置信度低,使用Vision检测
            if dom_confidence < self.VISION_FALLBACK_THRESHOLD:
                vision_page_type, vision_confidence = await self.detect_by_vision(page)

                # 合并结果
                if vision_confidence > dom_confidence:
                    return PageStateResult(
                        page_type=vision_page_type,
                        confidence=vision_confidence,
                        evidence={
                            'dom_type': dom_page_type,
                            'dom_confidence': dom_confidence,
                            'vision_type': vision_page_type,
                            'vision_confidence': vision_confidence,
                            'method': 'vision_fallback'
                        },
                        requires_action=True,
                        recommended_action=self._get_recommended_action(vision_page_type)
                    )

            # 步骤3: 返回DOM检测结果
            requires_action = dom_confidence < self.HIGH_CONFIDENCE_THRESHOLD
            return PageStateResult(
                page_type=dom_page_type,
                confidence=dom_confidence,
                evidence={
                    'dom_type': dom_page_type,
                    'dom_confidence': dom_confidence,
                    'method': 'dom_primary'
                },
                requires_action=requires_action,
                recommended_action=self._get_recommended_action(dom_page_type) if requires_action else None
            )

        except Exception as e:
            return PageStateResult(
                page_type=PageType.UNKNOWN.value,
                confidence=0.0,
                evidence={'error': str(e)},
                requires_action=True,
                recommended_action='error_recovery'
            )

    async def detect_by_dom(self, page) -> Tuple[str, float]:
        """
        通过 DOM 检测页面状态

        检测方法:
            1. URL模式匹配
            2. DOM选择器匹配
            3. 综合评分

        Args:
            page: Playwright Page对象

        Returns:
            Tuple[str, float]: (页面类型, 置信度)
        """
        try:
            # 获取URL
            url = page.url if hasattr(page, 'url') else ''

            # 各类型检测结果
            scores = {
                PageType.LOGIN.value: 0.0,
                PageType.JOB_LIST.value: 0.0,
                PageType.JOB_DETAIL.value: 0.0,
                PageType.JOB_APPLY_FORM.value: 0.0,
                PageType.POPUP.value: 0.0,
                PageType.CAPTCHA.value: 0.0,
                PageType.RECRUITER_PAGE.value: 0.0,
            }

            # 1. URL模式检测
            url_scores = self._detect_by_url(url)
            for page_type, score in url_scores.items():
                scores[page_type] += score * 0.3  # URL权重30%

            # 2. DOM选择器检测
            # 检测登录
            login_score = await self._check_selectors(page, self.selectors.LOGIN_SELECTORS)
            scores[PageType.LOGIN.value] += login_score * 0.7

            # 检测弹窗
            popup_score = await self._check_selectors(page, self.selectors.POPUP_SELECTORS)
            scores[PageType.POPUP.value] += popup_score * 0.7

            # 检测验证码
            captcha_score = await self._check_selectors(page, self.selectors.CAPTCHA_SELECTORS)
            scores[PageType.CAPTCHA.value] += captcha_score * 0.7

            # 只有在没有检测到弹窗或验证码时,才检测职位相关页面
            # 但优先检测招聘者页面（这个要最先排除）
            if popup_score < 0.3 and captcha_score < 0.3:
                # 检测招聘者页面（HR/雇主视角）- 最高优先级排除
                recruiter_score = await self._check_selectors(page, self.selectors.RECRUITER_PAGE_SELECTORS)
                # 如果同时有求职者按钮存在，降低招聘者页面置信度
                seeker_buttons = await self._check_selectors(page, self.selectors.RECRUITER_PAGE_ABSENCE_SELECTORS)
                if seeker_buttons > 0.3:
                    recruiter_score = recruiter_score * 0.3  # 降低置信度
                scores[PageType.RECRUITER_PAGE.value] += recruiter_score * 0.8

                # 检测职位列表
            if popup_score < 0.3 and captcha_score < 0.3:
                # 检测职位列表
                job_list_score = await self._check_selectors(page, self.selectors.JOB_LIST_SELECTORS)
                scores[PageType.JOB_LIST.value] += job_list_score * 0.7

                # 检测职位详情
                job_detail_score = await self._check_selectors(page, self.selectors.JOB_DETAIL_SELECTORS)
                scores[PageType.JOB_DETAIL.value] += job_detail_score * 0.7

                # 检测投递表单
                apply_form_score = await self._check_selectors(page, self.selectors.JOB_APPLY_FORM_SELECTORS)
                scores[PageType.JOB_APPLY_FORM.value] += apply_form_score * 0.7

            # 找出最高分的页面类型
            best_type = max(scores, key=scores.get)
            best_score = scores[best_type]

            # 如果最高分低于阈值,返回UNKNOWN
            if best_score < self.LOW_CONFIDENCE_THRESHOLD:
                return PageType.UNKNOWN.value, best_score

            return best_type, min(best_score, 1.0)

        except Exception as e:
            return PageType.UNKNOWN.value, 0.0

    async def detect_by_vision(self, page) -> Tuple[str, float]:
        """
        通过 Vision 检测页面状态

        当DOM检测不确定时,使用视觉识别作为备选方案

        Args:
            page: Playwright Page对象

        Returns:
            Tuple[str, float]: (页面类型, 置信度)
        """
        if not self.vision_service:
            return PageType.UNKNOWN.value, 0.0

        try:
            # 等待页面稳定后再截图，避免 "page is navigating" 错误
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except Exception:
                pass

            # 截图
            screenshot = await page.screenshot()

            # 调用Vision服务分析
            vision_result = await self.vision_service.analyze_screenshot(screenshot)

            if not vision_result:
                return PageType.UNKNOWN.value, 0.0

            # 从VisionResult获取页面类型
            page_type = vision_result.page_type if hasattr(vision_result, 'page_type') else PageType.UNKNOWN.value

            # 获取置信度
            confidence = 0.5
            if hasattr(vision_result, 'raw_response') and isinstance(vision_result.raw_response, dict):
                confidence = vision_result.raw_response.get('confidence', 0.5)

            # 转换为标准页面类型
            mapped_type = self._map_vision_page_type(page_type)

            return mapped_type, confidence

        except Exception as e:
            return PageType.UNKNOWN.value, 0.0

    async def detect_login_state(self, page) -> bool:
        """
        检测是否是登录状态

        Args:
            page: Playwright Page对象

        Returns:
            bool: True表示在登录页,需要登录
        """
        try:
            page_type, confidence = await self.detect_by_dom(page)
            return page_type == PageType.LOGIN.value and confidence > self.LOW_CONFIDENCE_THRESHOLD
        except:
            return False

    async def detect_popup_state(self, page) -> bool:
        """
        检测是否有弹窗

        Args:
            page: Playwright Page对象

        Returns:
            bool: True表示存在弹窗
        """
        try:
            page_type, confidence = await self.detect_by_dom(page)
            return page_type == PageType.POPUP.value and confidence > self.LOW_CONFIDENCE_THRESHOLD
        except:
            return False

    async def is_on_job_list(self, page) -> bool:
        """
        检测是否在职位列表页

        Args:
            page: Playwright Page对象

        Returns:
            bool: True表示在职位列表页
        """
        try:
            page_type, confidence = await self.detect_by_dom(page)
            return page_type == PageType.JOB_LIST.value and confidence > self.LOW_CONFIDENCE_THRESHOLD
        except:
            return False

    async def is_on_job_detail(self, page) -> bool:
        """
        检测是否在职位详情页

        Args:
            page: Playwright Page对象

        Returns:
            bool: True表示在职位详情页
        """
        try:
            page_type, confidence = await self.detect_by_dom(page)
            return page_type == PageType.JOB_DETAIL.value and confidence > self.LOW_CONFIDENCE_THRESHOLD
        except:
            return False

    async def is_on_apply_form(self, page) -> bool:
        """
        检测是否在投递表单页

        Args:
            page: Playwright Page对象

        Returns:
            bool: True表示在投递表单页
        """
        try:
            page_type, confidence = await self.detect_by_dom(page)
            return page_type == PageType.JOB_APPLY_FORM.value and confidence > self.LOW_CONFIDENCE_THRESHOLD
        except:
            return False

    async def is_captcha_page(self, page) -> bool:
        """
        检测是否是验证码页

        Args:
            page: Playwright Page对象

        Returns:
            bool: True表示在验证码页
        """
        try:
            page_type, confidence = await self.detect_by_dom(page)
            return page_type == PageType.CAPTCHA.value and confidence > self.LOW_CONFIDENCE_THRESHOLD
        except:
            return False

    async def is_recruiter_page(self, page) -> bool:
        """
        检测是否是招聘者页面（HR/雇主视角）

        招聘者页面不是求职者视角，应该跳过

        Args:
            page: Playwright Page对象

        Returns:
            bool: True表示在招聘者页面
        """
        try:
            page_type, confidence = await self.detect_by_dom(page)
            return page_type == PageType.RECRUITER_PAGE.value and confidence > self.LOW_CONFIDENCE_THRESHOLD
        except:
            return False

    async def _check_selectors(self, page, selectors: List[str]) -> float:
        """
        检查选择器匹配情况,返回置信度

        Args:
            page: Playwright Page对象
            selectors: 选择器列表

        Returns:
            float: 0.0-1.0的置信度
        """
        try:
            if not selectors:
                return 0.0

            matched_count = 0
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        matched_count += 1
                except:
                    continue

            return matched_count / len(selectors) if selectors else 0.0

        except Exception as e:
            return 0.0

    def _detect_by_url(self, url: str) -> Dict[str, float]:
        """
        通过URL模式检测页面类型

        Args:
            url: 页面URL

        Returns:
            Dict[str, float]: 各页面类型的置信度
        """
        scores = {
            PageType.LOGIN.value: 0.0,
            PageType.JOB_LIST.value: 0.0,
            PageType.JOB_DETAIL.value: 0.0,
            PageType.JOB_APPLY_FORM.value: 0.0,
        }

        if not url:
            return scores

        url_lower = url.lower()

        # Login URL patterns
        login_patterns = [
            r'login',
            r'signin',
            r'sign-in',
            r'auth',
            r'/account/login',
            r'/user/login',
            r'/passport/login',
        ]
        for pattern in login_patterns:
            if re.search(pattern, url_lower):
                scores[PageType.LOGIN.value] = 1.0
                break

        # Job list URL patterns
        job_list_patterns = [
            r'job_list',
            r'job-list',
            r'jobs',
            r'/job/',
            r'/position/list',
            r'/search',
            r'recruit',
            r'jobfair',
            r'campus',
        ]
        for pattern in job_list_patterns:
            if re.search(pattern, url_lower):
                scores[PageType.JOB_LIST.value] = 1.0
                break

        # Job detail URL patterns
        job_detail_patterns = [
            r'/job/\d+',
            r'/position/\d+',
            r'/job-detail',
            r'/jobDetail',
            r'job-detail',
            r'jobinfo',
        ]
        for pattern in job_detail_patterns:
            if re.search(pattern, url_lower):
                scores[PageType.JOB_DETAIL.value] = 1.0
                break

        # Apply form URL patterns
        apply_form_patterns = [
            r'apply',
            r'/resume/send',
            r'/job/apply',
            r'confirm',
        ]
        for pattern in apply_form_patterns:
            if re.search(pattern, url_lower):
                scores[PageType.JOB_APPLY_FORM.value] = 1.0
                break

        return scores

    def _map_vision_page_type(self, vision_page_type: str) -> str:
        """
        将Vision返回的页面类型映射到标准PageType

        Args:
            vision_page_type: Vision服务返回的页面类型

        Returns:
            str: 标准化的页面类型
        """
        # 映射表
        mapping = {
            'login': PageType.LOGIN.value,
            'signin': PageType.LOGIN.value,
            'job_list': PageType.JOB_LIST.value,
            'joblist': PageType.JOB_LIST.value,
            'job-list': PageType.JOB_LIST.value,
            'jobs': PageType.JOB_LIST.value,
            'job_detail': PageType.JOB_DETAIL.value,
            'jobdetail': PageType.JOB_DETAIL.value,
            'job-detail': PageType.JOB_DETAIL.value,
            'job_detail': PageType.JOB_DETAIL.value,
            'apply_form': PageType.JOB_APPLY_FORM.value,
            'applyform': PageType.JOB_APPLY_FORM.value,
            'apply': PageType.JOB_APPLY_FORM.value,
            'popup': PageType.POPUP.value,
            'modal': PageType.POPUP.value,
            'dialog': PageType.POPUP.value,
            'captcha': PageType.CAPTCHA.value,
            'verify': PageType.CAPTCHA.value,
            'verification': PageType.CAPTCHA.value,
        }

        return mapping.get(vision_page_type.lower(), PageType.UNKNOWN.value)

    def _get_recommended_action(self, page_type: str) -> Optional[str]:
        """
        根据页面类型获取推荐动作

        Args:
            page_type: 页面类型

        Returns:
            Optional[str]: 推荐的动作
        """
        action_map = {
            PageType.LOGIN.value: 'login',
            PageType.JOB_LIST.value: 'scroll_or_click',
            PageType.JOB_DETAIL.value: 'click_apply',
            PageType.JOB_APPLY_FORM.value: 'fill_and_submit',
            PageType.POPUP.value: 'close_popup',
            PageType.CAPTCHA.value: 'handle_captcha',
            PageType.RECRUITER_PAGE.value: 'skip',  # 招聘者页面直接跳过
        }

        return action_map.get(page_type)

    async def batch_detect_states(self, pages: List) -> List[PageStateResult]:
        """
        批量检测多个页面状态

        Args:
            pages: Playwright Page对象列表

        Returns:
            List[PageStateResult]: 各页面的状态检测结果
        """
        tasks = [self.detect_page_state(page) for page in pages]
        return await asyncio.gather(*tasks)

    def get_page_type_confidence(self, result: PageStateResult, page_type: str) -> float:
        """
        获取特定页面类型的置信度

        Args:
            result: PageStateResult实例
            page_type: 页面类型

        Returns:
            float: 置信度值
        """
        if result.page_type == page_type:
            return result.confidence
        return 0.0


# 便捷函数
async def detect_current_page_state(page, vision_service=None, embedding_service=None) -> PageStateResult:
    """
    便捷函数:检测当前页面状态

    Args:
        page: Playwright Page对象
        vision_service: Vision服务实例(可选)
        embedding_service: Embedding服务实例(可选)

    Returns:
        PageStateResult: 页面状态检测结果
    """
    engine = PageStateEngine(vision_service=vision_service, embedding_service=embedding_service)
    return await engine.detect_page_state(page)
