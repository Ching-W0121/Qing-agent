"""
诊断测试 - 检查搜索框的事件绑定
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
    print("\n[2] 检查搜索相关元素...")
    search_input = await page.query_selector('input[placeholder*="搜索"]')
    if search_input:
        # 检查是否有data-*属性或事件
        input_html = await search_input.evaluate('el => el.outerHTML')
        print(f"    输入框HTML: {input_html[:200]}...")

        # 检查父容器
        parent = await search_input.evaluate_handle('el => el.parentElement.parentElement')
        parent_html = await parent.evaluate('el => el.outerHTML')
        print(f"    父容器HTML: {parent_html[:300]}...")

    # 找home-search相关的按钮
    print("\n[3] 找home-search中的按钮...")
    buttons = await page.query_selector_all('.home-search button')
    print(f"    home-search中按钮数量: {len(buttons)}")
    for btn in buttons[:3]:
        btn_text = await btn.inner_text()
        print(f"    按钮: '{btn_text}'")

    # 找所有搜索相关的a标签
    print("\n[4] 找搜索相关链接...")
    links = await page.query_selector_all('a[href*="sou"], a[href*="search"], a[href*="jobs"]')
    for link in links[:5]:
        href = await link.get_attribute('href')
        link_text = await link.inner_text()
        print(f"    链接: {href} - '{link_text}'")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test())