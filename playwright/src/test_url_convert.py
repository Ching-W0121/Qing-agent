"""
测试URL转换是否正确
"""

import asyncio
import json
import sys
import re
import html
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from platforms.zhilian import ZhilianPlatform


async def test_url_conversion():
    print("=" * 60)
    print("测试URL转换逻辑")
    print("=" * 60)

    platform = ZhilianPlatform()
    await platform.init(headless=True, use_persistent=False)

    # 模拟提取到的URL（和搜索结果中的一样）
    test_urls = [
        # 模拟 /job/ 格式（这是网页中常见的格式）
        'https://www.zhaopin.com/job/CC820107150J40799697111.htm?utm_source=test',
        'https://www.zhaopin.com/job/CC401831410J40784320707.htm?refcode=4089',
        # 已经是 jobdetail 格式的
        'https://www.zhaopin.com/jobdetail/CC665457120J40838395301.htm?refcode=4089&srccode=408901',
    ]

    print("\n测试URL转换:")
    for test_url in test_urls:
        # 应用和 search_jobs 中相同的转换逻辑
        if '/job/' in test_url:
            converted = test_url.replace('/job/', '/jobdetail/')
            print(f"  原始: {test_url}")
            print(f"  转换: {converted}")
            print()
        else:
            print(f"  保持: {test_url}")
            print()

    await platform.close()


async def test_search_and_apply():
    """完整测试：搜索 -> 获取URL -> 投递"""
    print("\n" + "=" * 60)
    print("完整流程测试")
    print("=" * 60)

    cookies_file = Path('C:/Users/TR/Desktop/1.txt')
    with open(cookies_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    for cookie in cookies:
        if cookie.get('sameSite') == 'unspecified':
            cookie['sameSite'] = 'Lax'

    platform = ZhilianPlatform()
    await platform.init(headless=False, use_persistent=False)

    try:
        await platform.context.add_cookies(cookies)
        print("[OK] Cookie已设置")
    except Exception as e:
        print(f"[WARN] Cookie设置失败: {e}")

    page = await platform.new_page()

    # 1. 搜索
    print("\n[1] 搜索职位...")
    jobs = await platform.search_jobs('品牌策划', '深圳', 1)
    print(f"    找到 {len(jobs)} 个职位")

    if jobs:
        # 2. 检查第一个职位的URL格式
        first_job = jobs[0]
        print(f"\n[2] 检查URL格式:")
        print(f"    source_url: {first_job.get('source_url', '')}")
        print(f"    platform_job_id: {first_job.get('platform_job_id', '')}")

        # 3. 尝试投递第一个职位
        job_url = first_job.get('source_url', '')
        if job_url and '/jobdetail/' in job_url:
            print(f"\n[3] 投递职位: {job_url}")
            result = await platform.apply_job(job_url)
            print(f"    结果: {result.get('message', 'unknown')}")
            print(f"    状态: {result.get('status', 'unknown')}")
        else:
            print(f"\n[ERROR] URL格式不正确: {job_url}")
    else:
        print("    没有找到职位")

    await platform.close()


if __name__ == '__main__':
    asyncio.run(test_url_conversion())
    asyncio.run(test_search_and_apply())