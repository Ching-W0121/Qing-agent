"""
诊断测试 - 找搜索按钮
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
    print(f"    URL: {page.url}")

    # 找搜索按钮
    print("\n[2] 找所有可能的搜索按钮...")
    btn_count = 0
    for selector in [
        '#searchButton', 'button.search-btn', '.search-button',
        '[class*="search"][class*="btn"]', 'button:has-text("搜索")',
        'button:has-text("找职位")', '[class*="search"] button',
        '.header-search button', '.search-btn'
    ]:
        btns = await page.query_selector_all(selector)
        if btns:
            for btn in btns:
                if await btn.is_visible():
                    btn_text = await btn.inner_text()
                    print(f"    {selector}: '{btn_text}'")
                    btn_count += 1

    print(f"\n共找到 {btn_count} 个搜索按钮")

    # 尝试找到输入框和按钮的组合
    print("\n[3] 找表单组合...")
    form_selectors = [
        'form[action*="search"]',
        'form[action*="sou"]',
        '.search-form',
        '[class*="search"][class*="form"]'
    ]
    for selector in form_selectors:
        form = await page.query_selector(selector)
        if form:
            print(f"    找到表单: {selector}")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test())