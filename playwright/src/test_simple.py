"""
简单测试 - 更长的超时和更少的截图
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
    try:
        await page.goto('https://www.zhaopin.com/', timeout=60000)
        await asyncio.sleep(5)
        print(f"    URL: {page.url}")
        await page.screenshot(path=str(desktop / 's1.png'))
    except Exception as e:
        print(f"    失败: {e}")
        await browser.close()
        return

    print("\n完成 - 截图在桌面")
    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test())