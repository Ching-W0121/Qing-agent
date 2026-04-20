"""
求职 Agent - Playwright 浏览器自动化入口

用法:
    python -m playwright.src.main --platform zhilian --keyword "品牌策划" --city 深圳
"""

import asyncio
import argparse
from typing import List, Dict
from platforms.zhilian import ZhilianPlatform
from platforms.job51 import Job51Platform
from platforms.liepin import LiepinPlatform


PLATFORMS = {
    'zhilian': ZhilianPlatform,
    '51job': Job51Platform,
    'liepin': LiepinPlatform,
}


async def search_platform(platform_name: str, keyword: str, city: str, page: int = 1) -> List[Dict]:
    """搜索单个平台"""
    if platform_name not in PLATFORMS:
        print(f"[错误] 不支持的平台: {platform_name}")
        return []

    platform = PLATFORMS[platform_name]()

    try:
        await platform.init(headless=True)

        # 登录（这里需要配置 cookie 或账号密码）
        login_success = await platform.login()
        if not login_success:
            print(f"[警告] {platform_name} 登录可能失败")

        # 搜索职位
        jobs = await platform.search_jobs(keyword, city, page)

        return jobs

    finally:
        await platform.close()


async def search_all(keyword: str, city: str, page: int = 1) -> Dict[str, List[Dict]]:
    """搜索所有平台"""
    results = {}

    for platform_name in PLATFORMS.keys():
        print(f"\n{'='*50}")
        print(f"开始搜索 {platform_name}...")
        jobs = await search_platform(platform_name, keyword, city, page)
        results[platform_name] = jobs
        print(f"{platform_name} 找到 {len(jobs)} 个职位")

    return results


async def apply_job(platform_name: str, job_url: str) -> Dict:
    """投递单个职位"""
    if platform_name not in PLATFORMS:
        return {'success': False, 'message': f'不支持的平台: {platform_name}'}

    platform = PLATFORMS[platform_name]()

    try:
        await platform.init(headless=True)
        await platform.login()

        result = await platform.apply_job(job_url)

        return result

    finally:
        await platform.close()


def main():
    parser = argparse.ArgumentParser(description='求职 Agent 浏览器自动化')
    parser.add_argument('--platform', choices=['zhilian', '51job', 'liepin', 'all'], default='all',
                        help='选择平台 (默认: all)')
    parser.add_argument('--keyword', required=True, help='搜索关键词')
    parser.add_argument('--city', default='深圳', help='目标城市 (默认: 深圳)')
    parser.add_argument('--page', type=int, default=1, help='页码 (默认: 1)')
    parser.add_argument('--url', help='投递职位 URL (可选)')

    args = parser.parse_args()

    if args.url:
        # 投递模式
        result = asyncio.run(apply_job(args.platform, args.url))
        print(f"\n投递结果: {result}")
    else:
        # 搜索模式
        if args.platform == 'all':
            results = asyncio.run(search_all(args.keyword, args.city, args.page))
        else:
            jobs = asyncio.run(search_platform(args.platform, args.keyword, args.city, args.page))
            results = {args.platform: jobs}

        # 打印结果
        print(f"\n{'='*50}")
        print("搜索结果汇总:")
        for platform, jobs in results.items():
            print(f"\n{platform}: {len(jobs)} 个职位")
            for i, job in enumerate(jobs[:5], 1):
                print(f"  {i}. {job.get('title', 'N/A')} @ {job.get('company', 'N/A')} ({job.get('salary', 'N/A')})")


if __name__ == '__main__':
    main()
