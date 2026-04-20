"""
智联招聘 职位搜索测试
"""

import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

async def test_zhilian_search():
    print("=" * 60)
    print("智联招聘 职位搜索测试")
    print("=" * 60)

    async with async_playwright() as p:
        try:
            print("\n[1] 启动浏览器...")
            browser = await p.chromium.launch(
                headless=False,  # 显示浏览器窗口
                channel='msedge',
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
            )
            page = await context.new_page()

            # 访问智联招聘
            print("[2] 访问智联招聘...")
            await page.goto('https://www.zhaopin.com')
            await page.wait_for_load_state('networkidle')
            print(f"[OK] 页面加载成功")

            # 等待搜索框出现
            print("[3] 等待搜索框...")
            await page.wait_for_timeout(2000)

            # 查找搜索框并输入
            print("[4] 输入搜索关键词: 品牌策划...")

            # 尝试多种选择器
            search_input = None
            selectors = [
                'input[name="k"]',
                'input[placeholder*="搜索"]',
                '.search-input input',
                '#keywordInput',
                'input[class*="search"]'
            ]

            for selector in selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=3000)
                    if search_input:
                        print(f"[OK] 找到搜索框: {selector}")
                        break
                except:
                    continue

            if not search_input:
                # 截图以便调试
                await page.screenshot(path='debug_search.png')
                print("[WARN] 未找到标准搜索框，尝试截图调试...")

                # 获取页面快照查看结构
                snapshot = await page.content()
                if '品牌策划' in snapshot or '搜索' in snapshot:
                    print("[INFO] 页面包含搜索相关内容")

            # 输入关键词
            if search_input:
                await search_input.click()
                await search_input.fill('品牌策划')
                await page.wait_for_timeout(500)

                # 按回车搜索
                print("[5] 按回车键搜索...")
                await page.keyboard.press('Enter')
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(3000)

                # 获取结果
                title = await page.title()
                print(f"[OK] 搜索完成! 页面标题: {title}")

                # 尝试获取职位数量
                try:
                    # 查找结果数量元素
                    result_selectors = ['.result-count', '.job-count', '[class*="count"]']
                    for sel in result_selectors:
                        count_elem = await page.query_selector(sel)
                        if count_elem:
                            count_text = await count_elem.inner_text()
                            print(f"[INFO] 职位数量: {count_text}")
                            break
                except:
                    pass

                # 截图保存结果
                await page.screenshot(path='search_result.png', full_page=True)
                print("[OK] 截图已保存: search_result.png")

            print("\n" + "=" * 60)
            print("测试完成!")
            print("=" * 60)

            await browser.close()
            return True

        except Exception as e:
            print(f"[ERROR] 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    await test_zhilian_search()
    print("\n按 Enter 键退出...")
    input()

if __name__ == '__main__':
    asyncio.run(main())
