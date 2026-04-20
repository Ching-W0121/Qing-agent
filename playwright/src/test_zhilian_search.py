"""
测试 zhilian.py 的 search_jobs 方法
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from platforms.zhilian import ZhilianPlatform


async def test():
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

    print("\n[1] 搜索: 品牌策划 @ 深圳")
    jobs = await platform.search_jobs('品牌策划', '深圳', 1)
    print(f"    找到 {len(jobs)} 个职位")

    if jobs:
        print("\n[2] 前3个职位:")
        for i, job in enumerate(jobs[:3], 1):
            print(f"    {i}. {job.get('title')} @ {job.get('company')}")
            print(f"       URL: {job.get('source_url', '')[:80]}...")

    print("\n完成!")
    await platform.close()


if __name__ == '__main__':
    asyncio.run(test())