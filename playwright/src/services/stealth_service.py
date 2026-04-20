"""
V3.4 Stealth Service
反检测服务 - 模拟真实浏览器指纹
"""

import random
import asyncio
from typing import List, Optional, Dict, Any

# 真实User-Agent列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
]

class StealthConfig:
    """Stealth模式配置"""

    def __init__(self):
        self.enabled = True
        self.remove_webdriver = True
        self.randomize_ua = True
        self.randomize_canvas = True
        self.randomize_webgl = True
        self.randomize_audio = True
        self.human_scroll = True
        self.human_mouse = True
        self.random_delay_min = 1
        self.random_delay_max = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "remove_webdriver": self.remove_webdriver,
            "randomize_ua": self.randomize_ua,
            "randomize_canvas": self.randomize_canvas,
            "randomize_webgl": self.randomize_webgl,
            "randomize_audio": self.randomize_audio,
            "human_scroll": self.human_scroll,
            "human_mouse": self.human_mouse,
            "random_delay_min": self.random_delay_min,
            "random_delay_max": self.random_delay_max
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StealthConfig':
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


class StealthService:
    """
    Stealth模式核心服务
    提供浏览器指纹随机化和反检测功能
    """

    def __init__(self, config: StealthConfig = None):
        self.config = config or StealthConfig()
        self._ua_cache = None

    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        return random.choice(USER_AGENTS)

    def get_stealth_browser_args(self) -> List[str]:
        """
        获取Stealth模式浏览器参数
        """
        args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--window-size=1920,1080',
        ]

        if self.config.enabled:
            # 添加Stealth参数
            args.extend([
                '--disable-blink-features=AutomationControlled',
            ])

        return args

    async def apply_stealth_to_page(self, page) -> None:
        """
        对页面应用Stealth配置
        """
        if not self.config.enabled:
            return

        # 1. 移除webdriver属性
        if self.config.remove_webdriver:
            await self._remove_webdriver_properties(page)

        # 2. 随机化Canvas
        if self.config.randomize_canvas:
            await self._randomize_canvas(page)

        # 3. 随机化WebGL
        if self.config.randomize_webgl:
            await self._randomize_webgl(page)

        # 4. 随机化Audio
        if self.config.randomize_audio:
            await self._randomize_audio(page)

        # 5. 修改navigator信息
        await self._patch_navigator(page)

    async def _remove_webdriver_properties(self, page) -> None:
        """移除webdriver相关属性"""
        await page.evaluate("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });

            // 移除自动化相关属性
            delete window.cdc_adoQpoasnfaoPpfpelxm pdof;
            delete window.$cdc_asdjflasutopfhvcWlcPtpFoc;
        """)

    async def _patch_navigator(self, page) -> None:
        """修补navigator信息"""
        ua = self.get_random_user_agent()

        await page.evaluate(f"""
            Object.defineProperty(navigator, 'userAgent', {{
                get: () => '{ua}',
                configurable: true
            }});

            Object.defineProperty(navigator, 'plugins', {{
                get: () => [
                    {{ name: 'Chrome PDF Plugin' }},
                    {{ name: 'Chrome PDF Viewer' }},
                    {{ name: 'Native Client' }}
                ],
                configurable: true
            }});

            Object.defineProperty(navigator, 'languages', {{
                get: () => ['zh-CN', 'zh', 'en-US', 'en'],
                configurable: true
            }});
        """)

    async def _randomize_canvas(self, page) -> None:
        """随机化Canvas指纹"""
        await page.evaluate("""
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                if (this.width > 0 && this.height > 0) {
                    const context = this.getContext('2d');
                    if (context) {
                        const imageData = context.getImageData(0, 0, this.width, this.height);
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            // 添加随机噪声
                            imageData.data[i] = Math.min(255, imageData.data[i] + Math.floor(Math.random() * 10) - 5);
                            imageData.data[i + 1] = Math.min(255, imageData.data[i + 1] + Math.floor(Math.random() * 10) - 5);
                            imageData.data[i + 2] = Math.min(255, imageData.data[i + 2] + Math.floor(Math.random() * 10) - 5);
                        }
                        context.putImageData(imageData, 0, 0);
                    }
                }
                return originalToDataURL.apply(this, arguments);
            };
        """)

    async def _randomize_webgl(self, page) -> None:
        """随机化WebGL指纹"""
        await page.evaluate("""
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                // 随机化WEBGL_debug_renderer_info
                if (parameter === 37445) {
                    return 'Intel Iris OpenGL Engine';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.apply(this, arguments);
            };
        """)

    async def _randomize_audio(self, page) -> None:
        """随机化Audio指纹"""
        await page.evaluate("""
            const originalCreateDynamicsCompressor = DynamicsCompressor.prototype.createDynamicsCompressor;
            DynamicsCompressor.prototype.createDynamicsCompressor = function() {
                const compressor = originalCreateDynamicsCompressor.apply(this, arguments);
                // 添加随机偏移
                compressor.threshold.value += (Math.random() - 0.5) * 0.1;
                compressor.knee.value += (Math.random() - 0.5) * 0.1;
                return compressor;
            };
        """)

    def get_random_delay(self) -> float:
        """获取随机延迟时间"""
        return random.uniform(self.config.random_delay_min, self.config.random_delay_max)


# 全局单例
stealth_service = StealthService()