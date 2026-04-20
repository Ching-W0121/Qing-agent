"""
V3.3 完整流程测试脚本
使用ZhilianPlatform直接搜索和投递
"""

import asyncio
import json
import sys
import random
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from platforms.zhilian import ZhilianPlatform


async def load_cookies():
    """从文件加载Cookie"""
    cookie_file = Path('C:/Users/TR/Desktop/1.txt')
    with open(cookie_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    return cookies


async def run_test():
    print("=" * 60)
    print("V3.3 完整流程测试 - 品牌策划+品牌设计")
    print("=" * 60)

    # 加载Cookie
    cookies = await load_cookies()
    print(f"[OK] 已加载 {len(cookies)} 个Cookie")

    # 修复Cookie格式
    for cookie in cookies:
        if cookie.get('sameSite') == 'unspecified':
            cookie['sameSite'] = 'Lax'

    # 初始化平台
    platform = ZhilianPlatform()

    # 使用非持久化模式
    await platform.init(headless=False, use_persistent=False)

    # 设置Cookie
    try:
        await platform.context.add_cookies(cookies)
        print("[OK] Cookie已设置")
    except Exception as e:
        print(f"[WARN] Cookie设置失败: {e}")

    # 1. 验证登录
    print("\n[1] 验证登录状态...")
    page = await platform.new_page()
    await page.goto('https://www.zhaopin.com/', wait_until='domcontentloaded')
    await asyncio.sleep(3)

    # 检查是否已登录
    try:
        login_name = await page.inner_text('.user-name, .login-name, [class*="user"][class*="name"]')
        print(f"[OK] 已登录: {login_name}")
    except:
        print("[WARN] 未检测到登录信息")

    # 2. 搜索职位
    print("\n[2] 搜索职位...")
    keywords = ['品牌策划', '品牌设计']
    city = '深圳'
    all_jobs = []

    for keyword in keywords:
        for page_num in range(1, 4):  # 最多3页
            print(f"  搜索: {keyword} @ {city} 第{page_num}页...")

            # 直接使用平台搜索
            jobs = await platform.search_jobs(keyword, city, page_num)
            print(f"    找到 {len(jobs)} 个职位")

            if not jobs:
                print(f"    第{page_num}页无数据，停止")
                break

            all_jobs.extend(jobs)

            await asyncio.sleep(random.uniform(3, 6))

    print(f"\n共找到 {len(all_jobs)} 个职位")

    # 3. 去重
    seen_ids = set()
    unique_jobs = []
    for job in all_jobs:
        job_id = job.get('platform_job_id') or job.get('job_id') or ''
        job_url = job.get('source_url') or job.get('url') or ''
        identifier = job_id or job_url
        if identifier and identifier not in seen_ids:
            seen_ids.add(identifier)
            unique_jobs.append(job)
        elif not identifier:
            unique_jobs.append(job)
    print(f"去重后: {len(unique_jobs)} 个职位")

    # 4. 投递（前6个职位）
    print("\n[3] 开始投递...")
    applied_count = 0
    apply_results = []

    for i, job in enumerate(unique_jobs[:6]):
        job_url = job.get('source_url') or job.get('url')
        if not job_url:
            continue

        title = job.get('title', 'N/A')
        company = job.get('company', 'N/A')
        print(f"\n  [{i+1}/6] 投递: {title} @ {company}")
        print(f"      URL: {job_url}")

        try:
            # 使用平台投递方法
            apply_result = await platform.apply_job(job_url)
            print(f"      结果: {apply_result.get('message', 'unknown')}")

            apply_results.append({
                'title': title,
                'company': company,
                'result': apply_result.get('message', 'unknown')
            })
        except Exception as e:
            print(f"      投递失败: {e}")
            apply_results.append({
                'title': title,
                'company': company,
                'result': f'error: {e}'
            })

        applied_count += 1

        # 随机延时
        await asyncio.sleep(random.uniform(5, 10))

    # 5. 总结
    print("\n" + "=" * 60)
    print("测试完成!")
    print(f"投递数量: {applied_count}")
    print("=" * 60)

    # 输出详细结果
    success_count = 0
    for i, result in enumerate(apply_results, 1):
        status = result['result']
        if '成功' in status:
            success_count += 1
        print(f"  {i}. {result['title']} @ {result['company']}: {status}")

    print(f"\n成功: {success_count}/{applied_count}")

    # 关闭
    await platform.close()

    return {
        'success': True,
        'applied_count': applied_count,
        'success_count': success_count,
        'results': apply_results
    }


if __name__ == '__main__':
    result = asyncio.run(run_test())
    print(f"\n最终结果: {result}")