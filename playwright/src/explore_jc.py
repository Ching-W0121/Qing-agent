import asyncio
import json

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

        await page.goto('https://app.jobcopilot.com/copilot', wait_until='domcontentloaded')
        await asyncio.sleep(3)

        # 获取页面结构
        structure = await page.evaluate("""
            () => {
                const body = document.body;
                const structure = {
                    title: document.title,
                    url: window.location.href,
                    headings: Array.from(document.querySelectorAll('h1, h2, h3')).map(h => h.innerText),
                    buttons: Array.from(document.querySelectorAll('button')).map(b => b.innerText.substring(0, 50)),
                    links: Array.from(document.querySelectorAll('a[href]')).map(a => ({text: a.innerText.substring(0, 30), href: a.href})).slice(0, 20),
                    inputs: Array.from(document.querySelectorAll('input')).map(i => ({type: i.type, placeholder: i.placeholder, name: i.name})),
                    mainContent: document.querySelector('main, #app, #root, .container')?.innerText?.substring(0, 1000) || ''
                };
                return structure;
            }
        """)

        print('=== Page Structure ===')
        print(json.dumps(structure, ensure_ascii=False, indent=2))

        await context.close()

asyncio.run(explore_jobcopilot())
