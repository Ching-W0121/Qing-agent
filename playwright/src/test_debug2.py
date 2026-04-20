"""
测试 - 检查搜索后URL变化
"""

import asyncio
import json
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test():
    desktop = Path('C:/Users/TR/Desktop')
    cookies_file = desktop / '1.txt'

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

    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    )

    for cookie in cookies:
        cookie_copy = {k: v for k, v in cookie.items() if k not in ['id', 'storeId']}
        try:
            await context.add_cookies([cookie_copy])
        except:
            pass

    page = await context.new_page()

    # 打开官网
    print("[1] 打开官网...")
    await page.goto('https://www.zhaopin.com/', wait_until='domcontentloaded')
    await asyncio.sleep(3)
    print(f"    URL: {page.url}")
    await page.screenshot(path=str(desktop / 'debug_step1_home.png'), full_page=True)

    # 检查登录
    try:
        login_name = await page.inner_text('.user-name, .login-name')
        print(f"    已登录: {login_name}")
    except:
        print(f"    未登录")

    # 找到搜索框
    print("\n[2] 找搜索框...")
    search_input = None
    for selector in ['#keywordInput', 'input[placeholder*="搜索"]', 'input.search-input']:
        elem = await page.query_selector(selector)
        if elem and await elem.is_visible():
            print(f"    找到: {selector}")
            search_input = elem
            break

    if search_input:
        await search_input.fill('品牌策划')
        print("    输入: 品牌策划")

        # 点击搜索
        print("\n[3] 点击搜索...")
        for selector in ['#searchButton', 'button.search-btn', 'button:has-text("搜索")']:
            btn = await page.query_selector(selector)
            if btn and await btn.is_visible():
                await btn.click()
                print(f"    点击: {selector}")
                break

        # 等待
        await asyncio.sleep(5)
        print(f"\n[4] 搜索后URL: {page.url}")
        await page.screenshot(path=str(desktop / 'debug_step2_after_search.png'), full_page=True)

        body_text = await page.inner_text('body')
        print(f"    内容长度: {len(body_text)}")

        # 尝试提取所有URL
        print("\n[5] 提取URL...")
        html = await page.content()

        # 查找各种URL模式
        patterns = [
            (r'href=["\']([^"\']*jobdetail[^"\']*\.htm[^"\']*)["\']', 'jobdetail'),
            (r'href=["\']([^"\']*/job/[^"\']*\.htm[^"\']*)["\']', '/job/'),
            (r'href=["\']([^"\']*zhaopin\.com[^"\']*)["\']', 'zhaopin'),
        ]

        for pattern, name in patterns:
            urls = re.findall(pattern, html, re.IGNORECASE)
            print(f"    {name}: 找到 {len(urls)} 个")
            if urls:
                print(f"    示例: {urls[0][:100]}...")

    print(f"\n截图保存在桌面")
    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test())