"""
直接使用正确的URL格式测试投递
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_direct_apply():
    print("=" * 60)
    print("直接测试投递（使用用户提供的URL格式）")
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

    # 用户提供的正确URL格式
    test_url = 'https://www.zhaopin.com/jobdetail/CC665457120J40838395301.htm?refcode=4089&srccode=408901&preactionid=f3e53f46-b339-4f04-acf6-276bc0ad1ffb'

    print(f"\n[1] 打开: {test_url}")
    await page.goto(test_url, wait_until='domcontentloaded', timeout=20000)
    await asyncio.sleep(3)

    print(f"    URL: {page.url}")
    print(f"    标题: {await page.title()}")

    # 检查页面内容
    body_text = await page.inner_text('body')
    print(f"    内容长度: {len(body_text)}")

    if len(body_text) > 1000:
        # 查找投递按钮
        selectors = [
            ('.summary-planes__action button', 'summary-planes'),
            ('.collect-and-apply__btn', 'collect'),
            ('.a-button.a--bordered.a--filled', 'a-button'),
            ('button:has-text("立即投递")', 'text'),
        ]

        for selector, name in selectors:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=1000):
                    btn_text = await btn.inner_text()
                    print(f"\n[2] 找到按钮 [{name}]: {btn_text.strip()}")

                    # 点击投递
                    print(f"\n[3] 点击投递...")
                    await btn.click()
                    await asyncio.sleep(3)

                    # 检查结果
                    result = await page.inner_text('body')
                    if '投递成功' in result or '申请成功' in result:
                        print(f"    结果: 投递成功!")
                    elif '已投递' in result or '已申请' in result:
                        print(f"    结果: 已投递过")
                    else:
                        print(f"    结果: 未知")
                    break
            except Exception as e:
                continue
        else:
            print(f"\n[ERROR] 未找到投递按钮")
    else:
        print(f"\n[ERROR] 页面内容异常，可能需要登录")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test_direct_apply())