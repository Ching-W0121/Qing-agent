"""
V3.3 Vision Service - 视觉识别服务
使用 Doubao-1.5-vision-pro 分析页面截图，识别UI元素
"""

import base64
import io
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class PageType(Enum):
    """页面类型枚举"""
    LOGIN = "login"
    JOB_LIST = "job_list"
    JOB_DETAIL = "job_detail"
    JOB_APPLY_FORM = "job_apply_form"
    POPUP = "popup"
    CAPTCHA = "captcha"
    UNKNOWN = "unknown"


@dataclass
class UIElement:
    """UI元素"""
    text: str
    element_type: str  # button, input, link, text, image
    bounding_box: Dict[str, float]  # x, y, width, height
    confidence: float = 1.0
    attributes: Dict[str, str] = None


@dataclass
class VisionResult:
    """视觉识别结果"""
    page_type: PageType
    elements: List[UIElement]
    buttons: List[UIElement]
    popups: List[UIElement]
    inputs: List[UIElement]
    success: bool
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


class VisionService:
    """
    V3.3 视觉识别服务
    使用 Doubao-1.5-vision-pro 进行页面视觉分析
    """

    # V3.3 Doubao API 配置
    API_KEY = "fddc1778-d04c-403e-8327-ab68ec1ec9dd"
    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    VISION_MODEL = "doubao-seed-2-0-code-preview-260215"

    def __init__(self, api_key: str = None, base_url: str = None):
        """
        初始化视觉服务

        Args:
            api_key: Doubao API密钥
            base_url: API基础URL
        """
        self.api_key = api_key or self.API_KEY
        self.base_url = base_url or self.BASE_URL
        self.model = self.VISION_MODEL
        self._client = None  # 延迟初始化

    def _get_client(self):
        """获取API客户端（延迟初始化）"""
        if self._client is None:
            # 这里应该初始化 Doubao API 客户端
            # 实际使用时会通过配置获取 API key
            self._client = DoubaoClient(api_key=self.api_key, base_url=self.base_url)
        return self._client

    async def analyze_screenshot(self, screenshot_bytes: bytes) -> VisionResult:
        """
        分析截图

        Args:
            screenshot_bytes: PNG格式的截图数据

        Returns:
            VisionResult: 包含页面类型和识别到的UI元素
        """
        try:
            # 将图片转换为 base64
            image_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')

            print(f"[Vision API] 调用 Doubao Vision API, 图片大小: {len(screenshot_bytes)} bytes")

            # 调用 Doubao Vision API
            client = self._get_client()
            response = await client.vision(
                model=self.model,
                image=image_base64,
                prompt=self._get_analysis_prompt()
            )

            # 调试: 打印响应中的buttons信息
            try:
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '{}')
                import json
                data = json.loads(content) if isinstance(content, str) else content
                print(f"[Vision API] API返回buttons数量: {len(data.get('buttons', []))}")
                print(f"[Vision API] API返回buttons: {data.get('buttons', [])[:2]}")
            except Exception as parse_err:
                print(f"[Vision API] 解析响应内容失败: {parse_err}")

            return self._parse_vision_response(response)

        except Exception as e:
            print(f"[Vision API] 异常: {str(e)}")
            return VisionResult(
                page_type=PageType.UNKNOWN,
                elements=[],
                buttons=[],
                popups=[],
                inputs=[],
                success=False,
                error=str(e)
            )

    async def analyze_page(self, page) -> VisionResult:
        """
        分析当前页面（截图 + DOM）

        Args:
            page: Playwright page 对象

        Returns:
            VisionResult: 页面分析结果
        """
        try:
            # 等待页面稳定后再操作，避免 "page is navigating" 错误
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except Exception:
                pass  # 超时继续执行

            # 截图
            screenshot_bytes = await page.screenshot()
            print(f"[VisionService] 截图大小: {len(screenshot_bytes)} bytes")

            # 获取页面内容
            page_info = await self._get_page_info(page)
            print(f"[VisionService] page_info: {page_info.get('url', 'N/A')}, title: {page_info.get('title', 'N/A')[:30]}")

            # 调用视觉分析
            vision_result = await self.analyze_screenshot(screenshot_bytes)
            print(f"[VisionService] analyze_screenshot返回: success={vision_result.success}, buttons={len(vision_result.buttons)}, error={vision_result.error}")

            # 结合 DOM 信息增强识别结果
            vision_result = self._enhance_with_dom(vision_result, page_info)
            print(f"[VisionService] 最终结果: buttons={len(vision_result.buttons)}")

            return vision_result

        except Exception as e:
            print(f"[VisionService] analyze_page异常: {e}")
            import traceback
            traceback.print_exc()
            return VisionResult(
                page_type=PageType.UNKNOWN,
                elements=[],
                buttons=[],
                popups=[],
                inputs=[],
                success=False,
                error=str(e)
            )

    def _get_analysis_prompt(self) -> str:
        """获取分析提示词"""
        return """分析这个招聘页面的截图，识别：

1. 页面类型（login/job_list/job_detail/popup/captcha/unknown）
2. 所有按钮（特别是投递按钮、登录按钮、关闭按钮）
3. 弹窗（如登录弹窗、提示弹窗）
4. 输入框（如用户名、密码、验证码）
5. 其他重要UI元素

请以JSON格式返回结果：
{
  "page_type": "页面类型",
  "buttons": [{"text": "按钮文字", "x": 100, "y": 200, "width": 100, "height": 40, "type": "button"}],
  "popups": [{"text": "弹窗内容", "x": 0, "y": 0, "width": 500, "height": 300}],
  "inputs": [{"label": "输入框标签", "x": 100, "y": 200, "width": 200, "height": 40, "type": "text/password"}],
  "has_login_popup": true/false,
  "has_captcha": true/false,
  "has_apply_button": true/false,
  "confidence": 0.0-1.0
}"""

    def _parse_vision_response(self, response: Dict) -> VisionResult:
        """解析视觉API响应"""
        # 保存原始响应用于调试
        raw_resp = response
        try:
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '{}')

            # 尝试提取JSON
            import json
            try:
                data = json.loads(content)
            except:
                # 尝试从markdown代码块中提取
                import re
                match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                else:
                    # 尝试提取 {...} 格式
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        data = json.loads(match.group(0))
                    else:
                        raise ValueError("无法解析视觉响应")

            # 解析页面类型
            page_type_str = data.get('page_type', 'unknown').lower()
            if 'login' in page_type_str:
                page_type = PageType.LOGIN
            elif 'list' in page_type_str or 'search' in page_type_str:
                page_type = PageType.JOB_LIST
            elif 'detail' in page_type_str or 'job' in page_type_str:
                page_type = PageType.JOB_DETAIL
            elif 'apply' in page_type_str or 'form' in page_type_str:
                page_type = PageType.JOB_APPLY_FORM
            elif 'popup' in page_type_str or 'dialog' in page_type_str:
                page_type = PageType.POPUP
            elif 'captcha' in page_type_str or 'verify' in page_type_str:
                page_type = PageType.CAPTCHA
            else:
                page_type = PageType.UNKNOWN

            # 解析按钮
            buttons = []
            for btn in data.get('buttons', []):
                buttons.append(UIElement(
                    text=btn.get('text', ''),
                    element_type='button',
                    bounding_box={
                        'x': btn.get('x', 0),
                        'y': btn.get('y', 0),
                        'width': btn.get('width', 0),
                        'height': btn.get('height', 0)
                    },
                    confidence=data.get('confidence', 0.8)
                ))

            # 解析弹窗
            popups = []
            for popup in data.get('popups', []):
                popups.append(UIElement(
                    text=popup.get('text', ''),
                    element_type='popup',
                    bounding_box={
                        'x': popup.get('x', 0),
                        'y': popup.get('y', 0),
                        'width': popup.get('width', 0),
                        'height': popup.get('height', 0)
                    },
                    confidence=data.get('confidence', 0.8)
                ))

            # 解析输入框
            inputs = []
            for inp in data.get('inputs', []):
                inputs.append(UIElement(
                    text=inp.get('label', ''),
                    element_type='input',
                    bounding_box={
                        'x': inp.get('x', 0),
                        'y': inp.get('y', 0),
                        'width': inp.get('width', 0),
                        'height': inp.get('height', 0)
                    },
                    confidence=data.get('confidence', 0.8)
                ))

            return VisionResult(
                page_type=page_type,
                elements=buttons + popups + inputs,
                buttons=buttons,
                popups=popups,
                inputs=inputs,
                success=True,
                raw_response=data
            )

        except Exception as e:
            return VisionResult(
                page_type=PageType.UNKNOWN,
                elements=[],
                buttons=[],
                popups=[],
                inputs=[],
                success=False,
                error=str(e),
                raw_response=raw_resp
            )

    async def _get_page_info(self, page) -> Dict:
        """获取页面DOM信息"""
        try:
            # 等待页面稳定
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=3000)
            except Exception:
                pass

            # 获取视口大小
            viewport = page.viewport_size

            # 获取页面URL
            url = page.url

            # 获取页面标题
            title = await page.title()

            # 尝试获取登录弹窗
            try:
                login_popup = await page.query_selector(
                    '.login-dialog, .login-popup, [class*="login"][class*="popup"], '
                    '[class*="login"][class*="dialog"], .modal[class*="login"]'
                )
                has_login_popup = login_popup is not None
            except Exception:
                has_login_popup = False

            return {
                'viewport': viewport,
                'url': url,
                'title': title,
                'has_login_popup': has_login_popup
            }
        except Exception:
            return {}

    def _enhance_with_dom(self, vision_result: VisionResult, page_info: Dict) -> VisionResult:
        """结合DOM信息增强视觉识别结果"""
        # 如果视觉识别发现问题，可以结合DOM进行修正

        # 检查是否有登录弹窗（DOM级别检测）
        if page_info.get('has_login_popup') and vision_result.page_type != PageType.LOGIN:
            # 如果DOM发现登录弹窗但视觉没识别到，更新结果
            vision_result.page_type = PageType.POPUP

        return vision_result

    def find_apply_button(self, vision_result: VisionResult) -> Optional[UIElement]:
        """找到投递按钮"""
        apply_keywords = ['投递', '申请', '立即投递', 'apply', 'submit', '发送', 'confirm']

        for btn in vision_result.buttons:
            btn_text_lower = btn.text.lower()
            for keyword in apply_keywords:
                if keyword.lower() in btn_text_lower:
                    return btn

        return None

    def find_close_button(self, vision_result: VisionResult) -> Optional[UIElement]:
        """找到关闭按钮"""
        close_keywords = ['关闭', 'close', '×', 'cancel', '取消', '×']

        for btn in vision_result.buttons:
            btn_text_lower = btn.text.lower()
            for keyword in close_keywords:
                if keyword.lower() in btn_text_lower:
                    return btn

        return None

    def find_login_button(self, vision_result: VisionResult) -> Optional[UIElement]:
        """找到登录按钮"""
        login_keywords = ['登录', 'login', 'sign in', '注册', 'register']

        for btn in vision_result.buttons:
            btn_text_lower = btn.text.lower()
            for keyword in login_keywords:
                if keyword.lower() in btn_text_lower:
                    return btn

        return None


class DoubaoClient:
    """
    Doubao API 客户端
    实际使用时通过配置获取 API key
    """

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url

    async def vision(self, model: str, image: str, prompt: str) -> Dict:
        """
        调用视觉模型

        Args:
            model: 模型名称
            image: base64编码的图片
            prompt: 分析提示词

        Returns:
            API响应
        """
        import httpx

        # 构建请求
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}}
                    ]
                }
            ]
        }

        # 发送请求
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30.0
            )

            response.raise_for_status()
            return response.json()
