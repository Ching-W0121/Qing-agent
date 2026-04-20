"""
测试搜索和URL提取
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_search():
    print("=" * 60)
    print("测试搜索和URL提取")
    print("=" * 60)

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

    # 正确的搜索页URL格式
    search_url = 'https://www.zhaopin.com/sou/jl765/kw%E5%93%81%E7%89%88%E7%AD%96%E5%88%92/p1'
    print(f"\n[1] 打开搜索页: {search_url}")
    await page.goto(search_url, wait_until='domcontentloaded')
    await asyncio.sleep(5)

    print(f"    URL: {page.url}")
    print(f"    标题: {await page.title()}")

    # 截图
    await page.screenshot(path='test_search_result.png', full_page=True)
    print(f"    截图: test_search_result.png")

    # 获取页面内容
    body_text = await page.inner_text('body')
    print(f"    内容长度: {len(body_text)}")

    if len(body_text) > 1000:
        print(f"    页面加载正常")
    else:
        print(f"    页面内容可能异常")

    # 提取职位链接测试
    import re
    html_content = await page.content()

    # 提取 jobdetail URL
    job_pattern = r'href=["\']([^"\']*jobdetail[^"\']*\.htm[^"\']*)["\']'
    job_urls = re.findall(job_pattern, html_content, re.IGNORECASE)

    print(f"\n[2] 提取到 {len(job_urls)} 个职位详情URL")

    # 显示前5个URL
    for i, url in enumerate(job_urls[:5], 1):
        print(f"    {i}. {url[:100]}...")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test_search())