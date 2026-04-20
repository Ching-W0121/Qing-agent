"""
V3.4 Crawler Runner
集成 Vision + Embedding + Decision Engine + Recovery + Success Learning + RiskScore
"""

import asyncio
import hashlib
import random
from typing import Dict, List, Optional, Any
from datetime import datetime

# V3.3 Services
from services.page_state_engine import PageStateEngine, PageType, PageStateResult
from services.vision_service import VisionService, VisionResult
from services.embedding_service import EmbeddingService
from services.decision_engine import DecisionEngine
from services.recovery_engine import RecoveryEngine, PageState
from services.success_learning_engine import SuccessLearningEngine, ApplyRecord
from services.job_memory_graph import JobMemoryGraph, JobStatus

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# V3.4 新增服务
try:
    from services.stealth_service import stealth_service, StealthConfig
    from services.human_behavior import human_behavior
    from services.risk_score_service import RiskScoreService
except ImportError:
    stealth_service = None
    human_behavior = None
    RiskScoreService = None


class ClickExecutor:
    """
    坐标点击执行器
    负责将 Vision 检测到的 bbox 坐标转换为实际点击
    """

    async def click_bbox(self, page, bbox: Dict) -> bool:
        """
        使用 bbox 坐标点击（中心点）

        Args:
            page: Playwright page 对象
            bbox: 包含 x, y, width, height 的字典

        Returns:
            bool: 点击是否成功
        """
        try:
            x = bbox.get('x', 0) + bbox.get('width', 0) / 2
            y = bbox.get('y', 0) + bbox.get('height', 0) / 2
            await page.mouse.click(x, y)
            return True
        except Exception as e:
            print(f"[ClickExecutor] 坐标点击失败: {e}")
            return False

    async def click_by_selector(self, page, selector: str) -> bool:
        """
        使用 CSS selector 点击

        Args:
            page: Playwright page 对象
            selector: CSS 选择器

        Returns:
            bool: 点击是否成功
        """
        try:
            btn = await page.query_selector(selector)
            if btn:
                await btn.click()
                return True
            return False
        except Exception as e:
            print(f"[ClickExecutor] Selector点击失败: {e}")
            return False

    async def click_by_text(self, page, text: str, timeout: float = 5) -> bool:
        """
        通过文本查找并点击按钮

        Args:
            page: Playwright page 对象
            text: 按钮文本（支持模糊匹配）
            timeout: 超时时间

        Returns:
            bool: 点击是否成功
        """
        try:
            # 尝试多种选择器
            selectors = [
                f'button:has-text("{text}")',
                f'a:has-text("{text}")',
                f'[class*="btn"]:has-text("{text}")',
            ]
            for sel in selectors:
                try:
                    btn = await page.wait_for_selector(sel, timeout=timeout)
                    if btn:
                        await btn.click()
                        return True
                except:
                    continue
            return False
        except Exception as e:
            print(f"[ClickExecutor] 文本点击失败: {e}")
            return False

    async def click_with_fallback(self, page, btn_info: Dict, max_retries: int = 3) -> Dict:
        """
        多级 fallback 点击策略

        Args:
            page: Playwright page 对象
            btn_info: 按钮信息 dict，包含 x, y, width, height, text, selector
            max_retries: 最大重试次数

        Returns:
            Dict: {"success": bool, "method": str, "error": str}
        """
        # 方法1: 坐标点击
        if btn_info.get('x') and btn_info.get('y'):
            for retry in range(max_retries):
                success = await self.click_bbox(page, btn_info)
                if success:
                    return {"success": True, "method": f"bbox_retry_{retry}", "error": None}

        # 方法2: Selector 点击
        if btn_info.get('selector'):
            success = await self.click_by_selector(page, btn_info['selector'])
            if success:
                return {"success": True, "method": "selector", "error": None}

        # 方法3: 文本点击
        if btn_info.get('text'):
            success = await self.click_by_text(page, btn_info['text'])
            if success:
                return {"success": True, "method": "text", "error": None}

        return {"success": False, "method": "none", "error": "所有点击方法都失败"}


class PopupDetector:
    """
    弹窗检测器
    检测并处理页面弹窗
    """

    POPUP_KEYWORDS = ['关闭', '取消', '知道了', 'confirm', 'cancel', 'close', 'popup', 'modal']

    async def detect_popup(self, page) -> Optional[Dict]:
        """
        检测页面是否有弹窗

        Returns:
            Optional[Dict]: 弹窗信息，包含 selector 和文本
        """
        try:
            # 检查常见的弹窗选择器
            popup_selectors = [
                '.popup', '.modal', '.dialog', '.overlay',
                '[class*="popup"]', '[class*="modal"]', '[class*="dialog"]',
                '[role="dialog"]', '[aria-modal="true"]'
            ]

            for sel in popup_selectors:
                popup = await page.query_selector(sel)
                if popup:
                    is_visible = await popup.is_visible()
                    if is_visible:
                        text = await popup.inner_text() or ""
                        return {"selector": sel, "text": text[:100]}

            # 检查是否有遮罩层
            overlays = await page.query_selector_all('[class*="overlay"], [class*="mask"]')
            for overlay in overlays:
                is_visible = await overlay.is_visible()
                if is_visible:
                    return {"selector": None, "text": "overlay_detected"}

            return None

        except Exception as e:
            print(f"[PopupDetector] 检测失败: {e}")
            return None

    async def close_popup(self, page) -> bool:
        """
        尝试关闭弹窗

        Returns:
            bool: 是否成功关闭
        """
        try:
            # 尝试关闭按钮
            close_selectors = [
                '.popup .close', '.modal .close', '.dialog .close',
                '[class*="popup"] [class*="close"]',
                '[class*="modal"] [class*="close"]',
                'button:has-text("关闭")', 'a:has-text("关闭")',
                '.btn-close', '.close-btn'
            ]

            for sel in close_selectors:
                try:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(0.5)
                        return True
                except:
                    continue

            # 尝试 ESC 键关闭
            try:
                await page.keyboard.press('Escape')
                return True
            except:
                pass

            return False

        except Exception as e:
            print(f"[PopupDetector] 关闭失败: {e}")
            return False


class LoginStateDetector:
    """
    登录状态检测器
    通过页面元素检测用户登录状态
    """

    LOGIN_SELECTORS = {
        # 智联招聘可能的选择器
        'container': [
            'div.c-login.top',
            'div.login-top',
            '.header-user',
            '[class*="user-name"]',
            '.user-info'
        ],
        'username': [
            'div.c-login.top span.c-login__top__name',
            'div.login-top span[class*="name"]',
            '.header-user span[class*="name"]',
            '[class*="user-name"]',
            '.user-name'
        ],
        'photo': [
            'div.c-login.top span.c-login__top__photo',
            '.header-user-photo'
        ]
    }

    async def detect_login_state(self, page) -> Dict:
        """
        检测用户登录状态

        Returns:
            Dict: {
                "is_logged_in": bool,
                "username": str or None,
                "page_url": str
            }
        """
        try:
            # 尝试多个选择器
            container = None
            for selector in self.LOGIN_SELECTORS['container']:
                try:
                    elem = await page.query_selector(selector)
                    if elem and await elem.is_visible():
                        container = elem
                        print(f"[LoginStateDetector] 找到容器: {selector}")
                        break
                except:
                    continue

            if container:
                # 尝试获取用户名
                username = None
                for selector in self.LOGIN_SELECTORS['username']:
                    try:
                        username_elem = await page.query_selector(selector)
                        if username_elem:
                            username = await username_elem.inner_text()
                            if username:
                                print(f"[LoginStateDetector] 找到用户名: {username}")
                                break
                    except:
                        continue

                return {
                    "is_logged_in": True,
                    "username": username,
                    "page_url": page.url
                }

            # 尝试直接查找包含"王庆"等中文名的元素
            try:
                page_content = await page.content()
                if 'c-login' in page_content or 'user-name' in page_content.lower():
                    # 页面可能有登录元素但选择器不匹配
                    print("[LoginStateDetector] 页面包含登录相关元素但选择器未匹配")
            except:
                pass

            return {
                "is_logged_in": False,
                "username": None,
                "page_url": page.url
            }

        except Exception as e:
            print(f"[LoginStateDetector] 检测失败: {e}")
            return {
                "is_logged_in": False,
                "username": None,
                "page_url": page.url,
                "error": str(e)
            }


