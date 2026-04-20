"""
测试 - 点击自动完成建议触发搜索
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

    print("[1] 打开官网...")
    await page.goto('https://www.zhaopin.com/', wait_until='domcontentloaded')
    await asyncio.sleep(3)
    print(f"    URL: {page.url}")
    await page.screenshot(path=str(desktop / 't1_home.png'), full_page=True)

    # 检查登录
    try:
        login_name = await page.inner_text('.user-name, .login-name')
        print(f"    已登录: {login_name}")
    except:
        print(f"    未登录")

    # 找到搜索框
    print("\n[2] 找到搜索框...")
    search_input = None
    for selector in ['#keywordInput', 'input[placeholder*="搜索"]', 'input.search-input', '#sugInput']:
        elem = await page.query_selector(selector)
        if elem and await elem.is_visible():
            print(f"    找到: {selector}")
            search_input = elem
            break

    if search_input:
        await search_input.click()
        await asyncio.sleep(0.3)
        await search_input.fill('品牌策划')
        print("    输入: 品牌策划")
        await asyncio.sleep(1)  # 等待自动完成出现
        await page.screenshot(path=str(desktop / 't2_filled.png'), full_page=True)

        # 点击自动完成建议中的第一个选项
        print("\n[3] 点击自动完成建议...")
        suggestion_selectors = [
            '.sug-list li:first-child',
            '.search-sug li:first-child',
            '[class*="sug"] li:first-child',
            '.auto-complete li:first-child'
        ]

        clicked = False
        for selector in suggestion_selectors:
            try:
                suggestion = await page.query_selector(selector)
                if suggestion and await suggestion.is_visible():
                    await suggestion.click()
                    print(f"    点击: {selector}")
                    clicked = True
                    break
            except:
                continue

        if not clicked:
            # 如果没有找到建议，尝试按Enter
            print("    未找到建议，按Enter")
            await search_input.press('Enter')

        # 等待搜索结果
        await asyncio.sleep(5)
        print(f"\n[4] 当前URL: {page.url}")
        await page.screenshot(path=str(desktop / 't3_after_search.png'), full_page=True)

        body_text = await page.inner_text('body')
        print(f"    内容长度: {len(body_text)}")

        # 检查URL是否变化
        if 'sou.zhaopin.com' in page.url or '/sou/' in page.url:
            print(f"    搜索成功，跳转到了搜索页")
        else:
            print(f"    URL未变化，可能搜索失败")

        # 提取URL
        print("\n[5] 提取URL...")
        html = await page.content()
        job_urls = re.findall(r'href=["\']([^"\']*jobdetail[^"\']*\.htm[^"\']*)["\']', html, re.IGNORECASE)
        print(f"    jobdetail URLs: {len(job_urls)}")

        if job_urls:
            print(f"    示例: {job_urls[0][:100]}...")

            # 进入第一个职位
            print("\n[6] 进入职位详情...")
            first_url = job_urls[0]
            await page.goto(first_url, wait_until='domcontentloaded')
            await asyncio.sleep(3)
            await page.screenshot(path=str(desktop / 't4_job_detail.png'), full_page=True)
            print(f"    标题: {await page.title()}")

            # 查找投递按钮
            print("\n[7] 查找投递按钮...")
            for selector in ['.summary-planes__action button', '.collect-and-apply__btn', 'button:has-text("立即投递")']:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    btn_text = await btn.inner_text()
                    print(f"    找到: {selector} - '{btn_text}'")
                    await btn.click(timeout=5000)
                    await asyncio.sleep(3)
                    await page.screenshot(path=str(desktop / 't5_result.png'), full_page=True)
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

    print("\n完成!")
    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test())