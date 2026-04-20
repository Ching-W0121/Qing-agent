"""
测试职位详情页打开情况
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def load_cookies():
    cookie_file = Path('C:/Users/TR/Desktop/1.txt')
    with open(cookie_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    return cookies


async def test_job_page():
    print("=" * 60)
    print("测试职位详情页打开情况")
    print("=" * 60)

    # 加载Cookie
    cookies = await load_cookies()
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

    # 先访问智联首页
    print("\n[1] 访问智联首页...")
    await page.goto('https://www.zhaopin.com/', wait_until='domcontentloaded')
    await asyncio.sleep(3)

    # 检查是否已登录
    try:
        login_name = await page.inner_text('.user-name, .login-name')
        print(f"[OK] 已登录: {login_name}")
    except:
        print("[WARN] 未登录")

    # 测试打开一个具体的职位详情页
    test_url = 'https://www.zhaopin.com/job/CC820107150J40799697111.htm'
    print(f"\n[2] 直接打开职位详情页: {test_url}")

    await page.goto(test_url, wait_until='domcontentloaded')
    await asyncio.sleep(3)

    # 获取当前URL
    print(f"    当前URL: {page.url}")

    # 获取页面标题
    try:
        title = await page.title()
        print(f"    页面标题: {title}")
    except:
        print(f"    无法获取标题")

    # 截图
    await page.screenshot(path='test_job_detail.png', full_page=True)
    print(f"    截图已保存: test_job_detail.png")

    # 尝试获取页面主要内容
    try:
        body_text = await page.inner_text('body')
        print(f"    页面文本长度: {len(body_text)} 字符")

        # 检查是否有职位信息
        if '品牌策划' in body_text or '职位' in body_text:
            print(f"    页面包含职位信息")
        else:
            print(f"    页面可能不是职位详情页")

        # 检查是否有验证码/登录提示
        if any(x in body_text for x in ['验证码', '请登录', '登录后', 'captcha', 'Captcha']):
            print(f"    页面包含验证码/登录提示")

    except Exception as e:
        print(f"    获取页面内容失败: {e}")

    # 尝试查找投递按钮
    apply_btn_selectors = [
        '.collect-and-apply__btn',
        '.btn.apply-btn',
        '.summary-planes__action button',
        '.a-button.a--bordered.a--filled',
        'button:has-text("立即投递")',
        'a:has-text("立即投递")'
    ]

    for selector in apply_btn_selectors:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=2000):
                print(f"    找到投递按钮: {selector}")
                break
        except:
            continue
    else:
        print(f"    未找到投递按钮")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test_job_page())