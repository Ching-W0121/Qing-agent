import sys
sys.path.insert(0, 'src')
import asyncio
from platforms.zhilian import ZhilianPlatform

async def test():
    platform = ZhilianPlatform()
    await platform.init(headless=True)

    import json
    with open('C:/Users/TR/Desktop/1.txt', 'r') as f:
        cookies = json.load(f)

    await platform.context.add_cookies([{
        'name': c['name'],
        'value': c['value'],
        'domain': c.get('domain', '.zhaopin.com'),
        'path': c.get('path', '/'),
    } for c in cookies[:5]])

    # Test search with 1 keyword, 1 page
    jobs = await platform.search_jobs('品牌策划', '深圳', 1)
    print(f'Found {len(jobs)} jobs')

    # Write results to file
    with open('search_results.json', 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    print('Results written to search_results.json')

    for i, job in enumerate(jobs[:3]):
        print(f"\nJob {i+1}:")
        print(f"  title: '{job.get('title', '')}'")
        print(f"  company: '{job.get('company', '')}'")
        print(f"  salary: '{job.get('salary', '')}'")
        print(f"  salary_min: {job.get('salary_min', 0)}")
        print(f"  salary_max: {job.get('salary_max', 0)}")

    await platform.close()

asyncio.run(test())