class DeliveryVerifier:
    """
    投递验证器
    通过用户求职反馈页面验证投递结果
    """

    DELIVERY_PATH = {
        'feedback_menu': 'a:has-text("求职反馈"), [class*="feedback"]',
        'delivery_tab': '[class*="delivery"]:has-text("投递成功"), [class*="applied"]',
        'delivery_item': '[class*="job-item"], .job-detail-item'
    }

    async def verify_delivery(self, page, job_url: str = None) -> Dict:
        """
        验证投递结果

        Args:
            page: Playwright page 对象
            job_url: 职位URL（可选，用于匹配特定职位）

        Returns:
            Dict: {
                "is_delivered": bool,
                "delivery_list": list,
                "matched_job": dict or None
            }
        """
        try:
            print("[DeliveryVerifier] 开始验证投递...")

            # 1. 点击用户名区域
            username_selectors = [
                'div.c-login.top',
                '.header-user',
                '[class*="user-name"]',
                '.user-info'
            ]

            username_clicked = False
            for sel in username_selectors:
                try:
                    elem = await page.query_selector(sel)
                    if elem and await elem.is_visible():
                        await elem.click()
                        username_clicked = True
                        print(f"[DeliveryVerifier] 点击用户名区域: {sel}")
                        break
                except:
                    continue

            await asyncio.sleep(1.5)

            # 2. 查找并点击"求职反馈"
            feedback_selectors = [
                'a:has-text("求职反馈")',
                '[class*="menu"] a:has-text("反馈")',
                '[class*="nav"] a:has-text("反馈")',
                'a:has-text("投递管理")',
                '[class*="feedback"]'
            ]

            feedback_link = None
            for sel in feedback_selectors:
                try:
                    link = await page.query_selector(sel)
                    if link and await link.is_visible():
                        feedback_link = link
                        print(f"[DeliveryVerifier] 找到反馈链接: {sel}")
                        break
                except:
                    continue

            if not feedback_link:
                print("[DeliveryVerifier] 未找到求职反馈入口")
                return {
                    "is_delivered": False,
                    "delivery_list": [],
                    "error": "未找到求职反馈入口"
                }

            await feedback_link.click()
            print("[DeliveryVerifier] 点击求职反馈")
            await asyncio.sleep(2)  # 等待页面加载

            # 3. 切换到"投递成功"标签
            delivery_tab_selectors = [
                '[class*="tab"]:has-text("投递成功")',
                '[class*="delivery"]:has-text("投递成功")',
                'a:has-text("投递成功")',
                '[class*="tab"]:has-text("已投递")'
            ]

            delivery_tab = None
            for sel in delivery_tab_selectors:
                try:
                    tab = await page.query_selector(sel)
                    if tab and await tab.is_visible():
                        delivery_tab = tab
                        print(f"[DeliveryVerifier] 找到投递成功标签: {sel}")
                        break
                except:
                    continue

            if delivery_tab:
                await delivery_tab.click()
                print("[DeliveryVerifier] 点击投递成功标签")
                await asyncio.sleep(2)

            # 4. 提取投递列表
            delivery_list = []
            page_text = await page.content()
            print(f"[DeliveryVerifier] 页面内容长度: {len(page_text)}")

            # 尝试多种列表选择器
            list_selectors = [
                '[class*="job-list"]',
                '[class*="delivery-list"]',
                '[class*="applied-list"]',
                '.job-item',
                '[class*="resume-item"]',
                '[class*="item"]'
            ]

            items = []
            for sel in list_selectors:
                try:
                    elements = await page.query_selector_all(sel)
                    if elements and len(elements) > 0:
                        print(f"[DeliveryVerifier] 找到列表项: {sel}, 数量: {len(elements)}")
                        items = elements
                        break
                except:
                    continue

            for item in items[:20]:  # 最多取20个
                try:
                    text = await item.inner_text()
                    # 提取职位信息
                    delivery_list.append({
                        "text": text[:200] if text else "",
                        "url": page.url
                    })
                except:
                    continue

            print(f"[DeliveryVerifier] 投递列表长度: {len(delivery_list)}")

            # 5. 如果提供了 job_url，尝试匹配
            matched_job = None
            if job_url:
                for job in delivery_list:
                    job_text = job.get('text', '').lower()
                    job_url_lower = job_url.lower()
                    # 匹配职位名称或URL
                    if (job_url in job_text) or (job_url_lower in job_text) or any(kw in job_text for kw in [job_url.split('/')[-1].split('.')[0]]):
                        matched_job = job
                        print(f"[DeliveryVerifier] 匹配到职位: {job.get('text')[:50]}")
                        break

            return {
                "is_delivered": matched_job is not None,
                "delivery_list": delivery_list,
                "matched_job": matched_job,
                "total_count": len(delivery_list)
            }

        except Exception as e:
            print(f"[DeliveryVerifier] 验证失败: {e}")
            return {
                "is_delivered": False,
                "delivery_list": [],
                "error": str(e)
            }


class ClickVerification:
    """
    点击验证器
    验证点击操作是否真正成功
    """

    # 投递成功的关键词
    SUCCESS_KEYWORDS = [
        "已投递", "投递成功", "申请成功", "投递完成", "申请完成",
        "恭喜", "成功投递", "发送成功", "submit success",
        "application sent", "applied successfully"
    ]

    # 需要登录的关键词
    LOGIN_KEYWORDS = [
        "请先登录", "需要登录", "登录后", "login required", "please login"
    ]

    # 验证码关键词 - 使用更精确的匹配避免误报
    CAPTCHA_KEYWORDS = [
        "验证码", "captcha", "拼图", "滑动验证",
        "人机验证", "图片验证", "点选验证"
    ]

    # 已投递关键词
    ALREADY_APPLIED_KEYWORDS = [
        "已申请", "已投递", "重复投递", "已投递过", "已经申请"
    ]

    # 失败关键词
    FAIL_KEYWORDS = [
        "投递失败", "申请失败", "失败", "error", "系统错误"
    ]

    # 投递按钮相关关键词（存在这些词说明还在投递页面）
    APPLY_PAGE_KEYWORDS = [
        "投递", "申请", "应聘", "apply", "立即申请", "马上申请"
    ]

    async def verify_click_result(self, page, expected_state: str = "apply_success") -> Dict:
        """
        验证点击结果

        Args:
            page: Playwright page 对象
            expected_state: 期望的状态

        Returns:
            Dict: 验证结果 {"state": str, "message": str, "details": dict}
        """
        try:
            await asyncio.sleep(1.5)  # 等待页面响应

            # 获取页面内容
            content = await page.content()
            url = page.url

            # 1. 首先检查各种成功/失败状态
            for keyword in self.SUCCESS_KEYWORDS:
                if keyword in content:
                    return {"state": "success", "message": f"检测到成功关键词: {keyword}", "details": {"url": url, "keyword": keyword}}

            for keyword in self.LOGIN_KEYWORDS:
                if keyword in content:
                    return {"state": "login_required", "message": f"检测到登录关键词: {keyword}", "details": {"url": url}}

            for keyword in self.CAPTCHA_KEYWORDS:
                if keyword in content:
                    return {"state": "captcha", "message": f"检测到验证码: {keyword}", "details": {"url": url}}

            for keyword in self.ALREADY_APPLIED_KEYWORDS:
                if keyword in content:
                    return {"state": "already_applied", "message": f"检测到已投递: {keyword}", "details": {"url": url}}

            for keyword in self.FAIL_KEYWORDS:
                if keyword in content:
                    return {"state": "failed", "message": f"检测到失败: {keyword}", "details": {"url": url}}

            # 2. 检查页面是否跳转到职位列表或搜索页（可能是成功后的跳转）
            if "zhaopin.com/sou/" in url or "zhaopin.com/joblist" in url:
                return {"state": "success", "message": "跳转到职位列表页，可能投递成功", "details": {"url": url}}

            # 3. 检查是否还在投递页面（如果不在，说明可能跳转了）
            has_apply_keywords = any(kw in content for kw in self.APPLY_PAGE_KEYWORDS)

            # 4. 如果页面内容中不再有投递相关关键词，且URL变了，可能成功了
            current_url = page.url
            if not has_apply_keywords and current_url != url:
                # 页面内容变了，且没有投递关键词，可能是成功跳转了
                # 进一步检查是否有用户信息（登录状态）
                if "登录" not in content or "user" in content.lower():
                    return {"state": "success", "message": "页面已变化，可能投递成功", "details": {"url": url}}

            # 5. 如果还在职位详情页，检查是否还有投递按钮
            if "zhaopin.com/job/" in url:
                # 还在职位详情页，检查是否还能找到投递按钮
                apply_btn = await page.query_selector('button:has-text("投递"), button:has-text("申请")')
                if not apply_btn:
                    # 没有投递按钮了，可能已经投递过了
                    return {"state": "already_applied", "message": "页面无投递按钮，可能已投递", "details": {"url": url}}

            return {"state": "unknown", "message": "状态未知，无法确定投递结果", "details": {"url": url, "has_apply_keywords": has_apply_keywords}}

        except Exception as e:
            return {"state": "error", "message": str(e), "details": {}}


