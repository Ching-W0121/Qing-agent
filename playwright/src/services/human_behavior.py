"""
V3.4 Human Behavior Simulator
人类行为模拟器 - 模拟真实用户操作行为
"""

import random
import asyncio
from typing import Optional, Tuple

class HumanBehaviorSimulator:
    """
    人类行为模拟器
    通过模拟真实用户行为降低反爬检测
    """

    def __init__(self):
        self.enabled = True
        # 滚动配置
        self.scroll_min_pauses = 3
        self.scroll_max_pauses = 6
        self.scroll_min_distance = 100
        self.scroll_max_distance = 500
        self.scroll_pause_min = 0.5
        self.scroll_pause_max = 1.5
        # 鼠标移动配置
        self.mouse_min_steps = 8
        self.mouse_max_steps = 15
        self.mouse_step_min_delay = 0.02
        self.mouse_step_max_delay = 0.08
        self.mouse_jitter_range = 10
        # 点击延迟
        self.click_pause_min = 0.1
        self.click_pause_max = 0.3
        # 通用延迟
        self.action_delay_min = 1
        self.action_delay_max = 3

    async def human_scroll(self, page, direction: str = "down") -> None:
        """
        模拟人类滚动: 不是直线，而是有停顿的曲线

        Args:
            page: Playwright page对象
            direction: "up" 或 "down"
        """
        if not self.enabled:
            await page.evaluate(f"window.scrollBy(0, {random.randint(200, 500)})")
            return

        pause_count = random.randint(self.scroll_min_pauses, self.scroll_max_pauses)
        direction_multiplier = 1 if direction == "down" else -1

        for _ in range(pause_count):
            distance = random.randint(
                self.scroll_min_distance,
                self.scroll_max_distance
            ) * direction_multiplier

            await page.evaluate(f"""
                window.scrollBy(0, {distance})
            """)

            # 随机停顿
            pause_time = random.uniform(
                self.scroll_pause_min,
                self.scroll_pause_max
            )
            await asyncio.sleep(pause_time)

    async def human_scroll_to_element(self, page, selector: str, timeout: float = 5) -> bool:
        """
        滚动到元素位置（人类行为）

        Args:
            page: Playwright page对象
            selector: 元素选择器
            timeout: 超时时间

        Returns:
            bool: 是否成功
        """
        try:
            element = await page.wait_for_selector(selector, timeout=timeout * 1000)
            if not element:
                return False

            # 人类行为滚动
            await self.human_scroll(page, "down")
            await asyncio.sleep(random.uniform(0.3, 0.7))
            await self.human_scroll(page, "up")

            return True
        except Exception as e:
            print(f"[HumanBehavior] 滚动到元素失败: {e}")
            return False

    async def human_mouse_move(self, page, target_x: int, target_y: int) -> None:
        """
        模拟人类鼠标移动: 曲线路径，带抖动

        Args:
            page: Playwright page对象
            target_x: 目标X坐标
            target_y: 目标Y坐标
        """
        if not self.enabled:
            await page.mouse.move(target_x, target_y)
            return

        # 随机起点偏移
        start_x = target_x + random.randint(-50, 50)
        start_y = target_y + random.randint(-50, 50)
        await page.mouse.move(start_x, start_y)

        # 计算步数
        steps = random.randint(self.mouse_min_steps, self.mouse_max_steps)

        # 使用贝塞尔曲线生成平滑路径
        import math
        for i in range(steps):
            ratio = (i + 1) / steps
            # 二阶贝塞尔曲线
            t = ratio
            # 控制点
            cp_x = (start_x + target_x) / 2 + random.randint(-30, 30)
            cp_y = (start_y + target_y) / 2 + random.randint(-30, 30)

            # 贝塞尔公式
            x = int((1-t)**2 * start_x + 2*(1-t)*t * cp_x + t**2 * target_x)
            y = int((1-t)**2 * start_y + 2*(1-t)*t * cp_y + t**2 * target_y)

            # 添加抖动
            x += random.randint(-self.mouse_jitter_range, self.mouse_jitter_range)
            y += random.randint(-self.mouse_jitter_range, self.mouse_jitter_range)

            await page.mouse.move(x, y)

            # 随机延迟
            delay = random.uniform(
                self.mouse_step_min_delay,
                self.mouse_step_max_delay
            )
            await asyncio.sleep(delay)

    async def human_click(self, page, x: int, y: int, button: str = "left") -> None:
        """
        人类点击: 移动到目标 + 小停顿 + 点击

        Args:
            page: Playwright page对象
            x: 点击X坐标
            y: 点击Y坐标
            button: 鼠标按钮 ("left", "right", "middle")
        """
        # 先移动到目标（人类行为）
        await self.human_mouse_move(page, x, y)

        # 小停顿
        await asyncio.sleep(random.uniform(self.click_pause_min, self.click_pause_max))

        # 点击
        await page.mouse.click(x, y, button=button)

    async def human_double_click(self, page, x: int, y: int) -> None:
        """人类双击"""
        await self.human_click(page, x, y)
        await asyncio.sleep(random.uniform(0.1, 0.2))
        await page.mouse.click(x, y, button="left")

    async def human_right_click(self, page, x: int, y: int) -> None:
        """人类右键点击"""
        await self.human_mouse_move(page, x, y)
        await asyncio.sleep(random.uniform(self.click_pause_min, self.click_pause_max))
        await page.mouse.click(x, y, button="right")

    async def human_hover(self, page, x: int, y: int, duration: float = None) -> None:
        """
        人类悬停

        Args:
            page: Playwright page对象
            x: 悬停X坐标
            y: 悬停Y坐标
            duration: 悬停持续时间（秒）
        """
        await self.human_mouse_move(page, x, y)
        if duration:
            await asyncio.sleep(duration)
        else:
            await asyncio.sleep(random.uniform(0.3, 0.8))

    async def human_slider_drag(self, page, slider_selector: str, target_distance: int = None) -> bool:
        """
        模拟人类滑块拖动行为

        Args:
            page: Playwright page对象
            slider_selector: 滑块选择器
            target_distance: 目标拖动距离，如果为None则自动计算

        Returns:
            bool: 是否成功完成滑块验证
        """
        try:
            # 找到滑块元素
            slider = await page.query_selector(slider_selector)
            if not slider:
                print(f"[HumanBehavior] 未找到滑块元素: {slider_selector}")
                return False

            # 获取滑块位置
            bbox = await slider.bounding_box()
            if not bbox:
                print(f"[HumanBehavior] 无法获取滑块位置")
                return False

            # 滑块中心点
            slider_x = bbox['x'] + bbox['width'] / 2
            slider_y = bbox['y'] + bbox['height'] / 2

            # 如果没有指定距离，尝试自动计算
            if target_distance is None:
                # 尝试找缺口位置或背景图
                # 这里简化处理，假设需要拖动到右侧70%的位置
                target_distance = int(bbox['width'] * 3)

            # 目标位置
            target_x = slider_x + target_distance
            target_y = slider_y

            # 模拟人类拖动：按下 -> 移动 -> 释放
            # 按下
            await page.mouse.move(slider_x, slider_y)
            await asyncio.sleep(random.uniform(0.1, 0.2))
            await page.mouse.down()
            await asyncio.sleep(random.uniform(0.05, 0.15))

            # 人类拖动路径：分段移动，有加速减速
            steps = random.randint(15, 25)
            for i in range(steps):
                # 使用缓动函数：先慢后快再慢
                progress = (i + 1) / steps
                # 缓出效果
                ease_progress = 1 - (1 - progress) ** 2

                current_x = slider_x + (target_x - slider_x) * ease_progress
                current_y = slider_y + random.randint(-3, 3)  # 添加轻微Y轴抖动

                await page.mouse.move(int(current_x), int(current_y))

                # 移动延迟：开始和结束慢，中间快
                if progress < 0.2 or progress > 0.8:
                    delay = random.uniform(0.03, 0.08)
                else:
                    delay = random.uniform(0.015, 0.04)
                await asyncio.sleep(delay)

            # 释放
            await page.mouse.up()
            await asyncio.sleep(random.uniform(0.3, 0.5))

            print(f"[HumanBehavior] 滑块拖动完成，距离: {target_distance}")
            return True

        except Exception as e:
            print(f"[HumanBehavior] 滑块拖动失败: {e}")
            return False

    async def detect_and_solve_slider(self, page) -> bool:
        """
        检测页面是否有滑块验证并尝试自动解决

        Args:
            page: Playwright page对象

        Returns:
            bool: 是否解决了滑块验证
        """
        try:
            # 滑块验证码选择器 (51job 等平台)
            slider_selectors = [
                # 51job 滑块验证码
                '.nc_wrapper .slider',
                '.geetest_slider',
                '.geetest_slider_knob',
                '[class*="slider"] [class*="track"]',
                '[class*="slider"] [class*="button"]',
                # 通用
                '[class*="slider"] [class*="btn"]',
                '[class*="slider"] a',
                '[class*="geetest"] [class*="slider"]',
                '[class*="nc_wrapper"] [class*="slider"]',
                'div[class*="slider"]',
            ]

            for selector in slider_selectors:
                slider = await page.query_selector(selector)
                if slider:
                    is_visible = await slider.is_visible()
                    if is_visible:
                        print(f"[HumanBehavior] 检测到滑块验证码")
                        return await self.human_slider_drag(page, selector)

            return False

        except Exception as e:
            print(f"[HumanBehavior] 滑块检测失败: {e}")
            return False

    async def random_action_delay(self) -> None:
        """随机动作间隔延迟"""
        delay = random.uniform(self.action_delay_min, self.action_delay_max)
        await asyncio.sleep(delay)

    async def type_like_human(self, page, selector: str, text: str,
                              min_char_delay: float = 0.05,
                              max_char_delay: float = 0.15) -> None:
        """
        人类打字行为

        Args:
            page: Playwright page对象
            selector: 输入框选择器
            text: 要输入的文本
            min_char_delay: 最小字符延迟
            max_char_delay: 最大字符延迟
        """
        element = await page.query_selector(selector)
        if not element:
            return

        await element.click()
        await asyncio.sleep(random.uniform(0.1, 0.3))

        for char in text:
            await element.type(char)
            delay = random.uniform(min_char_delay, max_char_delay)
            await asyncio.sleep(delay)


# 全局单例
human_behavior = HumanBehaviorSimulator()