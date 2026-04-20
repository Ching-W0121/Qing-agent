"""
测试 - 使用键盘方向键选择建议
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
    await page.screenshot(path=str(desktop / 'k1_home.png'))

    # 检查登录
    try:
        login_name = await page.inner_text('.user-name, .login-name')
        print(f"    已登录: {login_name}")
    except:
        print(f"    未登录")

    # 找到搜索框
    print("\n[2] 找搜索框...")
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
        await asyncio.sleep(1)
        await page.screenshot(path=str(desktop / 'k2_filled.png'))

        # 按下方向键选择建议
        print("\n[3] 按方向键选择...")
        await search_input.press('ArrowDown')
        await asyncio.sleep(0.3)
        await page.screenshot(path=str(desktop / 'k3_arrow.png'))

        # 按Enter确认
        print("\n[4] 按Enter确认...")
        await search_input.press('Enter')
        await asyncio.sleep(5)
        print(f"    URL: {page.url}")
        await page.screenshot(path=str(desktop / 'k4_after_enter.png'))

        body_text = await page.inner_text('body')
        print(f"    内容长度: {len(body_text)}")

        # 提取URL
        html = await page.content()
        job_urls = re.findall(r'href=["\']([^"\']*jobdetail[^"\']*\.htm[^"\']*)["\']', html, re.IGNORECASE)
        print(f"    jobdetail URLs: {len(job_urls)}")

        if job_urls:
            print(f"\n[5] 进入第一个职位...")
            first_url = job_urls[0]
            if '/job/' in first_url and 'jobdetail' not in first_url:
                first_url = first_url.replace('/job/', '/jobdetail/')
            print(f"    URL: {first_url[:80]}...")
            await page.goto(first_url, wait_until='domcontentloaded')
            await asyncio.sleep(3)
            await page.screenshot(path=str(desktop / 'k5_detail.png'))
            print(f"    标题: {await page.title()}")

            # 查找投递按钮
            print("\n[6] 查找投递按钮...")
            for selector in ['.summary-planes__action button', '.collect-and-apply__btn', 'button:has-text("立即投递")']:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    btn_text = await btn.inner_text()
                    print(f"    找到: {selector} - '{btn_text}'")
                    await btn.click(timeout=5000)
                    await asyncio.sleep(3)
                    await page.screenshot(path=str(desktop / 'k6_result.png'))
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