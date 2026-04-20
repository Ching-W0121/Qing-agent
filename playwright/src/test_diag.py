"""
诊断测试 - 找出搜索流程问题
"""

import asyncio
import json
import sys
import re
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
    print(f"    URL: {page.url}")

    # 找搜索框
    print("\n[2] 找搜索框...")
    for selector in ['#keywordInput', 'input[placeholder*="搜索"]', '#sugInput']:
        elem = await page.query_selector(selector)
        if elem and await elem.is_visible():
            print(f"    找到: {selector}")
            # 输入关键词
            await elem.click()
            await asyncio.sleep(0.2)
            await elem.fill('品牌策划')
            print("    已输入: 品牌策划")
            await asyncio.sleep(0.5)

            # 获取输入框的值
            val = await elem.input_value()
            print(f"    输入框值: {val}")

            # 按Enter
            print("\n[3] 按Enter...")
            await elem.press('Enter')
            await asyncio.sleep(3)
            print(f"    URL: {page.url}")

            # 检查页面内容
            html = await page.content()
            if 'jobdetail' in html.lower():
                print("    页面包含jobdetail")
            else:
                print("    页面不包含jobdetail")
                # 打印body前500字符
                body = await page.inner_text('body')
                print(f"    body内容: {body[:300]}...")

            break

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test())