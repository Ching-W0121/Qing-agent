"""
测试正确的搜索流程
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_flow():
    print("=" * 60)
    print("测试正确搜索流程")
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

    # 1. 打开官网
    print("\n[1] 打开官网...")
    await page.goto('https://www.zhaopin.com/', wait_until='domcontentloaded')
    await asyncio.sleep(3)

    # 2. 找搜索框
    print("\n[2] 查找搜索框...")
    search_selectors = ['#keywordInput', 'input[name="keyword"]', 'input.search-input', '#sugInput']
    search_input = None
    for selector in search_selectors:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                print(f"    找到: {selector}")
                search_input = elem
                break
        except:
            continue

    if not search_input:
        print("    未找到搜索框，尝试截图查看...")
        await page.screenshot(path='test_no_search.png', full_page=True)
        await browser.close()
        return

    # 3. 输入关键词
    print("\n[3] 输入关键词...")
    await search_input.fill('品牌策划')
    await asyncio.sleep(0.5)

    # 4. 点击搜索
    print("\n[4] 点击搜索...")
    btn_selectors = ['#searchButton', 'button.search-btn', 'button:has-text("搜索")']
    for selector in btn_selectors:
        try:
            btn = await page.query_selector(selector)
            if btn and await btn.is_visible():
                await btn.click()
                print(f"    点击: {selector}")
                break
        except:
            continue

    # 5. 等待结果
    print("\n[5] 等待搜索结果...")
    await asyncio.sleep(5)

    # 截图
    await page.screenshot(path='test_search_result.png', full_page=True)
    print("    截图: test_search_result.png")

    # 6. 提取职位
    print("\n[6] 提取职位...")
    body_text = await page.inner_text('body')
    print(f"    页面内容长度: {len(body_text)}")

    # 提取URL测试
    import re
    job_pattern = r'href=["\']([^"\']*jobdetail[^"\']*\.htm[^"\']*)["\']'
    job_urls = re.findall(job_pattern, await page.content(), re.IGNORECASE)
    print(f"    找到 {len(job_urls)} 个 jobdetail URL")

    for i, url in enumerate(job_urls[:3], 1):
        print(f"    {i}. {url[:100]}...")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test_flow())