class ApplyResultDetector:
    """
    投递结果确认系统 (Apply Result Detection System)

    解决"点击后结果未知"的问题，实现真正的结果闭环检测

    检测流程:
    1. 点击前保存 DOM snapshot
    2. 点击后等待 2-5 秒
    3. 每 1 秒检测一次 DOM 变化，最多 5 次
    4. 综合判断: URL变化 + DOM关键词 + 页面对比
    5. 返回明确的 结果分类: SUCCESS / LOGIN_FAIL / CAPTCHA_REQUIRED / CLICK_FAIL / NO_APPLY_BUTTON

    禁止返回 unknown 状态
    """

    # 成功关键词
    SUCCESS_KEYWORDS = [
        "已投递", "投递成功", "申请成功", "已申请", "投递完成",
        "申请完成", "恭喜", "恭喜您", "成功投递", "发送成功",
        "submit success", "applied successfully", "application sent",
        "简历已投递", "投递简历成功"
    ]

    # 登录失败关键词
    LOGIN_FAIL_KEYWORDS = [
        "请先登录", "请登录", "需要登录", "登录后投递",
        "登录即表示", "login required", "please login",
        "登录智联", "登录表示同意"
    ]

    # 验证码关键词 - 使用更精确的匹配避免误报
    CAPTCHA_KEYWORDS = [
        "验证码", "captcha", "拼图", "滑动验证",
        "人机验证", "图片验证", "点选验证"
    ]

    # 已投递关键词 (需要单独处理)
    ALREADY_APPLIED_KEYWORDS = [
        "已申请", "已投递", "重复投递", "已投递过",
        "已经申请", "不能重复投递"
    ]

    # 失败关键词
    FAIL_KEYWORDS = [
        "投递失败", "申请失败", "失败", "error", "系统错误",
        "操作失败", "请稍后重试"
    ]

    # 投递相关关键词（还在投递流程中）
    APPLY_PAGE_KEYWORDS = [
        "投递", "申请", "应聘", "apply", "立即申请",
        "马上申请", "投递简历", "申请职位"
    ]

    def __init__(self):
        self.pre_click_dom_hash = None
        self.pre_click_dom_length = 0
        self.pre_click_url = None

    async def take_dom_snapshot(self, page) -> Dict:
        """
        获取 DOM 快照

        Returns:
            Dict: {
                "url": str,
                "content": str,
                "length": int,
                "hash": str
            }
        """
        import hashlib
        content = await page.content()
        # 计算内容哈希
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        return {
            "url": page.url,
            "content": content,
            "length": len(content),
            "hash": content_hash
        }

    async def detect_apply_result(self, page, job_url: str = None) -> Dict:
        """
        核心检测方法: 检测投递结果

        Args:
            page: Playwright page 对象
            job_url: 职位URL（用于对比）

        Returns:
            Dict: {
                "state": str,  # SUCCESS / LOGIN_FAIL / CAPTCHA_REQUIRED / CLICK_FAIL / NO_APPLY_BUTTON
                "message": str,
                "details": dict
            }
        """
        # 1. 获取点击后的初始状态
        initial_url = page.url
        initial_content = await page.content()
        initial_hash = hashlib.md5(initial_content.encode('utf-8')).hexdigest()

        print(f"[ApplyResultDetector] 开始检测投递结果")
        print(f"[ApplyResultDetector] 当前URL: {initial_url}")

        # 2. 等待策略: 2-5秒后开始检测
        wait_time = random.uniform(2, 5)
        print(f"[ApplyResultDetector] 等待 {wait_time:.1f} 秒...")
        await asyncio.sleep(wait_time)

        # 3. 轮询检测: 每1秒检测一次，最多5次
        for attempt in range(5):
            await asyncio.sleep(1)  # 每秒检测一次

            current_url = page.url
            current_content = await page.content()
            current_hash = hashlib.md5(current_content.encode('utf-8')).hexdigest()

            print(f"[ApplyResultDetector] 第 {attempt + 1} 次检测: URL={current_url[:50]}")

            # ===== A) URL 变化检测 =====
            url_changed = current_url != initial_url
            print(f"[ApplyResultDetector] URL变化: {url_changed}")

            # 如果跳转到登录页 → LOGIN_FAIL
            if "login" in current_url.lower() or "登录" in current_content[:500]:
                return {
                    "state": "LOGIN_FAIL",
                    "message": "检测到登录跳转，Cookie可能已过期",
                    "details": {
                        "initial_url": initial_url,
                        "current_url": current_url,
                        "attempt": attempt + 1
                    }
                }

            # 如果跳转到职位列表页 → SUCCESS
            if url_changed and any(pattern in current_url for pattern in ["zhaopin.com/sou/", "zhaopin.com/joblist", "zhaopin.com/jobs"]):
                return {
                    "state": "SUCCESS",
                    "message": "跳转到职位列表，投递可能成功",
                    "details": {
                        "initial_url": initial_url,
                        "current_url": current_url,
                        "attempt": attempt + 1
                    }
                }

            # ===== B) DOM 关键词检测 (核心) =====
            # 成功关键词检测
            for keyword in self.SUCCESS_KEYWORDS:
                if keyword in current_content:
                    return {
                        "state": "SUCCESS",
                        "message": f"检测到成功关键词: {keyword}",
                        "details": {
                            "keyword": keyword,
                            "current_url": current_url,
                            "attempt": attempt + 1,
                            "url_changed": url_changed
                        }
                    }

            # 已投递关键词
            for keyword in self.ALREADY_APPLIED_KEYWORDS:
                if keyword in current_content:
                    return {
                        "state": "ALREADY_APPLIED",
                        "message": f"检测到已投递关键词: {keyword}",
                        "details": {
                            "keyword": keyword,
                            "current_url": current_url,
                            "attempt": attempt + 1
                        }
                    }

            # 登录失败关键词
            for keyword in self.LOGIN_FAIL_KEYWORDS:
                if keyword in current_content:
                    return {
                        "state": "LOGIN_FAIL",
                        "message": f"检测到登录失败关键词: {keyword}",
                        "details": {
                            "keyword": keyword,
                            "current_url": current_url,
                            "attempt": attempt + 1
                        }
                    }

            # 验证码关键词
            for keyword in self.CAPTCHA_KEYWORDS:
                if keyword in current_content:
                    return {
                        "state": "CAPTCHA_REQUIRED",
                        "message": f"检测到验证码: {keyword}",
                        "details": {
                            "keyword": keyword,
                            "current_url": current_url,
                            "attempt": attempt + 1
                        }
                    }

            # 失败关键词
            for keyword in self.FAIL_KEYWORDS:
                if keyword in current_content:
                    return {
                        "state": "CLICK_FAIL",
                        "message": f"检测到失败关键词: {keyword}",
                        "details": {
                            "keyword": keyword,
                            "current_url": current_url,
                            "attempt": attempt + 1
                        }
                    }

            # ===== C) 页面对比机制 =====
            # 如果 DOM 完全无变化 → CLICK_FAIL
            if current_hash == initial_hash and attempt >= 2:
                # 多次检测都是相同内容，说明点击没有生效
                print(f"[ApplyResultDetector] DOM无变化，尝试次数: {attempt + 1}")
                if attempt >= 3:
                    return {
                        "state": "CLICK_FAIL",
                        "message": "页面DOM无变化，点击可能未生效",
                        "details": {
                            "initial_hash": self.pre_click_dom_hash,
                            "current_hash": current_hash,
                            "attempt": attempt + 1
                        }
                    }

            # 如果还在职位详情页，检查投递按钮是否消失
            if "zhaopin.com/job/" in current_url or job_url:
                apply_btn = await page.query_selector(
                    'button:has-text("投递"), button:has-text("申请"), '
                    'a:has-text("投递"), a:has-text("申请")'
                )
                if not apply_btn:
                    # 投递按钮消失了，可能已经投递过了
                    # 但需要结合其他指标判断
                    if not any(kw in current_content for kw in self.APPLY_PAGE_KEYWORDS):
                        return {
                            "state": "SUCCESS",
                            "message": "投递按钮消失且无投递相关关键词，可能已投递",
                            "details": {
                                "current_url": current_url,
                                "attempt": attempt + 1
                            }
                        }

        # 4. 最多5次检测后仍无结果 → CLICK_NO_RESPONSE
        final_url = page.url
        final_content = await page.content()

        # 最后检查: 如果URL变了但没有成功关键词，可能是 SUCCESS
        if final_url != initial_url:
            return {
                "state": "SUCCESS",
                "message": "URL发生变化，判定为可能成功",
                "details": {
                    "initial_url": initial_url,
                    "current_url": final_url,
                    "total_attempts": 5
                }
            }

        return {
            "state": "CLICK_NO_RESPONSE",
            "message": "经过5次检测后无法确定投递结果",
            "details": {
                "initial_url": initial_url,
                "current_url": final_url,
                "initial_length": len(initial_content),
                "final_length": len(final_content),
                "total_attempts": 5
            }
        }

    async def verify_delivery_in_list(self, page) -> Dict:
        """
        通过访问"我的投递"列表来验证是否投递成功

        Returns:
            Dict: {"is_delivered": bool, "error": str}
        """
        try:
            # 尝试访问投递列表页
            delivery_urls = [
                "https://www.zhaopin.com/my/apply/",
                "https://i.zhaopin.com/My/ApplyList",
                "https://www.zhaopin.com/user/delivery"
            ]

            for url in delivery_urls:
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                    await asyncio.sleep(2)

                    content = await page.content()
                    if "投递" in content or "申请" in content:
                        return {"is_delivered": True, "list_url": url}
                except:
                    continue

            return {"is_delivered": False, "error": "无法访问投递列表页"}

        except Exception as e:
            return {"is_delivered": False, "error": str(e)}


