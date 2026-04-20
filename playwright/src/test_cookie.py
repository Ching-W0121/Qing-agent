"""
测试Cookie是否正确加载
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_cookie():
    print("=" * 60)
    print("测试Cookie加载")
    print("=" * 60)

    # 读取Cookie
    cookies_file = Path('C:/Users/TR/Desktop/1.txt')
    print(f"\n[1] 读取Cookie文件: {cookies_file}")

    with open(cookies_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    print(f"    Cookie数量: {len(cookies)}")

    # 显示前3个Cookie
    for i, c in enumerate(cookies[:3], 1):
        print(f"    {i}. {c.get('name', 'N/A')} = {c.get('value', 'N/A')[:20]}...")

    # 修复 sameSite
    for cookie in cookies:
        if cookie.get('sameSite') == 'unspecified':
            cookie['sameSite'] = 'Lax'
            print(f"    修复 sameSite: {cookie['name']}")

    # 启动浏览器
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

    # 设置Cookie
    print(f"\n[2] 设置Cookie到Context...")
    success_count = 0
    for cookie in cookies:
        cookie_copy = {k: v for k, v in cookie.items() if k not in ['id', 'storeId']}
        try:
            await context.add_cookies([cookie_copy])
            success_count += 1
        except Exception as e:
            print(f"    失败: {cookie_copy.get('name', 'N/A')} - {e}")

    print(f"    成功设置: {success_count}/{len(cookies)}")

    # 打开官网
    print(f"\n[3] 打开官网...")
    page = await context.new_page()
    await page.goto('https://www.zhaopin.com/', wait_until='domcontentloaded')
    await asyncio.sleep(3)

    # 截图
    await page.screenshot(path='test_cookie_home.png', full_page=True)
    print(f"    截图: test_cookie_home.png")

    # 检查登录状态
    try:
        login_name = await page.inner_text('.user-name, .login-name')
        print(f"    已登录: {login_name}")
    except:
        print(f"    未登录")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test_cookie())