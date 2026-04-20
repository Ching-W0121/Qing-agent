import asyncio
import json

async def test_jd_page():
    from platforms.zhilian import ZhilianPlatform

    with open('C:/Users/TR/Desktop/1.txt', 'r') as f:
        cookie = json.dumps(json.load(f))

    platform = ZhilianPlatform()
    await platform.init(headless=False)

    await platform.login(cookie=cookie)

    # 测试访问JD页面
    page = await platform.new_page()
    test_url = 'https://www.zhaopin.com/job/CC1510505710J40818330109.htm'
    await page.goto(test_url, wait_until='domcontentloaded')
    await asyncio.sleep(3)

    # 提取页面HTML片段
    html = await page.content()

    # 写入文件以便分析
    with open('jd_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('HTML saved to jd_page.html')

    # 截图
    await page.screenshot(path='jd_page.png')
    print('Screenshot saved to jd_page.png')

    # 查找投递按钮
    apply_btn = await page.query_selector('.collect-and-apply__btn')
    print(f'Apply button (.collect-and-apply__btn): {apply_btn}')

    if not apply_btn:
        apply_btn = await page.query_selector('button')
        print(f'Apply button (any button): {apply_btn}')

    # 查找公司名称
    company_elem = await page.query_selector('.company-name')
    print(f'Company elem: {company_elem}')
    if company_elem:
        print(f'Company text: {await company_elem.inner_text()}')

    await platform.close()

asyncio.run(test_jd_page())