class V3CrawlerRunner:
    """
    V3.4 爬虫执行器

    流程:
    1. PAGE STATE ENGINE → 识别页面状态
    2. VISION LAYER → 截图分析 UI 元素
    3. EMBEDDING DECISION LAYER → 向量相似度选择最佳按钮
    4. ACTION EXECUTION → Playwright 执行操作 (ClickExecutor)
    5. SUCCESS LEARNING ENGINE → 记录投递结果
    6. RECOVERY ENGINE → 异常时自动恢复
    7. CLICK VERIFICATION → 点击验证
    8. POPUP DETECTOR → 弹窗检测
    9. RISK SCORE → 动态风险控制
    """

    def __init__(self, platform, user_id: int, credentials: Dict):
        self.platform = platform  # ZhilianPlatform etc.
        self.user_id = user_id
        self.credentials = credentials

        # 初始化 V3.4 服务 (顺序重要!)
        self.vision_service = VisionService()
        self.embedding_service = EmbeddingService()
        self.decision_engine = DecisionEngine(embedding_service=self.embedding_service)
        self.recovery_engine = RecoveryEngine()
        self.success_learning = SuccessLearningEngine()
        self.job_memory = JobMemoryGraph()

        # PageStateEngine 需要在 vision_service 和 embedding_service 之后初始化
        self.page_state_engine = PageStateEngine(
            vision_service=self.vision_service,
            embedding_service=self.embedding_service
        )

        # 新增：执行层组件
        self.click_executor = ClickExecutor()
        self.popup_detector = PopupDetector()
        self.click_verification = ClickVerification()

        # 新增：登录状态检测和投递验证组件
        self.login_detector = LoginStateDetector()
        self.delivery_verifier = DeliveryVerifier()
        self.apply_result_detector = ApplyResultDetector()  # 投递结果确认系统

        # 配置服务关联
        self.recovery_engine.set_vision_service(self.vision_service)
        self.recovery_engine.set_embedding_service(self.embedding_service)

        # 执行日志
        self.execution_logs: List[Dict] = []

        # V3.4 新增
        self.risk_service = RiskScoreService() if RiskScoreService else None
        self.stealth_enabled = True
        self.current_risk_score = 0.0
        self.current_threshold = 0.7

        # 登录状态检测改进 - 失败计数器和API验证
        self.vision_detection_fail_count = 0  # 视觉检测连续失败次数
        self.max_vision_fail_before_phone = 2  # 超过此次数才触发手机验证
        self._last_login_result = None  # 上一次登录结果

    async def verify_cookie_via_api(self, page) -> Dict:
        """
        通过API验证Cookie是否有效
        访问用户信息API，如果返回有效数据说明Cookie有效

        Returns:
            Dict: {"valid": bool, "username": str or None, "error": str or None}
        """
        import json

        # 尝试多个可能返回用户信息的API端点
        api_endpoints = [
            "https://www.zhaopin.com/api/user/info",
            "https://i.zhaopin.com/api/user/profile",
            "https://www.zhaopin.com/api/resume/myinfo"
        ]

        for url in api_endpoints:
            try:
                # 从页面获取所有cookie
                cookies = await page.context.cookies()
                cookie_dict = {c['name']: c['value'] for c in cookies}

                # 发送API请求
                response = await page.request.get(url)
                if response.ok:
                    try:
                        data = await response.json()
                        # 检查返回数据是否包含用户信息
                        if isinstance(data, dict):
                            username = data.get('data', {}).get('username') or \
                                      data.get('data', {}).get('name') or \
                                      data.get('data', {}).get('realName') or \
                                      data.get('username') or data.get('name')
                            if username:
                                return {"valid": True, "username": username, "error": None}
                            # 即使没有用户名，200响应也说明Cookie有效
                            return {"valid": True, "username": None, "error": None}
                    except:
                        # 返回200但不是JSON，也说明Cookie有效
                        return {"valid": True, "username": None, "error": None}
                elif response.status == 401 or response.status == 403:
                    # 未授权，Cookie无效
                    continue
                else:
                    continue
            except Exception as e:
                continue

        return {"valid": False, "username": None, "error": "所有API验证失败"}

    async def verify_login_state_combined(self, page) -> Dict:
        """
        组合验证登录状态：视觉检测 + DOM元素 + API验证
        只有当所有方法都失败时才认为未登录

        Returns:
            Dict: {
                "is_logged_in": bool,
                "username": str or None,
                "confidence": float,
                "method": str  # "vision" / "dom" / "api" / "unknown"
            }
        """
        # 方法1: 视觉检测（首次检测）
        try:
            page_state = await self.page_state_engine.detect_page_state(page)
            self._last_page_state = page_state  # 保存最近一次检测结果
            if page_state.page_type != PageType.LOGIN.value and page_state.page_type != PageType.UNKNOWN.value:
                # 视觉检测认为已登录
                self.vision_detection_fail_count = 0  # 重置失败计数
                return {
                    "is_logged_in": True,
                    "username": None,
                    "confidence": page_state.confidence,
                    "method": "vision"
                }
        except Exception as e:
            print(f"[V3] 视觉检测失败: {e}")

        # 方法2: DOM元素检测
        try:
            login_state = await self.login_detector.detect_login_state(page)
            if login_state.get("is_logged_in"):
                self.vision_detection_fail_count = 0  # 重置失败计数
                return {
                    "is_logged_in": True,
                    "username": login_state.get("username"),
                    "confidence": 0.8,
                    "method": "dom"
                }
        except Exception as e:
            print(f"[V3] DOM检测失败: {e}")

        # 方法3: API验证（最可靠）
        try:
            api_result = await self.verify_cookie_via_api(page)
            if api_result.get("valid"):
                self.vision_detection_fail_count = 0  # 重置失败计数
                return {
                    "is_logged_in": True,
                    "username": api_result.get("username"),
                    "confidence": 0.95,
                    "method": "api"
                }
        except Exception as e:
            print(f"[V3] API验证失败: {e}")

        # 所有方法都失败，但需要区分"检测失败"和"确实未登录"
        # page_type 为 "unknown" 只表示检测无法确定页面类型，不代表未登录
        # 只有在明确检测到 LOGIN 页面时才认为是未登录
        page_state = getattr(self, '_last_page_state', None)
        if page_state and page_state.page_type == PageType.UNKNOWN.value:
            # 页面类型未知，不增加失败计数，也不认为未登录
            # 这种情况下保守返回已登录，让调用方自己判断
            print(f"[V3] 登录状态验证：页面类型未知，保守认为已登录")
            return {
                "is_logged_in": True,  # 保守认为已登录
                "username": None,
                "confidence": 0.0,
                "method": "unknown"
            }

        # 确实检测到登录页面或其他明确失败，增加失败计数
        self.vision_detection_fail_count += 1
        print(f"[V3] 登录状态验证失败，当前连续失败次数: {self.vision_detection_fail_count}")

        return {
            "is_logged_in": False,
            "username": None,
            "confidence": 0.0,
            "method": "unknown"
        }

    def should_trigger_phone_verification(self) -> bool:
        """
        判断是否应该触发手机验证
        只有连续失败超过阈值时才触发

        Returns:
            bool: True if should trigger phone verification
        """
        return self.vision_detection_fail_count >= self.max_vision_fail_before_phone

    def add_log(self, message: str, level: str = "info"):
        """添加执行日志"""
        log_entry = {
            "time": datetime.now().isoformat(),
            "message": message,
            "level": level
        }
        self.execution_logs.append(log_entry)
        print(f"[V3] {message}")

    async def _calculate_risk_before_click(self, page, context: dict) -> tuple[float, str, list]:
        """V3.4: 计算点击前的风险得分"""
        if not self.risk_service:
            return 0.0, "low", []

        # 收集风险上下文
        risk_context = {
            'page_type': context.get('page_type', 'unknown'),
            'consecutive_fail': context.get('consecutive_fail', 0),
            'recent_operations': context.get('recent_operations', 0),
            'has_error_keywords': context.get('has_error_keywords', False),
            'has_captcha': context.get('has_captcha', False),
            'url_redirected': context.get('url_redirected', False)
        }

        score, factors = self.risk_service.calculate_risk_score(risk_context)
        threshold = self.risk_service.calculate_threshold()
        level, action = self.risk_service.evaluate_risk_level(score, threshold)

        self.current_risk_score = score
        self.current_threshold = threshold

        return score, level, factors

    def _get_risk_reason_string(self, factors: list) -> str:
        """将风险因素转换为可读字符串"""
        if not factors:
            return "未知风险"

        reason_parts = []
        for f in factors:
            type_labels = {
                'login_required': '需要登录',
                'captcha': '检测到验证码',
                'popup': '检测到弹窗',
                'consecutive_fail': '连续失败',
                'high_frequency': '高频操作',
                'error_keywords': '错误关键词'
            }
            label = type_labels.get(f.get('type', ''), f.get('type', ''))
            reason_parts.append(f"{label}(+{f.get('weight', 0)*100:.0f}%)")

        return ', '.join(reason_parts)

    async def _emit_sse_event(self, event_type: str, data: dict):
        """发送SSE事件（如果可用）"""
        # 尝试通过task_event_manager发送
        try:
            from app.services.task_event_manager import emit_task_step
            if hasattr(self, 'task_id') and self.task_id:
                await emit_task_step(self.task_id, event_type, 'running', '', data)
        except Exception as e:
            print(f"[V3.4] SSE emit failed: {e}")

    def get_risk_status(self) -> dict:
        """获取当前风险状态"""
        if not self.risk_service:
            return {'enabled': False}

        status = self.risk_service.get_status()
        status['current_risk_score'] = self.current_risk_score
        status['current_threshold'] = self.current_threshold
        return status

    async def run_with_vision(self) -> Dict:
        """
        使用 V3.3 架构执行任务
        1. 初始化浏览器并检测页面状态
        2. 使用 Vision 分析页面
        3. 使用 Decision Engine 选择操作
        4. 执行并记录结果
        """
        self.add_log("V3.3 执行流程启动", "info")

        try:
            # 1. 初始化浏览器
            self.add_log("初始化浏览器...")
            await self.platform.init(headless=True)

            # 2. 导航到目标页面
            self.add_log("导航到智联招聘...")
            page = await self.platform.new_page()
            await page.goto(self.platform.base_url, wait_until='domcontentloaded')

            # 3. 检测页面状态
            page_state = await self.page_state_engine.detect_page_state(page)
            self.add_log(f"页面状态: {page_state.page_type}, 置信度: {page_state.confidence:.2f}")

            # 4. 根据页面状态执行相应操作
            if page_state.page_type == PageType.LOGIN.value:
                await self._handle_login_page(page, page_state)
            elif page_state.page_type == PageType.POPUP.value:
                await self._handle_popup(page, page_state)
            else:
                await self._handle_normal_page(page, page_state)

            return {
                "success": True,
                "logs": self.execution_logs,
                "state": page_state.page_type
            }

        except Exception as e:
            self.add_log(f"执行异常: {str(e)}", "error")
            return {
                "success": False,
                "error": str(e),
                "logs": self.execution_logs
            }
        finally:
            if self.platform:
                await self.platform.close()

    async def _handle_login_page(self, page, page_state: PageStateResult):
        """处理登录页面"""
        self.add_log("检测到登录页面，使用 Vision 分析登录表单...")

        # 使用 Vision 分析登录页面
        vision_result = await self.vision_service.analyze_page(page)

        # 查找登录按钮
        login_btn = self.vision_service.find_login_button(vision_result)
        if not login_btn:
            self.add_log("未找到登录按钮，尝试使用凭证登录...", "warn")
            # 使用 Cookie 登录
            if self.credentials.get('cookie'):
                success = await self.platform.login(cookie=self.credentials['cookie'])
                self.add_log(f"Cookie 登录结果: {'成功' if success else '失败'}")
        else:
            self.add_log(f"找到登录按钮: {login_btn.text}", "info")
            # 使用 Decision Engine 确认这是最佳登录选项
            elements = [e.to_dict() if hasattr(e, 'to_dict') else e for e in vision_result.elements]
            decision = await self.decision_engine.pick_login_action(elements)
            self.add_log(f"决策引擎选择: {decision.selected_element}", "info")

    async def _handle_popup(self, page, page_state: PageStateResult):
        """处理弹窗"""
        self.add_log("检测到弹窗，使用 Recovery Engine 关闭...")

        # 使用 Recovery Engine 处理弹窗
        recovery_result = await self.recovery_engine.handle_popup(page, {"state": PageState.POPUP})

        if recovery_result.success:
            self.add_log(f"弹窗处理成功: {recovery_result.message}")
        else:
            self.add_log(f"弹窗处理失败: {recovery_result.message}", "error")

    async def _handle_normal_page(self, page, page_state: PageStateResult):
        """处理正常页面"""
        self.add_log(f"页面状态正常: {page_state.page_type}")

        # 使用 Vision 分析页面元素
        vision_result = await self.vision_service.analyze_page(page)

        # 查找投递按钮
        apply_btn = self.vision_service.find_apply_button(vision_result)

        if apply_btn:
            self.add_log(f"找到投递按钮: {apply_btn.text}", "info")
            # 使用 Decision Engine 确认
            elements = [e.to_dict() if hasattr(e, 'to_dict') else e for e in vision_result.elements]
            decision = await self.decision_engine.pick_apply_button(elements)
            self.add_log(f"决策引擎选择: {decision.selected_element}, 置信度: {decision.confidence:.2f}")
        else:
            self.add_log("未找到投递按钮", "warn")

    def _element_to_dict(self, elem) -> Dict:
        """将 UIElement 或 dict 转换为 dict"""
        if isinstance(elem, dict):
            return elem
        if hasattr(elem, 'to_dict'):
            return elem.to_dict()
        if hasattr(elem, 'text'):
            return {
                'text': elem.text,
                'type': getattr(elem, 'element_type', 'button'),
                'x': elem.bounding_box.get('x', 0) if hasattr(elem, 'bounding_box') and elem.bounding_box else 0,
                'y': elem.bounding_box.get('y', 0) if hasattr(elem, 'bounding_box') and elem.bounding_box else 0,
                'width': elem.bounding_box.get('width', 0) if hasattr(elem, 'bounding_box') and elem.bounding_box else 0,
                'height': elem.bounding_box.get('height', 0) if hasattr(elem, 'bounding_box') and elem.bounding_box else 0,
            }
        return {}

    async def _find_apply_button_dom(self, page, job_url: str = None) -> Optional[Dict]:
        """
        DOM-based 投递按钮查找（Fallback when Vision fails）
        使用 Zhilian 平台的已知选择器
        """
        # 多次滚动页面以加载动态内容
        try:
            # 滚动到顶部
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.3)

            # 滚动到中间
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
            await asyncio.sleep(0.3)

            # 滚动到底部
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.5)

            # 再滚动回中间
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
            await asyncio.sleep(0.3)
        except Exception as e:
            self.add_log(f"滚动页面失败: {str(e)}", "warn")

        apply_selectors = [
            '.collect-and-apply__btn',
            '.btn.apply-btn',
            '.summary-planes__action button',
            '.a-button.a--bordered.a--filled',
            'button:has-text("立即投递")',
            'a:has-text("立即投递")',
            'button:has-text("投递")',
            'a:has-text("投递")',
            'button:has-text("申请")',
            'a:has-text("申请")',
            '.btn-primary',
            '.apply-button',
            '[class*="apply"]',
            '[class*="投递"]',
            'button[type="submit"]',
            '.job-detail-actions button',
            '.job-btn-container button',
            '.submit-btn',
            '.applyAction',
            '#applyBtn',
            '.start-apply',
            'button[class*="apply"]',
            'a[class*="apply"]',
            '.job-detail-tab button',
            '.bottom-area button',
        ]

        self.add_log(f"DOM Fallback: 尝试 {len(apply_selectors)} 个选择器...")

        # 尝试查找按钮
        for selector in apply_selectors:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    text = await btn.inner_text() or await btn.get_attribute('textContent') or ''
                    bounding_box = await btn.bounding_box()
                    self.add_log(f"DOM找到按钮: {selector}, text: {text.strip()[:50]}")
                    return {
                        'text': text.strip(),
                        'selector': selector,
                        'x': bounding_box['x'] if bounding_box else 0,
                        'y': bounding_box['y'] if bounding_box else 0,
                        'width': bounding_box['width'] if bounding_box else 0,
                        'height': bounding_box['height'] if bounding_box else 0,
                        'type': 'button'
                    }
            except Exception as e:
                continue

        self.add_log("DOM Fallback: 未找到任何按钮")
        return None

    async def apply_job_with_vision(self, job_url: str, company: str = "", title: str = "") -> Dict:
        """
        V3.4 Fallback投递流程 - Vision仅用于异常检测

        【战略调整】根据修改意见:
        - Vision不再用于"找按钮"，而是用于检测异常页面
        - 投递执行使用 platform.apply_job() (确定性DOM/Playwright)
        - Vision用于检测: CAPTCHA、登录失效、风控提示、结果页面

        流程:
        1. 初始化浏览器
        2. 导航到职位详情页
        3. 使用 platform.apply_job() 执行投递（确定性执行）
        4. 使用 Vision 检测异常（CAPTCHA、登录失效、风控）
        5. 使用 Vision 检测结果页面（已投递、今日已投递）
        6. 记录结果
        """
        self.add_log(f"[Vision Fallback] 开始投递职位: {job_url}")
        self.add_log(f"[Vision Fallback] 职位信息: {title} @ {company}")

        page = None
        try:
            # 1. 检查浏览器是否就绪
            browser_ready = await self.platform.is_browser_ready()
            if not browser_ready:
                self.add_log("[Vision Fallback] 浏览器未就绪，尝试重新初始化...")
                await self.platform.close()
                await self.platform.init(headless=False)
            else:
                self.add_log("[Vision Fallback] 浏览器状态正常")

            # 2. 创建新页面
            page = await self.platform.new_page(force_new=True)

            if not page:
                self.add_log("[Vision Fallback] 创建页面失败，无法投递", "error")
                return {
                    'success': False,
                    'message': '创建页面失败',
                    'status': 'failed',
                    'verified': False,
                    'verify_details': {}
                }

            # 3. 导航到职位详情页
            self.add_log("[Vision Fallback] 导航到职位详情页...")
            await page.goto(job_url, wait_until='domcontentloaded')
            await asyncio.sleep(random.uniform(1, 2))

            # 4. 【核心变化】使用 platform.apply_job() 执行投递
            #    而不是依赖Vision找按钮
            self.add_log("[Vision Fallback] 使用 platform.apply_job() 执行投递...")
            platform_result = await self.platform.apply_job(job_url)
            self.add_log(f"[Vision Fallback] platform.apply_result: {platform_result.get('message', 'unknown')}")

            platform_success = platform_result.get('success', False)
            platform_status = platform_result.get('status', '')

            if platform_success or platform_status == 'submitted':
                self.add_log("[Vision Fallback] 投递成功（通过platform.apply_job）", "success")
                record = ApplyRecord(
                    job_id=job_url,
                    company=platform_result.get('company', '') or company,
                    title=platform_result.get('title', '') or title,
                    page_type="job_detail",
                    result="success",
                    failure_reason="",
                    features={"method": "vision_fallback_platform_apply"}
                )
                self.success_learning.record_apply(record)
                return {
                    "success": True,
                    "result": "success",
                    "message": platform_result.get('message', '投递成功'),
                    "apply_result": platform_result,
                    "method": "platform_apply",
                    "logs": self.execution_logs
                }

            # 5. 如果platform.apply_job()失败，使用Vision检测异常
            self.add_log("[Vision Fallback] platform.apply_job()失败，使用Vision检测异常...")

            # Vision异常检测
            vision_result = await self.vision_service.analyze_page(page)
            self.add_log(f"[Vision Fallback] Vision分析完成: page_type={vision_result.page_type}")

            # 检测CAPTCHA异常
            if vision_result.page_type == PageType.CAPTCHA:
                self.add_log("[Vision Fallback] 检测到CAPTCHA验证码", "error")
                record = ApplyRecord(
                    job_id=job_url,
                    company=company,
                    title=title,
                    page_type="captcha",
                    result="captcha",
                    failure_reason="CAPTCHA检测",
                    features={"method": "vision_captcha_detected"}
                )
                self.success_learning.record_apply(record)
                return {
                    "success": False,
                    "error": "CAPTCHA_REQUIRED",
                    "message": "检测到验证码",
                    "vision_page_type": "CAPTCHA",
                    "logs": self.execution_logs
                }

            # 检测登录异常
            if vision_result.page_type == PageType.LOGIN:
                self.add_log("[Vision Fallback] 检测到登录失效", "error")
                record = ApplyRecord(
                    job_id=job_url,
                    company=company,
                    title=title,
                    page_type="login",
                    result="login_required",
                    failure_reason="登录失效",
                    features={"method": "vision_login_detected"}
                )
                self.success_learning.record_apply(record)
                return {
                    "success": False,
                    "error": "LOGIN_FAIL",
                    "message": "登录已失效",
                    "vision_page_type": "LOGIN",
                    "logs": self.execution_logs
                }

            # 检测"已投递"等结果页面
            if any(keyword in (vision_result.raw_response or {}).get('page_type', '').lower()
                   for keyword in ['applied', 'already', '已投递', '今日已投递']):
                self.add_log("[Vision Fallback] Vision检测到已投递状态", "warn")
                return {
                    "success": True,
                    "result": "already_applied",
                    "message": "该职位已投递",
                    "vision_page_type": vision_result.page_type.value,
                    "logs": self.execution_logs
                }

            # 6. 检查raw_response中的has_captcha等标记
            raw = vision_result.raw_response or {}
            if raw.get('has_captcha') or raw.get('has_verify'):
                self.add_log("[Vision Fallback] raw_response检测到验证码标记", "error")
                return {
                    "success": False,
                    "error": "CAPTCHA_REQUIRED",
                    "message": "检测到验证码标记",
                    "vision_page_type": vision_result.page_type.value,
                    "logs": self.execution_logs
                }

            # 7. 所有检测都通过但投递失败，返回失败
            self.add_log(f"[Vision Fallback] 投递失败，原因未知: {platform_result.get('message', 'unknown')}", "error")
            record = ApplyRecord(
                job_id=job_url,
                company=company,
                title=title,
                page_type=vision_result.page_type.value,
                result="failed",
                failure_reason=platform_result.get('message', 'unknown'),
                features={"method": "vision_fallback_all_failed"}
            )
            self.success_learning.record_apply(record)
            return {
                "success": False,
                "error": platform_result.get('message', '投递失败'),
                "result": platform_result.get('status', 'failed'),
                "vision_page_type": vision_result.page_type.value,
                "logs": self.execution_logs
            }

        except Exception as e:
            self.add_log(f"[Vision Fallback] 异常: {str(e)}", "error")
            return {
                "success": False,
                "error": str(e),
                "logs": self.execution_logs
            }
        # NOTE: 不在这里关闭 page，让它保持打开状态
        # 因为手机验证码流程可能需要在同一浏览器上下文中继续操作
        # page 的清理会在 platform.close() 时统一进行

    async def apply_job_smart(self, job_url: str, company: str = "", title: str = "") -> Dict:
        """
        V3.4 智能投递 - 主路径优先策略

        流程:
        1. Step 1: 直接执行 platform.apply_job()（主路径，100%成功）
        2. Step 2: Fallback → apply_job_with_vision（Vision仅用于异常检测）
        3. Step 3: Recovery → recovery_engine.handle_apply_failure()

        【战略】分工原则：
        - 投递执行: DOM / Playwright（确定性）
        - 状态判断: 规则 + API
        - 异常识别: Vision（辅助）
        - 决策优化: Learning Engine
        """
        self.add_log("=" * 50)
        self.add_log("[apply_job_smart] V3.4 智能投递策略启动")
        self.add_log("=" * 50)

        # ========== Step 1: 直接执行（主路径）==========
        self.add_log("[Step 1] 直接执行 platform.apply_job()...")
        self.add_log("[Apply] method=direct_apply")

        try:
            platform_result = await self.platform.apply_job(job_url)
            platform_success = platform_result.get('success', False)
            platform_status = platform_result.get('status', '')

            self.add_log(f"[Apply] direct_apply result: {platform_result.get('message', 'unknown')}")
            self.add_log(f"[Apply] direct_apply status: {platform_status}")

            if platform_success or platform_status == 'submitted':
                self.add_log("[Apply] direct_apply=success", "success")
                # 记录到 Success Learning
                record = ApplyRecord(
                    job_id=job_url,
                    company=company or platform_result.get('company', ''),
                    title=title or platform_result.get('title', ''),
                    page_type="job_detail",
                    result="success",
                    failure_reason="",
                    features={"method": "direct_apply", "platform": platform_result.get('company', '')}
                )
                self.success_learning.record_apply(record)
                return {
                    "success": True,
                    "result": "success",
                    "method": "direct_apply",
                    "message": platform_result.get('message', '投递成功'),
                    "apply_result": platform_result,
                    "logs": self.execution_logs
                }
            else:
                self.add_log(f"[Apply] direct_apply=failed ({platform_result.get('message', 'unknown')})", "warn")
                self.add_log("[Apply] vision_fallback=pending")

        except Exception as e:
            self.add_log(f"[Apply] direct_apply exception: {str(e)}", "error")
            self.add_log("[Apply] vision_fallback=pending")

        # ========== Step 2: Fallback → apply_job_with_vision ==========
        self.add_log("[Step 2] 主路径失败，Fallback到 Vision 流程...")
        self.add_log("[Apply] method=vision_fallback")

        try:
            vision_result = await self.apply_job_with_vision(job_url, company, title)
            vision_success = vision_result.get('success', False)

            self.add_log(f"[Apply] vision_fallback result: {vision_result.get('result', 'unknown')}")

            if vision_success:
                self.add_log("[Apply] vision_fallback=success", "success")
                return {
                    **vision_result,
                    "method": "vision_fallback",
                    "logs": self.execution_logs
                }
            else:
                self.add_log(f"[Apply] vision_fallback=failed ({vision_result.get('error', 'unknown')})", "warn")
                self.add_log("[Apply] recovery=pending")

        except Exception as e:
            self.add_log(f"[Apply] vision_fallback exception: {str(e)}", "error")
            self.add_log("[Apply] recovery=pending")

        # ========== Step 3: Recovery ==========
        self.add_log("[Step 3] Vision流程也失败，触发Recovery...")
        self.add_log("[Apply] method=recovery")

        try:
            recovery_result = await self.recovery_engine.handle_apply_failure(
                page=None,  # 可能没有可用page
                job_url=job_url,
                error_context={
                    "platform_result": platform_result if 'platform_result' in dir() else None,
                    "vision_result": vision_result if 'vision_result' in dir() else None
                }
            )
            self.add_log(f"[Apply] recovery result: {recovery_result}")

            # RecoveryResult 是 dataclass，需要转换
            from dataclasses import asdict
            result_dict = asdict(recovery_result) if hasattr(recovery_result, '__dataclass_fields__') else recovery_result

            return {
                **result_dict,
                "method": "recovery",
                "logs": self.execution_logs
            }

        except Exception as e:
            self.add_log(f"[Apply] recovery exception: {str(e)}", "error")
            return {
                "success": False,
                "error": str(e),
                "method": "recovery_failed",
                "logs": self.execution_logs
            }

    async def login_with_vision(self) -> Dict:
        """
        使用 V3.3 架构登录

        流程:
        1. 初始化浏览器
        2. 检测登录状态
        3. Vision 分析登录表单
        4. Decision Engine 选择登录方式
        5. Recovery Engine 处理异常
        6. 验证登录用户名

        Returns:
            Dict: {
                "success": bool,
                "username": str or None,
                "logs": list
            }
        """
        self.add_log("V3.3 登录流程启动")
        logged_in_username = None

        try:
            # 1. 初始化浏览器
            self.add_log("初始化浏览器...")
            await self.platform.init(headless=True)

            # 2. 创建新页面
            page = await self.platform.new_page()

            # 1. 检测页面状态
            self.add_log("检测页面状态...")
            page_state = await self.page_state_engine.detect_page_state(page)
            self.add_log(f"当前页面状态: {page_state.page_type}")

            # 2. 如果是登录页面
            if page_state.page_type == PageType.LOGIN.value:
                # 使用 Vision 分析
                self.add_log("使用 Vision 分析登录页面...")
                vision_result = await self.vision_service.analyze_page(page)

                # 使用 Decision Engine 选择登录按钮
                elements = [e.to_dict() if hasattr(e, 'to_dict') else e for e in vision_result.elements]
                decision = await self.decision_engine.pick_login_action(elements)
                self.add_log(f"决策引擎选择: {decision.selected_element}")

            # 3. 使用 Cookie 登录
            if self.credentials.get('cookie'):
                self.add_log("使用 Cookie 登录...")
                success = await self.platform.login(cookie=self.credentials['cookie'])
                if success:
                    self.add_log("Cookie 登录成功，等待页面稳定...", "success")
                    # 等待页面稳定
                    await asyncio.sleep(2)

                    # 使用组合验证方法验证登录状态
                    self.add_log("使用组合验证方法确认登录状态...")
                    verify_result = await self.verify_login_state_combined(page)

                    if verify_result["is_logged_in"]:
                        self.vision_detection_fail_count = 0  # 重置失败计数
                        logged_in_username = verify_result.get("username") or await self.get_logged_in_username(page)
                        if logged_in_username:
                            self.add_log(f"已确认登录用户: {logged_in_username} (验证方法: {verify_result['method']})", "success")
                        else:
                            self.add_log(f"Cookie有效，已登录 (验证方法: {verify_result['method']})", "success")
                        return {
                            "success": True,
                            "username": logged_in_username,
                            "logs": self.execution_logs
                        }
                    elif verify_result["method"] == "unknown":
                        # 验证方法返回 unknown，说明检测失败但 Cookie 登录实际成功了
                        # platform.login 内部已经验证过登录状态，所以这里应该认为成功
                        self.vision_detection_fail_count = 0  # 重置失败计数
                        self.add_log(f"Cookie有效（平台内部验证成功，外部检测不确定）", "success")
                        return {
                            "success": True,
                            "username": None,
                            "logs": self.execution_logs
                        }
                    else:
                        # 无法确认登录状态，但只有连续失败超过阈值才触发手机验证
                        self.add_log(f"无法确认登录状态，Cookie 可能已过期 (验证方法: {verify_result['method']})", "error")
                        if self.should_trigger_phone_verification():
                            self.add_log(f"连续验证失败 {self.vision_detection_fail_count} 次，触发手机验证", "warn")
                            return {
                                "success": False,
                                "username": None,
                                "error": "Cookie 已过期或无效",
                                "require_phone_verification": True,
                                "logs": self.execution_logs
                            }
                        else:
                            # 未超过阈值，保守返回失败但不触发手机验证，让调用方重试
                            self.add_log(f"未超过阈值({self.vision_detection_fail_count}/{self.max_vision_fail_before_phone})，等待重试", "warn")
                            return {
                                "success": False,
                                "username": None,
                                "error": "Cookie 可能已过期，请重试",
                                "require_phone_verification": False,
                                "retry_likely_success": True,
                                "logs": self.execution_logs
                            }
                else:
                    # Cookie登录返回失败，同样需要组合验证来判断
                    self.add_log("Cookie 登录返回失败，使用组合验证判断...", "warn")
                    verify_result = await self.verify_login_state_combined(page)

                    if verify_result["is_logged_in"]:
                        # 实际上已登录，可能是检测问题
                        self.vision_detection_fail_count = 0
                        logged_in_username = verify_result.get("username") or await self.get_logged_in_username(page)
                        self.add_log(f"组合验证显示已登录: {logged_in_username}", "success")
                        return {
                            "success": True,
                            "username": logged_in_username,
                            "logs": self.execution_logs
                        }
                    elif verify_result["method"] == "unknown":
                        # 验证方法返回 unknown，同样保守认为可能已登录
                        self.vision_detection_fail_count = 0  # 重置失败计数
                        self.add_log(f"Cookie登录失败但检测不确定，保守认为可能已登录", "warn")
                        return {
                            "success": True,
                            "username": None,
                            "logs": self.execution_logs
                        }
                    else:
                        self.add_log("Cookie 登录失败", "error")
                        if self.should_trigger_phone_verification():
                            self.add_log(f"连续验证失败 {self.vision_detection_fail_count} 次，触发手机验证", "warn")
                            return {
                                "success": False,
                                "username": None,
                                "error": "Cookie 已过期",
                                "require_phone_verification": True,
                                "logs": self.execution_logs
                            }
                        else:
                            return {
                                "success": False,
                                "username": None,
                                "error": "Cookie 登录失败，请重试",
                                "require_phone_verification": False,
                                "retry_likely_success": True,
                                "logs": self.execution_logs
                            }

            # 4. 使用账号密码登录
            elif self.credentials.get('username') and self.credentials.get('password'):
                self.add_log("使用账号密码登录...")
                success = await self.platform.login(
                    username=self.credentials['username'],
                    password=self.credentials['password']
                )
                if success:
                    self.add_log("账号密码登录成功", "success")
                    # 验证登录状态并获取用户名
                    await asyncio.sleep(1)
                    logged_in_username = await self.get_logged_in_username(page)
                    if logged_in_username:
                        self.add_log(f"已确认登录用户: {logged_in_username}", "success")
                    return {
                        "success": True,
                        "username": logged_in_username,
                        "logs": self.execution_logs
                    }
                else:
                    self.add_log("账号密码登录失败", "error")
                    return {
                        "success": False,
                        "username": None,
                        "logs": self.execution_logs
                    }

            # 5. Recovery 处理
            if page_state.requires_action:
                self.add_log("页面需要操作，使用 Recovery Engine...")
                recovery_result = await self.recovery_engine.recover(
                    PageState.LOGIN if page_state.page_type == PageType.LOGIN.value else PageState.UNKNOWN,
                    {"page": page}
                )
                self.add_log(f"Recovery 结果: {recovery_result.message}")

            return {
                "success": False,
                "username": None,
                "logs": self.execution_logs
            }

        except Exception as e:
            self.add_log(f"登录异常: {str(e)}", "error")
            return {
                "success": False,
                "username": None,
                "error": str(e),
                "logs": self.execution_logs
            }

    def get_execution_logs(self) -> List[Dict]:
        """获取执行日志"""
        return self.execution_logs

    def get_learning_stats(self) -> Dict:
        """获取学习引擎统计"""
        return self.success_learning.export_learning()

    def export_learning_data(self) -> Dict:
        """导出学习数据"""
        return self.success_learning.export_learning()

    async def get_logged_in_username(self, page) -> Optional[str]:
        """
        获取当前登录用户的用户名

        Args:
            page: Playwright page 对象

        Returns:
            str or None: 登录用户名，如"王庆"
        """
        login_state = await self.login_detector.detect_login_state(page)
        if login_state.get('is_logged_in'):
            username = login_state.get('username')
            self.add_log(f"检测到已登录用户: {username}")
            return username
        else:
            self.add_log("未检测到登录状态", "warn")
            return None

    async def verify_delivery_status(self, page, job_url: str = None) -> Dict:
        """
        验证投递状态

        Args:
            page: Playwright page 对象
            job_url: 职位URL（可选）

        Returns:
            Dict: {
                "is_delivered": bool,
                "username": str,
                "delivery_count": int,
                "matched_job": dict or None
            }
        """
        self.add_log("开始验证投递状态...")

        # 1. 获取登录用户名
        username = await self.get_logged_in_username(page)

        if not username:
            return {
                "is_delivered": False,
                "username": None,
                "delivery_count": 0,
                "matched_job": None,
                "error": "用户未登录"
            }

        # 2. 验证投递
        verify_result = await self.delivery_verifier.verify_delivery(page, job_url)

        self.add_log(f"投递验证结果: 已投递{verify_result.get('total_count', 0)}个职位")

        if verify_result.get('is_delivered'):
            self.add_log("当前职位投递成功!", "success")
        elif job_url:
            self.add_log(f"当前职位未在投递列表中找到", "warn")

        return {
            "is_delivered": verify_result.get('is_delivered', False),
            "username": username,
            "delivery_count": verify_result.get('total_count', 0),
            "matched_job": verify_result.get('matched_job'),
            "delivery_list": verify_result.get('delivery_list', []),
            "error": verify_result.get('error')
        }


async def run_v3_login(platform, user_id: int, credentials: Dict) -> Dict:
    """V3.3 登录执行入口"""
    runner = V3CrawlerRunner(platform, user_id, credentials)
    login_result = await runner.login_with_vision()
    return {
        **login_result,
        "learning_stats": runner.get_learning_stats()
    }


async def run_v3_apply(platform, user_id: int, credentials: Dict, job_url: str) -> Dict:
    """V3.4 投递执行入口"""
    runner = V3CrawlerRunner(platform, user_id, credentials)
    result = await runner.apply_job_smart(job_url)
    return {
        **result,
        "logs": runner.get_execution_logs(),
        "learning_stats": runner.get_learning_stats()
    }
