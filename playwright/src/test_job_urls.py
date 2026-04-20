"""
测试不同的URL格式打开职位详情页
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def load_cookies():
    cookie_file = Path('C:/Users/TR/Desktop/1.txt')
    with open(cookie_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    return cookies


async def test_url_formats():
    print("=" * 60)
    print("测试不同URL格式打开职位详情页")
    print("=" * 60)

    cookies = await load_cookies()
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

    # 先登录
    print("\n[1] 尝试登录...")
    await page.goto('https://www.zhaopin.com/', wait_until='domcontentloaded')
    await asyncio.sleep(2)

    # 检查登录状态
    try:
        login_name = await page.inner_text('.user-name, .login-name')
        print(f"[OK] 已登录: {login_name}")
    except:
        print("[WARN] 未登录")

    # 不同的URL格式测试
    test_urls = [
        # 标准格式
        'https://www.zhaopin.com/job/CC820107150J40799697111.htm',
        # 带参数格式
        'https://www.zhaopin.com/job/CC820107150J40799697111.htm?utm_source=search',
        # job_detail旧格式
        'https://www.zhaopin.com/job_detail/CC820107150J40799697111.htm',
    ]

    for url in test_urls:
        print(f"\n[2] 测试URL: {url}")
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=10000)
            await asyncio.sleep(2)

            print(f"    实际URL: {page.url}")
            print(f"    页面标题: {await page.title()}")

            # 检查是否显示职位详情
            body_text = await page.inner_text('body')
            if '职位' in body_text and len(body_text) > 100:
                print(f"    页面内容正常 (长度: {len(body_text)})")
            else:
                print(f"    页面内容异常 (长度: {len(body_text)})")

            # 截图
            safe_name = url.split('/')[-1].replace('.htm', '').replace('?', '_')[:30]
            await page.screenshot(path=f'test_{safe_name}.png')
            print(f"    截图: test_{safe_name}.png")

        except Exception as e:
            print(f"    打开失败: {e}")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test_url_formats())