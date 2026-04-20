"""
测试投递单个职位 - 修复版
点击后直接检查结果，不再重新查找按钮
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_apply():
    print("=" * 60)
    print("测试投递单个职位")
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

    test_url = 'https://www.zhaopin.com/jobdetail/CC665457120J40838395301.htm?refcode=4089&srccode=408901&preactionid=f3e53f46-b339-4f04-acf6-276bc0ad1ffb'

    print(f"\n[1] 打开: {test_url}")
    await page.goto(test_url, wait_until='domcontentloaded')
    await asyncio.sleep(3)

    print(f"    URL: {page.url}")
    print(f"    标题: {await page.title()}")

    body_text = await page.inner_text('body')
    print(f"    内容长度: {len(body_text)}")

    # 查找并点击投递按钮
    apply_btn_selectors = [
        '.summary-planes__action button',
        '.collect-and-apply__btn',
        '.a-button.a--bordered.a--filled',
        'button:has-text("立即投递")',
        'a:has-text("立即投递")'
    ]

    clicked = False
    for selector in apply_btn_selectors:
        if clicked:
            break
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=2000):
                btn_text = await btn.inner_text()
                print(f"\n[2] 找到按钮 [{selector}]: {btn_text.strip()}")

                # 点击投递
                print(f"\n[3] 点击投递...")
                await btn.click()
                clicked = True

                # 等待结果
                await asyncio.sleep(3)

                # 检查页面变化 - 可能是弹窗
                modal_selectors = [
                    '.modal-dialog button:has-text("确认")',
                    '.modal-dialog button:has-text("确定")',
                    '.dialog button:has-text("确认")',
                    '.dialog button:has-text("确定")',
                    'button.confirm-btn',
                    '.a-modal button:has-text("确认")'
                ]

                for modal_sel in modal_selectors:
                    try:
                        modal_btn = page.locator(modal_sel).first
                        if await modal_btn.is_visible(timeout=1000):
                            print(f"    找到确认弹窗按钮: {modal_sel}")
                            await modal_btn.click()
                            await asyncio.sleep(2)
                            break
                    except:
                        continue

                # 检查最终结果
                final_text = await page.inner_text('body')
                print(f"    最终页面长度: {len(final_text)}")

                if '投递成功' in final_text or '申请成功' in final_text:
                    print(f"\n★★★ 结果: 投递成功! ★★★")
                elif '已投递' in final_text or '已申请' in final_text:
                    print(f"\n★★★ 结果: 已投递过 ★★★")
                elif '失败' in final_text or '错误' in final_text:
                    print(f"\n★★★ 结果: 投递失败 ★★★")
                else:
                    print(f"\n    结果未知，可能需要人工检查")
                    # 截图保存
                    await page.screenshot(path='test_apply_result.png', full_page=True)
                    print(f"    截图已保存: test_apply_result.png")

        except Exception as e:
            print(f"    按钮 {selector} 处理异常: {e}")
            continue

    if not clicked:
        print(f"\n[ERROR] 未找到任何投递按钮")

    # 截图
    await page.screenshot(path='test_apply_final.png', full_page=True)
    print(f"\n最终截图已保存: test_apply_final.png")

    await browser.close()
    await playwright.stop()


if __name__ == '__main__':
    asyncio.run(test_apply())