from typing import List, Dict
from platforms.base import BasePlatform
import asyncio
import re
import html
import random


class ZhilianPlatform(BasePlatform):
    """智联招聘平台适配器 - 增强反爬版"""

    def __init__(self):
        super().__init__('智联招聘')
        self.base_url = 'https://www.zhaopin.com'
        self.city_codes = {
            '深圳': '765',
            '北京': '530',
            '上海': '538',
            '广州': '753',
        }

    async def _human_delay(self, min_ms: float = 500, max_ms: float = 2000):
        """模拟人类操作的随机延迟 - V3.1增强版"""
        await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)

    async def _human_scroll(self, page, depth: str = 'half'):
        """模拟人类滚动页面 - V3.1增强版"""
        # 人类不会直线性滚动，会有停顿和微调
        if depth == 'half':
            # 先快速滚动到中部
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
            await asyncio.sleep(random.uniform(0.3, 0.7))
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
            await asyncio.sleep(random.uniform(0.2, 0.5))
        elif depth == 'full':
            # 分段滚动，带随机停顿
            positions = [0.2, 0.5, 0.8, 1.0]
            for pos in positions:
                await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pos})")
                await asyncio.sleep(random.uniform(0.3, 0.8))
        elif depth == 'third':
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            await asyncio.sleep(random.uniform(0.4, 0.9))
        elif depth == 'random':
            # 随机滚动到某个位置
            random_pos = random.uniform(0.2, 0.8)
            await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {random_pos})")
            await asyncio.sleep(random.uniform(0.3, 0.6))
        await asyncio.sleep(random.uniform(0.2, 0.5))

    async def _human_mouse_move(self, page, element):
        """模拟人类鼠标移动到元素 - V3.1增强版"""
        box = await element.bounding_box()
        if box:
            # 鼠标移动到元素中心，带一点随机偏移
            start_x = random.randint(50, 300)
            start_y = random.randint(50, 300)
            end_x = box['x'] + box['width'] / 2 + random.uniform(-15, 15)
            end_y = box['y'] + box['height'] / 2 + random.uniform(-15, 15)

            # 分段移动，模拟人类轨迹（更多步骤，更自然的曲线）
            steps = random.randint(8, 15)
            for i in range(steps):
                t = i / steps
                # 使用缓动函数让移动更自然
                ease_t = t * t * (3 - 2 * t)  # smoothstep
                x = start_x + (end_x - start_x) * ease_t + random.uniform(-5, 5)
                y = start_y + (end_y - start_y) * ease_t + random.uniform(-5, 5)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.03, 0.08))

    async def _random_mouse_wander(self, page):
        """随机鼠标漂移 - 模拟人类在页面上的无目的移动"""
        # 在页面上随机位置之间移动
        viewport = page.viewport_size
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, viewport['width'] - 100)
            y = random.randint(100, viewport['height'] - 100)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.2, 0.5))

    async def _random_click_non_target(self, page):
        """随机点击非目标元素 - 模拟人类误点"""
        # 随机选择器列表（常见但非目标元素）
        selectors = [
            'a[href*="about"]', 'a[href*="help"]', 'a[href*="contact"]',
            'span[class*="tag"]', 'div[class*="banner"]', 'button[class*="close"]',
            'a[target="_blank"]', 'img[class*="logo"]'
        ]
        try:
            selector = random.choice(selectors)
            element = await page.query_selector(selector)
            if element and random.random() < 0.3:  # 30%概率真的点击
                box = await element.bounding_box()
                if box:
                    # 先漂移到元素
                    await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    # 点击
                    await element.click()
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    # 返回
                    await page.go_back()
                    await asyncio.sleep(random.uniform(0.5, 1.0))
        except:
            pass  # 忽略选择器失败

    async def _human_hover_random_element(self, page):
        """随机悬停在某个元素上 - 模拟人类浏览"""
        try:
            # 随机选择页面上某个链接或按钮
            elements = await page.query_selector_all('a, button, .joblist-box__item')
            if elements:
                element = random.choice(elements[:10])  # 只看前10个
                await element.hover()
                await asyncio.sleep(random.uniform(0.5, 1.5))
        except:
            pass


    async def login(self, cookie: str = None, username: str = None, password: str = None) -> bool:
        """登录智联招聘"""
        print(f"[智联] login() called with cookie={type(cookie)}, username={username}, password={password}")
        try:
            if cookie:
                # 使用 Cookie 登录
                # cookie 可能是:
                # 1. 单个 cookie 值字符串
                # 2. JSON 字符串数组 (从浏览器 DevTools 复制)
                try:
                    import json
                    cookies_data = json.loads(cookie)
                    if isinstance(cookies_data, list):
                        cookies_list = cookies_data
                        print(f"[智联] Parsed {len(cookies_list)} cookies from JSON")
                    else:
                        print(f"[智联] Cookie is not a list, using as single cookie")
                        cookies_list = [{'name': 'zp_token', 'value': cookie, 'url': self.base_url}]
                except json.JSONDecodeError as e:
                    print(f"[智联] JSON decode error: {e}, using as single cookie")
                    cookies_list = [{'name': 'zp_token', 'value': cookie, 'url': self.base_url}]

                # 只保留必要的 cookie 属性 (在导航前添加)
                cookies_to_add = []
                for c in cookies_list:
                    cookie_dict = {
                        'name': c.get('name', ''),
                        'value': c.get('value', ''),
                        'domain': c.get('domain', '.zhaopin.com'),
                        'path': c.get('path', '/'),
                    }
                    if 'expirationDate' in c:
                        cookie_dict['expires'] = c['expirationDate']
                    if 'secure' in c:
                        cookie_dict['secure'] = c['secure']
                    cookies_to_add.append(cookie_dict)

                print(f"[智联] Adding {len(cookies_to_add)} cookies")
                await self.context.add_cookies(cookies_to_add)

            # 创建新页面并导航
            page = await self.new_page()
            print(f"[智联] Navigating to {self.base_url}/")

            # 模拟人类进入网站的行为 - 先随机滚动一下
            await page.goto(f'{self.base_url}/', wait_until='domcontentloaded')
            await self._human_delay(1000, 2000)
            await self._human_scroll(page, 'third')

            if username and password:
                # 点击登录 - 模拟人类找登录按钮
                login_link = await page.query_selector('text=登录')
                if login_link:
                    await self._human_mouse_move(page, login_link)
                    await self._human_delay(200, 500)
                    await login_link.click()
                    await self._human_delay(1000, 1500)

                # 输入账号密码 - 模拟人类打字
                username_input = await page.query_selector('input[name="loginname"]')
                password_input = await page.query_selector('input[name="password"]')
                if username_input:
                    # 逐字输入模拟人类打字
                    for char in username:
                        await username_input.type(char, delay=random.randint(50, 150))
                        await asyncio.sleep(random.uniform(0.02, 0.08))
                    await self._human_delay(100, 300)

                if password_input:
                    for char in password:
                        await password_input.type(char, delay=random.randint(80, 200))
                        await asyncio.sleep(random.uniform(0.02, 0.08))
                    await self._human_delay(200, 400)

                # 提交按钮
                submit_btn = await page.query_selector('button[type="submit"]')
                if submit_btn:
                    await self._human_mouse_move(page, submit_btn)
                    await self._human_delay(100, 300)
                    await submit_btn.click()
                    await self._human_delay(3000, 6000)

            # 验证登录成功
            await page.wait_for_timeout(2000)

            # 检查是否还有登录弹窗打开（明确的登录失败标志）
            login_dialog = await page.query_selector(
                '.login-dialog, .login-popup, .dialog-login, .login-modal, '
                '[class*="login"][class*="dialog"]:not([class*="closed"]), '
                '[class*="popup"][class*="login"]:not([class*="closed"])'
            )

            if login_dialog:
                print(f"[智联] Login dialog visible - cookie may be invalid")
                await page.close()
                return False

            # 对于 Cookie 登录，只要页面能加载且没有登录弹窗，就认为成功
            # 因为用户信息元素可能是异步加载的
            print(f"[智联] Cookie login successful - page loaded without login dialog")
            await page.close()
            return True

            await page.close()
            print(f"[智联] Login completed successfully")
            return True

        except Exception as e:
            print(f"[智联] Login exception: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def search_jobs(self, keyword: str, city: str = '深圳', page_num: int = 1) -> List[Dict]:
        """搜索职位 - V3.1增强版：列表页优先，低频抓取"""
        browser_page = await self.new_page()
        jobs = []

        try:
            city_code = self.city_codes.get(city, '765')
            search_url = f'https://sou.zhaopin.com/?jl={city_code}&kw={keyword}&p={page_num}'

            print(f"[智联] 搜索: {keyword} @ {city} 第{page_num}页")

            # V3.1: 随机点击非目标元素模拟
            await browser_page.goto('about:blank')
            await self._human_delay(500, 1000)
            await self._random_mouse_wander(browser_page)

            # 模拟人类搜索行为
            await browser_page.goto(search_url, wait_until='domcontentloaded')

            # V3.1: 人类行为模拟增强
            # 1. 等待页面基本加载
            await self._human_delay(3000, 5000)

            # 2. 随机悬停一些元素（假装在浏览）
            await self._human_hover_random_element(browser_page)

            # 3. 滚动页面（分阶段，带随机停留）
            await self._human_scroll(browser_page, 'third')

            # 4. 等待网络空闲
            await browser_page.wait_for_load_state('networkidle')
            await self._human_delay(2000, 4000)

            # 5. 随机点击非目标元素（模拟误点）
            await self._random_click_non_target(browser_page)

            # 6. 再滚动一下
            await self._human_scroll(browser_page, 'random')

            # 从 HTML 中提取职位 URL
            html_content = await browser_page.content()

            # 解码 HTML 实体
            html_decoded = html.unescape(html_content) if hasattr(html, 'unescape') else html_content

            # 提取 jobdetail URL
            job_pattern = r'href=["\']([^"\']*jobdetail[^"\']*\.htm[^"\']*)["\']'
            job_urls = re.findall(job_pattern, html_decoded, re.IGNORECASE)

            # 去重
            seen = set()
            for job_url in job_urls:
                if job_url in seen:
                    continue
                seen.add(job_url)

                if len(jobs) >= 30:
                    break

                try:
                    # 清理 URL
                    job_url = job_url.split('?')[0]  # 移除查询参数

                    # 标准化 URL 格式 - 旧格式 jobdetail/CCL... 已过时，转为新格式 job/CC...
                    # 新格式: https://www.zhaopin.com/job/CC1427635810J40875239003.htm
                    # 旧格式: http://www.zhaopin.com/jobdetail/CCL1491889800J40816898501.htm
                    if 'jobdetail' in job_url:
                        # 从旧格式提取 job_id: CCL1491889800J40816898501 -> 1491889800J40816898501
                        filename = job_url.split('/')[-1].replace('.htm', '')
                        # 去掉 CC/L 前缀，保留后面的数字字母
                        job_id_raw = filename.replace('CCL', '').replace('CC', '')
                        # 尝试构建新格式 URL
                        new_format_url = f'https://www.zhaopin.com/job/CC{job_id_raw}.htm'
                        job_url = new_format_url
                        print(f"[智联] 转换旧格式URL: {new_format_url}")

                    # 从 URL 提取 platform_job_id
                    filename = job_url.split('/')[-1].replace('.htm', '')
                    # 新格式: CC1427635810J40875239003 -> 1427635810J40875239003
                    platform_job_id = filename.replace('CC', '')

                    job = {
                        'platform': 'zhilian',
                        'platform_job_id': platform_job_id,
                        'title': '',  # 需要从页面获取
                        'company': '',
                        'city': city,
                        'area': '',
                        'salary': '',
                        'salary_min': 0,
                        'salary_max': 0,
                        'source_url': job_url,
                    }
                    jobs.append(job)
                except Exception as e:
                    continue

            # 尝试从页面获取更多信息
            for i, job in enumerate(jobs):
                try:
                    # 使用 JavaScript 获取相关元素的文本
                    # 注意: source_url 此时已经清理过, 不包含查询参数
                    source_url_filename = job['source_url'].split('/')[-1]

                    # 获取职位容器信息 - 使用正确的选择器
                    job_info = await browser_page.evaluate("""(fname) => {
                        const links = document.querySelectorAll('a[href*="' + fname + '"]');
                        for (let link of links) {
                            if (link.href.includes('jobdetail') || link.href.includes('/job/')) {
                                let company = '';
                                let areaText = '';
                                let salaryText = '';

                                // 获取容器 - jobinfo 包含职位信息, companyinfo 包含公司信息
                                const container = link.closest('.joblist-box__item, .joblist-box__iteminfo');
                                const companyInfo = container?.querySelector('.companyinfo');

                                if (!container) continue;

                                // 职位名称 - 从链接获取
                                const title = link.innerText?.trim() || '';

                                // 公司名 - 从 companyinfo 获取
                                const companySelectors = [
                                    '.companyinfo__name', '.companyinfo__name a',
                                    '[class*="companyinfo"][class*="name"]',
                                    '.companyinfo a', 'a.companyinfo'
                                ];
                                for (const sel of companySelectors) {
                                    const el = companyInfo?.querySelector(sel);
                                    if (el && el.innerText.trim()) {
                                        company = el.innerText.trim();
                                        break;
                                    }
                                }
                                // 备用: 从 companyinfo 的 innerText 获取
                                if (!company && companyInfo) {
                                    const ciText = companyInfo.innerText;
                                    const lines = ciText.split(/[\\n\\r]+/);
                                    if (lines.length > 0) company = lines[0].trim();
                                }

                                // 薪资 - 从 jobinfo 获取
                                const salarySelectors = [
                                    '.jobinfo__salary', '[class*="salary"]',
                                    '.jobinfo [class*="salary"]'
                                ];
                                for (const sel of salarySelectors) {
                                    const el = container.querySelector(sel);
                                    if (el && el.innerText.trim()) {
                                        salaryText = el.innerText.trim().replace(/[\\n\\r\\s]+/g, '');
                                        break;
                                    }
                                }

                                // 区域/城市
                                const areaSelectors = [
                                    '.jobinfo__other-info-location-image',
                                    '[class*="location"]',
                                    '.jobinfo__other-info span'
                                ];
                                for (const sel of areaSelectors) {
                                    const el = container.querySelector(sel);
                                    if (el && el.innerText.trim()) {
                                        areaText = el.innerText.trim().replace(/[\\n\\r\\s]+/g, '');
                                        break;
                                    }
                                }

                                return {
                                    title: title,
                                    company: company,
                                    area: areaText,
                                    salary: salaryText,
                                    linkHref: link.href
                                };
                            }
                        }
                        return null;
                    }""", source_url_filename)

                    if not job_info:
                        continue

                    # 提取数据
                    if job_info.get('title'):
                        job['title'] = job_info['title']
                    if job_info.get('company') and job_info['company']:
                        job['company'] = job_info['company']
                    if job_info.get('area') and job_info['area']:
                        area_text = job_info['area']
                        # 解析城市和区域
                        if '·' in area_text or '|' in area_text:
                            parts = re.split(r'[·|]', area_text)
                            if len(parts) >= 2:
                                job['city'] = parts[0].strip()
                                job['area'] = '·'.join(parts[1:]).strip()
                        else:
                            job['city'] = area_text
                    if job_info.get('salary') and job_info['salary']:
                        job['salary'] = job_info['salary']
                        job['salary_min'], job['salary_max'] = self._parse_salary(job['salary'])

                except Exception as e:
                    import traceback
                    print(f"[智联] 提取职位信息失败: {e}")
                    traceback.print_exc()
                    continue

            print(f"[智联] 找到 {len(jobs)} 个职位")

        except Exception as e:
            print(f"[智联] 搜索失败: {e}")

        finally:
            await browser_page.close()

        return jobs

    def _parse_salary(self, salary_text: str) -> tuple:
        """解析薪资文本返回 min, max"""
        if not salary_text or '面议' in salary_text:
            return 0, 0

        # 匹配薪资范围 如 "8-15K", "8-15千", "1.5-3万", "10-20万"
        pattern = r'(\d+\.?\d*)\s*[万kK千]?\s*[-~至]\s*(\d+\.?\d*)\s*[万kK千]?'
        match = re.search(pattern, salary_text, re.IGNORECASE)
        if match:
            min_val = float(match.group(1))
            max_val = float(match.group(2))

            # 确定单位 (万、千、K)
            unit_text = salary_text.lower()
            if '万' in unit_text:
                multiplier = 10000
            elif 'k' in unit_text:
                multiplier = 1000
            elif '千' in unit_text:
                multiplier = 1000
            else:
                multiplier = 1000  # 默认按千元处理

            min_sal = int(min_val * multiplier)
            max_sal = int(max_val * multiplier)
            return min_sal, max_sal

        return 0, 0

    async def apply_job(self, job_url: str) -> Dict:
        """投递职位 - 增强版，处理点击后打开新页面的情况"""
        page = await self.new_page()
        result = {
            'success': False,
            'message': '',
            'status': '',
            'company': '',
            'title': '',
            'salary': '',
            'salary_min': 0,
            'salary_max': 0,
            'city': '',
            'area': ''
        }

        try:
            # 模拟人类打开JD页面的行为
            await page.goto(job_url, wait_until='domcontentloaded')
            await self._human_delay(2000, 4000)

            # 先滚动到页面顶部，模拟人类浏览
            await page.evaluate("window.scrollTo(0, 0)")
            await self._human_delay(500, 1000)

            # 模拟人类慢慢往下滚动看职位详情
            await self._human_scroll(page, 'half')

            # ===== 提取职位详情 =====
            body_text = await page.inner_text('body')

            # 检查职位是否已下架/不存在
            if any(phrase in body_text for phrase in ['职位已下架', '职位不存在', '职位已失效', '该职位已暂停招聘', '职位已招满']):
                result['message'] = '职位已下架或不存在'
                result['status'] = 'position_not_exist'
                await page.close()
                return result

            # 检查是否被重定向到列表页（URL无效）
            if page.url != job_url and 'sou.zhaopin.com' in page.url:
                result['message'] = '职位URL已失效'
                result['status'] = 'position_not_exist'
                await page.close()
                return result

            # ===== 提取公司名称 =====
            company = ''

            # 方法1: 通过 CSS 选择器直接获取元素文本（最准确）
            company_selectors = [
                '.company-name',           # 智联常用
                '.enterprise-name',         # 企业名称
                '.company .name',           # 公司.name
                '.company-name-text',       # 公司名文本
                '[class*="company"][class*="name"]',
                '[class*="enterprise"][class*="name"]',
                '.detail-position .company',
                '.job-detail-tab .company',
                'h2.company-name',
                '.company a',               # 公司链接
                '.company-title',           # 公司标题
                '.company-info .name',      # 公司信息.名称
                '.base-info .company-name',
                '.first-row .company-name',
            ]
            for selector in company_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    company = (await elem.inner_text()).strip()
                    if company and len(company) >= 2:
                        # 清理公司名称
                        company = re.sub(r'^公司名称[：:]*\s*', '', company)
                        company = company.split('\n')[0].strip()  # 取第一行
                        # 去掉可能的后缀如"查看详情"等
                        company = re.sub(r'(查看详情|更多|>>).*$', '', company)
                        if company and len(company) <= 30:
                            break
                company = ''

            # 方法2: 通过文本匹配查找
            if not company:
                patterns = [
                    r'公司名称[：:]*\s*([^\n\r，,]+)',
                    r'公司[:：]\s*([^\n\r，,]+)',
                    r'企业名称[：:]*\s*([^\n\r，,]+)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, body_text)
                    if match:
                        company = match.group(1).strip()
                        break

            # 方法3: 在特定区域查找包含公司关键词的元素
            if not company:
                try:
                    # 在页面顶部区域查找
                    company_area = await page.evaluate("""
                        () => {
                            // 尝试在顶部区域找公司名
                            const header = document.querySelector('.job-detail-header, .position-detail-header, .job-header');
                            if (header) {
                                const text = header.innerText;
                                // 查找包含公司/集团/企业等的文本
                                const match = text.match(/[\\u4e00-\\u9fa5]{2,15}(?:公司|集团|企业|有限|股份|中心|医院|学校|工厂)/);
                                if (match) return match[0];
                            }
                            // 在 h1/h2/h3 中查找
                            const headings = document.querySelectorAll('h1, h2, h3');
                            for (const h of headings) {
                                const text = h.innerText;
                                if (/公司|集团|企业/.test(text)) {
                                    return text;
                                }
                            }
                            return '';
                        }
                    """)
                    if company_area:
                        company = company_area.strip()
                except:
                    pass

            # 方法4: 最后 fallback 到正则搜索
            if not company:
                match = re.search(r'([\u4e00-\u9fa5]{2,15}(?:公司|集团|企业|有限|股份|中心|医院|学校))', body_text)
                if match:
                    company = match.group(1)

            result['company'] = company

            # 提取职位名称
            title_elem = await page.query_selector('.job-name, .job-title, h1')
            if title_elem:
                result['title'] = (await title_elem.inner_text()).strip()

            # 提取薪资 - 常见格式 "1.5-3万" 或 "10-20K"
            salary_match = re.search(r'([\d.]+)\s*[-~至]\s*([\d.]+)\s*([万K千k元]*)?', body_text)
            if salary_match:
                min_sal = float(salary_match.group(1))
                max_sal = float(salary_match.group(2))
                unit = salary_match.group(3) or ''
                if '万' in unit:
                    result['salary_min'] = int(min_sal * 10000)
                    result['salary_max'] = int(max_sal * 10000)
                elif 'k' in unit.lower() or '千' in unit:
                    result['salary_min'] = int(min_sal * 1000)
                    result['salary_max'] = int(max_sal * 1000)
                else:
                    result['salary_min'] = int(min_sal * 1000)
                    result['salary_max'] = int(max_sal * 1000)
                result['salary'] = f"{min_sal}-{max_sal}{unit}"

            # ===== 提取城市和区域 =====
            city_area_selectors = [
                '.city-area', '.city .area', '.location .area',
                '[class*="city"][class*="area"]', '[class*="location"]',
                '.job-address', '.address-info', '.address',
                '.position-address', '.work-address',
            ]
            for selector in city_area_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    area_text = (await elem.inner_text()).strip()
                    if area_text and len(area_text) <= 50:
                        # 尝试解析格式: "城市 · 区域" 或 "城市 区域"
                        match = re.search(r'([\u4e00-\u9fa5]+)\s*[·\s]*([\u4e00-\u9fa5]+)', area_text)
                        if match:
                            result['city'] = match.group(1)
                            result['area'] = match.group(2)
                            break
                        # 如果只有一个词，可能是城市
                        if re.match(r'^[\u4e00-\u9fa5]+$', area_text) and 2 <= len(area_text) <= 10:
                            result['city'] = area_text
                            break

            # 如果选择器没找到，用正则匹配 body
            if not result['city']:
                # 常见格式: "深圳·福田·沙头", "深圳 南山区", "北京-朝阳区"
                patterns = [
                    r'([\u4e00-\u9fa5]{2,6})\s*[·\-\s]\s*([\u4e00-\u9fa5]{2,10}(?:区|县|镇|街|道|园|中心|城|村))',  # 城市·区域
                    r'工作地点[：:]*\s*([\u4e00-\u9fa5]+)\s*[·\-\s]*([\u4e00-\u9fa5]+)',  # 工作地点：城市·区域
                    r'地址[：:]*\s*([\u4e00-\u9fa5]{2,6})\s*[·\-\s]*([\u4e00-\u9fa5]+)',  # 地址：城市·区域
                    r'([\u4e00-\u9fa5]{2,6})(?:市|省)\s*([\u4e00-\u9fa5]{2,10}区?)',  # 深圳市 南山区
                ]
                for pattern in patterns:
                    area_match = re.search(pattern, body_text)
                    if area_match:
                        result['city'] = area_match.group(1)
                        result['area'] = area_match.group(2)
                        break

            # 滚动到页面底部找投递按钮
            await self._human_scroll(page, 'half')

            # 查找投递按钮
            apply_btn = await page.query_selector(
                '.collect-and-apply__btn, '
                '.btn.apply-btn, '
                'button:has-text("立即投递"), '
                'a:has-text("立即投递")'
            )

            if not apply_btn:
                result['message'] = '不可投递或已投递'
                result['status'] = 'not_applicable'
                await page.close()
                return result

            # 模拟人类鼠标移动到按钮位置
            await self._human_mouse_move(page, apply_btn)
            await self._human_delay(300, 600)

            # 点击投递按钮
            await apply_btn.click()

            # 等待新页面打开或内容变化 - 模拟人类等待
            await self._human_delay(2000, 4000)

            # 检查是否成功
            body_text = await page.inner_text('body')

            # 检查是否出现登录弹窗（cookie过期或未登录）
            login_popup_indicators = [
                '请登录', '登录后', 'login', 'Login',
                'text=登录', '登录即表示', '登录智联'
            ]
            # 排除真正的登录成功页面中的词
            if any(indicator in body_text for indicator in login_popup_indicators):
                # 检查是否真的是弹窗而不是页面内容
                login_dialog = await page.query_selector(
                    '.login-dialog, .login-popup, .dialog-login, '
                    '[class*="login"][class*="dialog"], [class*="popup"][class*="login"]'
                )
                if login_dialog or '请先登录' in body_text or '登录后' in body_text:
                    result['message'] = 'Cookie已过期，请重新获取Cookie'
                    result['status'] = 'cookie_expired'
                    await page.close()
                    return result

            if any(pattern in body_text for pattern in ['投递成功', '恭喜您', '恭喜', '已申请', '申请成功']):
                result['success'] = True
                result['message'] = '投递成功'
                result['status'] = 'submitted'
            else:
                # 检查是否打开了新页面
                await asyncio.sleep(2)
                current_pages = self.context.pages

                for new_page in current_pages:
                    if new_page != page:
                        try:
                            new_text = await new_page.inner_text('body')
                            # 检查新页面是否是登录页
                            if any(indicator in new_text for indicator in ['请登录', '登录后', 'login', 'Login']):
                                login_dialog = await new_page.query_selector(
                                    '.login-dialog, .login-popup, .dialog-login'
                                )
                                if login_dialog:
                                    result['message'] = 'Cookie已过期，请重新获取Cookie'
                                    result['status'] = 'cookie_expired'
                                    await new_page.close()
                                    await page.close()
                                    return result
                            if any(pattern in new_text for pattern in ['投递成功', '恭喜您', '恭喜', '已申请', '申请成功']):
                                result['success'] = True
                                result['message'] = '投递成功'
                                result['status'] = 'submitted'
                                await new_page.close()
                                break
                            else:
                                await new_page.close()
                        except:
                            pass

                if not result['success']:
                    body_text = await page.inner_text('body')
                    if '投递成功' in body_text or '恭喜' in body_text:
                        result['success'] = True
                        result['message'] = '投递成功'
                        result['status'] = 'submitted'
                    else:
                        result['message'] = '投递状态未知'
                        result['status'] = 'unknown'

        except Exception as e:
            result['message'] = f'投递失败: {e}'
            result['status'] = 'failed'

        finally:
            await page.close()

        return result

    async def get_job_detail(self, job_url: str) -> Dict:
        """获取职位详情 - V3.1增强版：人类行为模拟"""
        page = await self.new_page()
        try:
            # V3.1: 人类行为模拟 - 先随机浏览一下
            await page.goto('about:blank')
            await self._human_delay(500, 1500)
            await self._random_mouse_wander(page)

            # 访问详情页
            await page.goto(job_url, wait_until='domcontentloaded')

            # V3.1: 人类到达页面后的行为
            # 1. 先滚动到顶部（有时候页面从中间开始）
            await page.evaluate("window.scrollTo(0, 0)")
            await self._human_delay(1000, 2000)

            # 2. 随机滚动几次，模拟在浏览
            for _ in range(random.randint(2, 4)):
                await self._human_scroll(page, 'random')
                await self._human_delay(500, 1500)

            # 3. 获取职位描述
            desc_elem = await page.query_selector('.job-detail-content, .job-description')
            description = await desc_elem.inner_text() if desc_elem else ''

            # 4. 获取职位要求
            req_elem = await page.query_selector('.job-requirement, .requirement')
            requirements = await req_elem.inner_text() if req_elem else ''

            # V3.1: 离开前再随机移动一下鼠标
            await self._random_mouse_wander(page)
            await self._human_delay(300, 800)

            return {
                'description': description.strip(),
                'requirements': requirements.strip(),
            }
        except Exception as e:
            return {'description': '', 'requirements': '', 'error': str(e)}
        finally:
            await page.close()
