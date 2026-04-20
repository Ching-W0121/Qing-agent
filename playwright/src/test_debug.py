"""
完整流程截图调试 - 每一步都截图保存到桌面
"""

import asyncio
import json
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def debug_flow():
    print("=" * 60)
    print("完整流程截图调试")
    print("=" * 60)

    # 桌面路径
    desktop = Path('C:/Users/TR/Desktop')
    screenshot_dir = desktop / 'debug_screenshots'
    screenshot_dir.mkdir(exist_ok=True)

    cookies_file = desktop / '1.txt'
    print(f"\n[1] 读取Cookie: {cookies_file}")

    with open(cookies_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    print(f"    Cookie数量: {len(cookies)}")

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

    # 设置Cookie
    print(f"\n[2] 设置Cookie...")
    for cookie in cookies:
        cookie_copy = {k: v for k, v in cookie.items() if k not in ['id', 'storeId']}
        try:
            await context.add_cookies([cookie_copy])
        except Exception as e:
            print(f"    失败: {cookie_copy.get('name')} - {e}")
    print(f"    完成")

    page = await context.new_page()
    step = [0]  # 使用列表以便在内部函数修改

    async def save_screenshot(name):
        step[0] += 1
        filename = screenshot_dir / f"step{step[0]:02d}_{name}.png"
        await page.screenshot(path=str(filename), full_page=True)
        print(f"    截图: {filename.name}")
        return filename

    # ========== 步骤1: 打开官网 ==========
    print(f"\n[3] 打开官网...")
    await page.goto('https://www.zhaopin.com/', wait_until='domcontentloaded')
    await asyncio.sleep(3)
    await save_screenshot('01_homepage')

    # 检查是否登录
    try:
        login_name = await page.inner_text('.user-name, .login-name')
        print(f"    已登录: {login_name}")
    except:
        print(f"    未登录")

    # ========== 步骤2: 查找搜索框 ==========
    print(f"\n[4] 查找搜索框...")
    search_input = None
    search_selectors = [
        '#keywordInput',
        'input[name="keyword"]',
        'input.search-input',
        'input[placeholder*="搜索"]',
        'input[placeholder*="职位"]',
        '#sugInput',
        '.search-input input',
        'input#kwd-input'
    ]

    for selector in search_selectors:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                print(f"    找到: {selector}")
                search_input = elem
                break
        except:
            continue

    if not search_input:
        print(f"    未找到搜索框，尝试点击搜索图标")
        icon_selectors = ['.search-icon', '.header-search a', '[class*="search-icon"]', 'a.search']
        for icon_sel in icon_selectors:
            try:
                icon = await page.query_selector(icon_sel)
                if icon and await icon.is_visible():
                    await icon.click()
                    await asyncio.sleep(1)
                    await save_screenshot('02_after_click_search_icon')
                    for selector in search_selectors:
                        elem = await page.query_selector(selector)
                        if elem and await elem.is_visible():
                            print(f"    点击图标后找到: {selector}")
                            search_input = elem
                            break
                    if search_input:
                        break
            except:
                continue

    if not search_input:
        print(f"    仍然未找到搜索框")
        await save_screenshot('03_no_search_box')
    else:
        await save_screenshot('03_found_search_box')

    # ========== 步骤3: 输入关键词 ==========
    if search_input:
        print(f"\n[5] 输入关键词...")
        await search_input.fill('品牌策划')
        await asyncio.sleep(0.5)
        await save_screenshot('04_keyword_entered')

    # ========== 步骤4: 点击搜索 ==========
    print(f"\n[6] 点击搜索按钮...")
    btn_selectors = [
        '#searchButton',
        'button.search-btn',
        '.search-button',
        '[class*="search"][class*="btn"]',
        'button:has-text("搜索")',
        'button:has-text("找职位")'
    ]

    for selector in btn_selectors:
        try:
            btn = await page.query_selector(selector)
            if btn and await btn.is_visible():
                await btn.click()
                print(f"    点击: {selector}")
                break
        except:
            continue

    await asyncio.sleep(5)
    await save_screenshot('05_after_search_click')

    # ========== 步骤5: 查看搜索结果 ==========
    print(f"\n[7] 查看搜索结果...")
    body_text = await page.inner_text('body')
    print(f"    内容长度: {len(body_text)}")

    if '没有找到' in body_text or '0个职位' in body_text:
        print(f"    警告: 没有找到相关职位")
    else:
        print(f"    有搜索结果")

    # ========== 步骤6: 提取URL ==========
    print(f"\n[8] 提取职位URL...")
    job_pattern = r'href=["\']([^"\']*jobdetail[^"\']*\.htm[^"\']*)["\']'
    html_content = await page.content()
    job_urls = re.findall(job_pattern, html_content, re.IGNORECASE)
    print(f"    找到 {len(job_urls)} 个URL")

    for i, url in enumerate(job_urls[:3], 1):
        print(f"    {i}. {url[:80]}...")

    if job_urls:
        # ========== 步骤7: 点击第一个职位 ==========
        print(f"\n[9] 进入第一个职位详情...")
        first_url = job_urls[0]
        if '/job/' in first_url and 'jobdetail' not in first_url:
            first_url = first_url.replace('/job/', '/jobdetail/')
        print(f"    URL: {first_url}")
        await page.goto(first_url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        await save_screenshot('06_job_detail_page')

        print(f"    页面标题: {await page.title()}")
        detail_text = await page.inner_text('body')
        print(f"    内容长度: {len(detail_text)}")

        # ========== 步骤8: 查找投递按钮 ==========
        print(f"\n[10] 查找投递按钮...")
        apply_btn = None
        apply_selectors = [
            '.summary-planes__action button',
            '.collect-and-apply__btn',
            '.btn.apply-btn',
            '.a-button.a--bordered.a--filled',
            'button:has-text("立即投递")',
            'a:has-text("立即投递")'
        ]

        for selector in apply_selectors:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    btn_text = await btn.inner_text()
                    print(f"    找到: {selector} - '{btn_text}'")
                    apply_btn = btn
                    break
            except:
                continue

        if not apply_btn:
            print(f"    未找到投递按钮")
            await save_screenshot('07_no_apply_button')
        else:
            await save_screenshot('07_found_apply_button')

            # ========== 步骤9: 点击投递 ==========
            print(f"\n[11] 点击投递按钮...")
            try:
                await apply_btn.click(timeout=5000)
                print(f"    已点击")
            except Exception as e:
                print(f"    点击失败: {e}")

            await asyncio.sleep(3)
            await save_screenshot('08_after_click_apply')

            result_text = await page.inner_text('body')
            if '投递成功' in result_text or '申请成功' in result_text:
                print(f"    结果: 投递成功!")
            elif '已投递' in result_text or '已申请' in result_text:
                print(f"    结果: 已投递过")
            else:
                print(f"    结果: 未知")
    else:
        print(f"\n[WARNING] 没有找到任何职位URL，无法继续")

    print(f"\n截图保存位置: {screenshot_dir}")
    print(f"共 {step[0]} 张截图")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(debug_flow())