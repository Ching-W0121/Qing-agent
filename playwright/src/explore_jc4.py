import asyncio
import json
import sys

# 设置 UTF-8 输出
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

        structure = await page.evaluate("""
            () => {
                return {
                    title: document.title,
                    url: window.location.href,
                    headings: Array.from(document.querySelectorAll('h1, h2, h3')).map(h => h.innerText),
                    buttons: Array.from(document.querySelectorAll('button')).map(b => b.innerText.substring(0, 100)),
                    mainContent: document.querySelector('main, #app, #root, .container, body')?.innerText?.substring(0, 5000) || ''
                };
            }
        """)

        print('=== Copilot Page ===')
        # 使用 ASCII safe 方式输出
        print(json.dumps(structure, ensure_ascii=False, indent=2))

        await context.close()

asyncio.run(explore_jobcopilot())
