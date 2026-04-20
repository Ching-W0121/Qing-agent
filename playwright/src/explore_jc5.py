import asyncio
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def explore_jobcopilot():
    from playwright.async_api import async_playwright

    with open('C:/Users/TR/Desktop/1.txt', 'r') as f:
        cookies = json.load(f)

    chrome_path = 'C:/Users/TR/AppData/Local/Google/Chrome/User Data'

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=chrome_path,
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )

        page = await context.new_page()

        for cookie in cookies:
            try:
                await context.add_cookies([{
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    'domain': cookie.get('domain', '.app.jobcopilot.com'),
                    'path': cookie.get('path', '/'),
                }])
            except:
                pass

        # 访问 Copilot 主页面
        await page.goto('https://app.jobcopilot.com/copilot', wait_until='domcontentloaded')
        await asyncio.sleep(3)

        # 点击 "How copilot works" 按钮
        try:
            how_btn = page.get_by_text("How copilot works")
            await how_btn.click()
            await asyncio.sleep(2)
            print('Clicked How copilot works')
        except Exception as e:
            print(f'Could not click: {e}')

        # 获取完整内容
        content = await page.inner_text('body')
        print('=== Page Content ===')
        print(content[:5000])

        await context.close()

asyncio.run(explore_jobcopilot())
