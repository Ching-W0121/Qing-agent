import asyncio
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

async def check_extensions():
    from playwright.async_api import async_playwright

    # 检查已安装的扩展
    ext_paths = [
        'C:/Users/TR/AppData/Local/Google/Chrome/User Data/Default/Extensions',
        os.path.expanduser('~') + '/AppData/Roaming/Opera Software/Opera Stable/Extensions',
    ]

    for path in ext_paths:
        if os.path.exists(path):
            print(f'\\nExtensions in {path}:')
            try:
                for ext in os.listdir(path):
                    ext_json_path = os.path.join(path, ext, 'manifest.json')
                    if os.path.exists(ext_json_path):
                        with open(ext_json_path, 'r', encoding='utf-8') as f:
                            try:
                                manifest = json.load(f)
                                print(f'  - {manifest.get("name", "Unknown")}: v{manifest.get("version", "?")}')
                                print(f'    Description: {manifest.get("description", "")[:100]}')
                            except:
                                pass
            except Exception as e:
                print(f'  Error: {e}')

async def check_chrome_extensions():
    """检查 Chrome 扩展页面"""
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

        # 检查扩展页面
        await page.goto('chrome://extensions', wait_until='domcontentloaded')
        await asyncio.sleep(2)

        extensions = await page.evaluate("""
            () => {
                const items = document.querySelectorAll('extensions-item');
                return Array.from(items).map(item => ({
                    name: item.querySelector('.name')?.innerText,
                    version: item.querySelector('.version')?.innerText,
                    description: item.querySelector('[id$="-description"]')?.innerText
                }));
            }
        """)

        print('\\n=== Chrome Extensions ===')
        print(json.dumps(extensions, ensure_ascii=False, indent=2))

        await context.close()

# 运行
asyncio.run(check_extensions())
asyncio.run(check_chrome_extensions())
