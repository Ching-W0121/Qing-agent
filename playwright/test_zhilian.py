"""
智联招聘 完整搜索和职位数据抓取测试
"""

import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

async def test_zhilian_full():
    print("=" * 60)
    print("智联招聘 完整搜索测试")
    print("=" * 60)

    async with async_playwright() as p:
        try:
            print("\n[1] 启动浏览器...")
            browser = await p.chromium.launch(
                headless=False,
                channel='msedge',
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
            )
            page = await context.new_page()

            # 访问智联招聘搜索页面
            print("[2] 访问智联招聘搜索页面...")
            search_url = 'https://sou.zhaopin.com/?jl=765&kw=品牌策划'
            await page.goto(search_url)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            print(f"[OK] 页面加载完成")

            # 获取页面标题
            title = await page.title()
            print(f"[INFO] 页面标题: {title}")

            # 截图保存初始状态
            await page.screenshot(path='zhilian_step1.png', full_page=True)
            print("[OK] 截图已保存: zhilian_step1.png")

            # 等待搜索结果加载
            print("[3] 等待搜索结果...")
            await page.wait_for_timeout(5000)

            # 截图保存结果
            await page.screenshot(path='zhilian_step2_results.png', full_page=True)
            print("[OK] 结果截图已保存: zhilian_step2_results.png")

            # 尝试获取职位列表
            print("[4] 尝试获取职位列表...")

            # 使用 evaluate 获取页面内容分析
            job_data = await page.evaluate('''() => {
                const jobs = [];
                // 尝试多种选择器
                const jobCards = document.querySelectorAll('.jobinfo, .job-card, [class*="joblist"] a, .search-result-list a');
                jobCards.forEach((card, index) => {
                    if (index < 10) { // 只取前10个
                        const title = card.querySelector('.jobname, .job-name, [class*="title"]')?.innerText || '';
                        const company = card.querySelector('.companyname, .company-name, [class*="company"]')?.innerText || '';
                        const salary = card.querySelector('.salary')?.innerText || '';
                        if (title) {
                            jobs.push({ title, company, salary });
                        }
                    }
                });
                return {
                    count: jobCards.length,
                    jobs: jobs
                };
            }''')

            print(f"[INFO] 找到 {job_data['count']} 个职位元素")

            if job_data['jobs']:
                print("\n职位列表:")
                for i, job in enumerate(job_data['jobs'][:5], 1):
                    print(f"  {i}. {job['title']} | {job['company']} | {job['salary']}")

            # 尝试更精确的选择器
            print("\n[5] 尝试精确选择器获取数据...")

            # 等待内容加载
            await page.wait_for_selector('.jobinfo', timeout=10000).catch(lambda: None)

            # 获取所有职位卡片
            jobs = await page.query_selector_all('.jobinfo')

            if jobs:
                print(f"[OK] 找到 {len(jobs)} 个职位卡片")

                # 解析前5个职位
                for i, job_card in enumerate(jobs[:5], 1):
                    try:
                        title_elem = await job_card.query_selector('.jobname')
                        company_elem = await job_card.query_selector('.companyname')
                        salary_elem = await job_card.query_selector('.salary')

                        title = await title_elem.inner_text() if title_elem else "N/A"
                        company = await company_elem.inner_text() if company_elem else "N/A"
                        salary = await salary_elem.inner_text() if salary_elem else "N/A"

                        print(f"  {i}. {title.strip()} | {company.strip()} | {salary.strip()}")
                    except Exception as e:
                        print(f"  {i}. 解析失败: {e}")
            else:
                print("[WARN] 未找到职位卡片，尝试其他方式...")

                # 获取页面 HTML 片段用于调试
                html_preview = await page.inner_html('body')
                print(f"[DEBUG] 页面内容长度: {len(html_preview)} 字符")

                # 尝试保存完整 HTML
                with open('zhilian_page.html', 'w', encoding='utf-8') as f:
                    f.write(html_preview)
                print("[OK] 页面 HTML 已保存: zhilian_page.html")

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

if __name__ == '__main__':
    asyncio.run(test_zhilian_full())
