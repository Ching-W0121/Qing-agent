"""
Playwright 浏览器测试脚本
使用系统 Edge/Chrome 浏览器
"""

import asyncio
import sys
from playwright.async_api import async_playwright

# 设置 UTF-8 输出
sys.stdout.reconfigure(encoding='utf-8')

async def test_browser():
    print("=" * 50)
    print("Playwright Browser Test")
    print("=" * 50)

    async with async_playwright() as p:
        # 尝试 Edge
        try:
            print("\n[1] Trying to start Edge browser...")
            browser = await p.chromium.launch(
                headless=False,
                channel='msedge',
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto('https://www.baidu.com')
            title = await page.title()
            print(f"[OK] Edge started successfully! Page title: {title}")

            # 测试访问智联招聘
            print("\n[2] Testing Zhilian website...")
            await page.goto('https://www.zhaopin.com')
            await page.wait_for_load_state('networkidle')
            title = await page.title()
            print(f"[OK] Zhilian loaded! Page title: {title}")

            await browser.close()
            return True

        except Exception as edge_error:
            print(f"[FAIL] Edge failed: {edge_error}")

            # 尝试 Chrome
            try:
                print("\n[3] Trying to start Chrome browser...")
                browser = await p.chromium.launch(
                    headless=False,
                    channel='chrome',
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto('https://www.baidu.com')
                title = await page.title()
                print(f"[OK] Chrome started successfully! Page title: {title}")

                await browser.close()
                return True

            except Exception as chrome_error:
                print(f"[FAIL] Chrome failed: {chrome_error}")
                return False

async def main():
    success = await test_browser()
    if success:
        print("\n" + "=" * 50)
        print("Browser test SUCCESS! Ready for web testing")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("Browser test FAILED! Please check browser installation")
        print("=" * 50)

if __name__ == '__main__':
    asyncio.run(main())
