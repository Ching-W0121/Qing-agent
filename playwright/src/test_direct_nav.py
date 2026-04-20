"""
诊断测试 - 直接导航到搜索URL
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

    # 直接导航到搜索结果页
    print("[1] 直接导航到搜索URL...")
    search_url = 'https://www.zhaopin.com/sou/jl765/kw品牌策划/p1'
    print(f"    URL: {search_url}")
    await page.goto(search_url, wait_until='domcontentloaded')
    await asyncio.sleep(5)
    print(f"    实际URL: {page.url}")
    print(f"    标题: {await page.title()}")

    body = await page.inner_text('body')
    print(f"    内容长度: {len(body)}")

    # 提取jobdetail URL
    html = await page.content()
    job_urls = re.findall(r'href=["\']([^"\']*jobdetail[^"\']*\.htm[^"\']*)["\']', html, re.IGNORECASE)
    print(f"    jobdetail URLs: {len(job_urls)}")

    if job_urls:
        print(f"    示例: {job_urls[0][:80]}...")

        # 进入第一个
        print("\n[2] 进入第一个职位详情...")
        first_url = job_urls[0]
        await page.goto(first_url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        print(f"    标题: {await page.title()}")

        # 找投递按钮
        print("\n[3] 找投递按钮...")
        for selector in ['.summary-planes__action button', '.collect-and-apply__btn', 'button:has-text("立即投递")']:
            btn = await page.query_selector(selector)
            if btn and await btn.is_visible():
                btn_text = await btn.inner_text()
                print(f"    找到: {selector} - '{btn_text}'")
                await btn.click(timeout=5000)
                await asyncio.sleep(3)
                result = await page.inner_text('body')
                if '投递成功' in result:
                    print(f"    结果: 投递成功!")
                elif '已投递' in result:
                    print(f"    结果: 已投递过")
                else:
                    print(f"    结果: 未知")
                break
    else:
        print("    没有找到jobdetail URL")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test())