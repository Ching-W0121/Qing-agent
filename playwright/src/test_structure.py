"""
诊断测试 - 检查搜索框的HTML结构
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test():
    cookies_file = Path('C:/Users/TR/Desktop/1.txt')

    with open(cookies_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    for cookie in cookies:
        if cookie.get('sameSite') == 'unspecified':
            cookie['sameSite'] = 'Lax'

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,
        channel='msedge',
        args=['--disable-blink-features=AutomationControlled']
    )

    context = await browser.new_context(viewport={'width': 1920, 'height': 1080})

    for cookie in cookies:
        cookie_copy = {k: v for k, v in cookie.items() if k not in ['id', 'storeId']}
        try:
            await context.add_cookies([cookie_copy])
        except:
            pass

    page = await context.new_page()

    print("[1] 打开官网...")
    await page.goto('https://www.zhaopin.com/', wait_until='domcontentloaded')
    await asyncio.sleep(3)

    # 找到搜索框
    print("\n[2] 分析搜索框结构...")
    search_input = await page.query_selector('input[placeholder*="搜索"]')
    if search_input:
        print("    找到搜索框")

        # 获取父元素
        parent = await search_input.evaluate_handle('el => el.parentElement')
        parent_tag = await parent.evaluate('el => el.tagName')
        print(f"    父元素: {parent_tag}")

        # 获取父元素的类
        parent_class = await parent.evaluate('el => el.className')
        print(f"    父元素类: {parent_class}")

        # 往上找3层
        for i in range(3):
            parent = await parent.evaluate_handle('el => el.parentElement')
            parent_tag = await parent.evaluate('el => el.tagName')
            parent_class = await parent.evaluate('el => el.className')
            print(f"    第{i+1}层父元素: {parent_tag}, class: {parent_class[:50]}...")

        # 检查是否有form
        form = await search_input.evaluate_handle('el => el.closest("form")')
        if form:
            form_action = await form.evaluate('el => el.action')
            print(f"    所在表单action: {form_action}")

            # 检查表单内的按钮
            buttons = await form.evaluate('el => Array.from(el.querySelectorAll("button")).map(b => b.className + ":" + b.innerText)')
            print(f"    表单内按钮: {buttons}")
        else:
            print("    没有找到form")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test())