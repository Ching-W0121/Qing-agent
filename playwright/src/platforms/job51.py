"""
前程无忧 51job 平台适配器
V3.4 - 人类行为模拟为主，事前防御策略
"""

from typing import List, Dict, Optional, Tuple
from platforms.base import BasePlatform
import asyncio
import json
import random


class Job51Platform(BasePlatform):
    """前程无忧 51job 平台适配器"""

    def __init__(self):
        super().__init__('51job')
        self.base_url = 'https://we.51job.com'
        self._page: Optional[any] = None
        self._saved_cookies: List[Dict] = []
        # 搜索专用页面（复用同一个页面翻页）
        self._search_page: Optional[any] = None

    # ========== 人类行为模拟方法（参考智联） ==========

    async def _human_delay(self, min_ms: float = 500, max_ms: float = 2000):
        """模拟人类操作的随机延迟"""
        await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)

    async def _human_scroll(self, page, depth: str = 'half'):
        """模拟人类滚动页面"""
        if depth == 'half':
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
            await asyncio.sleep(random.uniform(0.3, 0.7))
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
            await asyncio.sleep(random.uniform(0.2, 0.5))
        elif depth == 'full':
            positions = [0.2, 0.5, 0.8, 1.0]
            for pos in positions:
                await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pos})")
                await asyncio.sleep(random.uniform(0.3, 0.8))
        elif depth == 'third':
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            await asyncio.sleep(random.uniform(0.4, 0.9))
        elif depth == 'random':
            random_pos = random.uniform(0.2, 0.8)
            await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {random_pos})")
            await asyncio.sleep(random.uniform(0.3, 0.6))
        await asyncio.sleep(random.uniform(0.2, 0.5))

    async def _random_mouse_wander(self, page):
        """随机鼠标漂移"""
        try:
            viewport = page.viewport_size
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.2, 0.5))
        except Exception:
            pass

    def _check_cancel(self):
        """检查是否已请求取消，如果是则抛出取消异常"""
        if self._cancel_requested:
            raise asyncio.CancelledError("任务被用户取消")

    # ========== 核心改进：Context/页面稳定性管理 ==========

    async def is_context_alive(self) -> bool:
        """检测 Persistent Context 是否可用"""
        try:
            if not self.persistent_context:
                return False
            pages = self.persistent_context.pages
            if not pages:
                return False
            if pages[0]:
                await pages[0].evaluate("1 + 1")
            return True
        except Exception:
            return False

    async def ensure_browser_ready(self) -> bool:
        """确保浏览器可用，如果不可用则自动修复"""
        if await self.is_context_alive():
            return True
        print(f"[51job] 浏览器连接已断开，尝试恢复...")
        try:
            await self._cleanup_browser_state()
            await self.init(headless=False, channel='msedge', use_persistent=True)
            if self._saved_cookies:
                await self.persistent_context.add_cookies(self._saved_cookies)
                print(f"[51job] Cookie 已恢复，共 {len(self._saved_cookies)} 条")
            return await self.is_context_alive()
        except Exception as e:
            print(f"[51job] 浏览器恢复失败: {e}")
            return False

    async def _cleanup_browser_state(self):
        """清理浏览器状态"""
        try:
            if self.persistent_context:
                await self.persistent_context.close()
        except Exception:
            pass
        self.persistent_context = None
        self.playwright = None

    async def _save_cookies(self):
        """保存当前 cookies"""
        try:
            if self.persistent_context:
                self._saved_cookies = await self.persistent_context.cookies()
                print(f"[51job] 已保存 {len(self._saved_cookies)} 个 cookies")
        except Exception as e:
            print(f"[51job] 保存 cookies 失败: {e}")

    async def restore_cookies(self):
        """恢复保存的 cookies"""
        if self._saved_cookies and self.persistent_context:
            try:
                await self.persistent_context.add_cookies(self._saved_cookies)
                print(f"[51job] 已恢复 {len(self._saved_cookies)} 个 cookies")
            except Exception as e:
                print(f"[51job] 恢复 cookies 失败: {e}")

    async def close(self):
        """关闭浏览器 - 保留 context"""
        await self._save_cookies()
        try:
            if self.persistent_context:
                for page in self.persistent_context.pages:
                    try:
                        if not page.is_closed():
                            await page.close()
                    except Exception:
                        pass
        except Exception as e:
            print(f"[51job] 关闭页面时出错: {e}")
        self._page = None

    async def verify_logged_in(self, page) -> bool:
        """验证是否已登录"""
        try:
            content = await page.content()
            if 'login' in content.lower() and '登录' in content:
                return False
            logged_in_indicators = ['退出', '个人中心', '我的简历', 'user-info', 'username']
            return any(indicator in content for indicator in logged_in_indicators)
        except Exception:
            return False

    async def login(self, cookie: str = None, username: str = None, password: str = None) -> bool:
        """登录 51job - 持久化登录版"""
        print(f"[51job] login() - use_persistent={self.user_data_dir is not None}, has_cookie={bool(cookie)}")
        try:
            if not await self.ensure_browser_ready():
                print(f"[51job] 浏览器不可用，无法登录")
                return False

            page = await self.persistent_context.new_page()
            self._page = page

            if cookie:
                print(f"[51job] 检测到 Cookie，尝试使用 Cookie 登录...")
                if self.persistent_context:
                    try:
                        cookies = self._parse_cookie_string(cookie)
                        if cookies:
                            await self.persistent_context.add_cookies(cookies)
                            self._saved_cookies = cookies
                            print(f"[51job] Cookie 已设置，共 {len(cookies)} 个")
                            await asyncio.sleep(1)
                    except Exception as e:
                        print(f"[51job] 设置 Cookie 失败: {e}")

            if self.user_data_dir:
                is_already_logged_in = await self.verify_logged_in(page)
                if is_already_logged_in:
                    print(f"[51job] 检测到已登录状态，复用登录态")
                    self._login_verified = True
                    await page.close()
                    return True

            login_url = f"{self.base_url}/pc/user/login"
            print(f"[51job] 访问登录页: {login_url}")
            await page.goto(login_url, wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(2)

            if self.user_data_dir:
                print(f"[51job] 等待验证登录状态...")
                for _ in range(10):
                    if await self.verify_logged_in(page):
                        print(f"[51job] 登录状态验证成功")
                        self._login_verified = True
                        await page.close()
                        return True
                    await asyncio.sleep(1)

            await self._save_cookies()

            print(f"[51job] 请手动在浏览器中登录...")
            for _ in range(15):
                is_logged_in = await self.verify_logged_in(page)
                if is_logged_in:
                    print(f"[51job] 手动登录成功")
                    self._login_verified = True
                    await self._save_cookies()
                    await page.close()
                    return True
                await asyncio.sleep(1)

            await page.close()
            return False

        except Exception as e:
            print(f"[51job] 登录异常: {e}")
            return False

    def _parse_cookie_string(self, cookie_string: str) -> List[Dict]:
        """解析 Cookie 字符串"""
        try:
            cookies = []
            for item in cookie_string.split(';'):
                item = item.strip()
                if '=' in item:
                    name, value = item.split('=', 1)
                    cookies.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.51job.com',
                        'path': '/',
                        'secure': True,
                        'httpOnly': False,
                    })
            return cookies
        except Exception as e:
            print(f"[51job] 解析 Cookie 失败: {e}")
            return []

    # ========== 搜索职位 ==========

    async def search_jobs(self, keyword: str, city: str = '深圳', page: int = 1) -> List[Dict]:
        """搜索职位 - 复用搜索页面翻页，像智联一样用正则提取"""
        jobs = []

        try:
            # 复用搜索页面，page=1时创建新页面，之后翻页复用
            if page == 1 or self._search_page is None or self._search_page.is_closed():
                if self._search_page and not self._search_page.is_closed():
                    await self._search_page.close()
                # new_page 会自动处理浏览器初始化
                self._search_page = await self.new_page()
                if not self._search_page:
                    print(f"[51job] 创建搜索页面失败")
                    return jobs
                await self._human_delay(500, 1500)
                await self._random_mouse_wander(self._search_page)

            p = self._search_page

            # 检查取消
            self._check_cancel()

            city_code = self._get_city_code(city)
            search_url = f'{self.base_url}/pc/search?jobArea={city_code}&searchType=2&keyword={keyword}&page={page}'
            print(f"[51job] 搜索: {keyword} @ {city} (城市代码: {city_code}, 页码: {page})")

            await p.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            self._check_cancel()  # 导航后检查取消
            await self._human_delay(2000, 4000)  # 等待Vue SPA渲染

            # 如果是第1页且需要选择城市
            if page == 1:
                print(f"[51job] 选择城市: {city}...")
                city_selectors = [
                    f'a.ch:has-text("{city}")',
                    f'a.ch.on:has-text("{city}")',
                    f'text="{city}"',
                ]
                city_selected = False
                for selector in city_selectors:
                    try:
                        city_elem = await p.query_selector(selector)
                        if city_elem:
                            elem_class = await city_elem.get_attribute('class') or ''
                            if 'on' in elem_class:
                                print(f"[51job] 城市 {city} 已经选中")
                                city_selected = True
                                break
                            await city_elem.click()
                            print(f"[51job] 点击城市筛选器: {selector}")
                            city_selected = True
                            await asyncio.sleep(1.5)
                            break
                    except Exception:
                        continue

                if not city_selected:
                    print(f"[51job] 未找到城市筛选器 {city}，继续执行...")

            # 像智联一样，用正则从原始HTML提取数据
            html_content = await p.content()
            print(f"[51job] 获取页面内容，长度: {len(html_content)}")

            # 51job的URL格式:
            # - 真正的职位详情页: https://jobs.51job.com/shenzhen/123456789.html (城市/纯数字ID.html)
            # - 列表页: https://jobs.51job.com/all/coBGNVNVMzUW8GYAVkBWk.html (不要)
            # - 校园招聘: https://jobs.51job.com/campus/... (不要)
            import re
            # 匹配所有包含数字ID的URL
            job_urls = re.findall(r'href=["\']([^"\']*(?:jobs\.51job\.com|job\.51job\.com)/[^"\']*\d+\.html)["\']', html_content, re.IGNORECASE)
            print(f"[51job] 正则提取到 {len(job_urls)} 个URL")

            # 过滤掉 /all/ 和 /campus/ 等无效页面
            job_urls = [u for u in job_urls if '/all/' not in u and '/campus/' not in u and '/search/' not in u]
            print(f"[51job] 过滤无效URL后剩余 {len(job_urls)} 个URL")

            # 去重 - 用job_id去重
            seen = set()
            unique_jobs = []
            for url in job_urls:
                url = url.strip()
                # 从URL提取job_id
                id_match = re.search(r'/(\d+)\.html', url)
                if not id_match:
                    continue
                job_id = id_match.group(1)
                if job_id in seen:
                    continue
                seen.add(job_id)
                unique_jobs.append((url, job_id))

            print(f"[51job] 去重后 {len(unique_jobs)} 个唯一URL")

            # 提取详细信息
            for job_url, job_id in unique_jobs:
                if not job_url.startswith('http'):
                    job_url = 'https://jobs.51job.com' + job_url if job_url.startswith('/') else f'https://jobs.51job.com/{job_url}'

                # 尝试从页面提取更多信息（简化版，找不到就算了）
                job_info = None
                try:
                    job_info = await p.evaluate(f"""(urlPart) => {{
                        const links = document.querySelectorAll('a[href*="jobs.51job"], a[href*="job.51job"]');
                        for (let link of links) {{
                            if (link.href.includes(urlPart)) {{
                                // 尝试找父容器
                                let container = link.closest('div');
                                if (!container) continue;

                                // 找最近的包含job关键字的容器
                                while (container && !container.className?.includes('job')) {{
                                    container = container.parentElement;
                                }}

                                if (container) {{
                                    const title = link.innerText?.trim() || link.title || '';
                                    const companyEl = container.querySelector('[class*="company"], [class*="cname"]');
                                    const company = companyEl?.innerText?.trim() || '';
                                    const salaryEl = container.querySelector('[class*="salary"]');
                                    const salary = salaryEl?.innerText?.trim() || '';
                                    const areaEl = container.querySelector('[class*="area"], [class*="location"]');
                                    const area = areaEl?.innerText?.trim() || '';
                                    return {{ title, company, salary, area }};
                                }}
                            }}
                        }}
                        return null;
                    }}""", job_id)
                except Exception:
                    pass

                # 安全地从job_info提取数据
                job_salary = ''
                job_title = ''
                job_company = ''
                job_area = ''
                if job_info and isinstance(job_info, dict):
                    job_salary = job_info.get('salary', '')
                    job_title = job_info.get('title', '')
                    job_company = job_info.get('company', '')
                    job_area = job_info.get('area', '')

                salary_min, salary_max = self._parse_salary(job_salary)

                job = {
                    'platform': 'job51',
                    'platform_job_id': job_id,
                    'title': job_title or f'职位{job_id}',
                    'company': job_company,
                    'city': city,
                    'area': job_area,
                    'salary': job_salary,
                    'salary_min': salary_min,
                    'salary_max': salary_max,
                    'source_url': job_url,
                    'url': job_url,
                }

                jobs.append(job)

            print(f"[51job] 最终解析得到 {len(jobs)} 个职位")
            return jobs

        except Exception as e:
            print(f"[51job] 搜索职位异常: {e}")
            import traceback
            traceback.print_exc()
            return jobs

    def _parse_salary(self, salary_text: str) -> Tuple[int, int]:
        """解析薪资文本"""
        if not salary_text or '面议' in salary_text or '薪' not in salary_text:
            return 0, 0

        import re
        pattern = r'(\d+\.?\d*)[万千]?-(\d+\.?\d*)[万千]?'
        match = re.search(pattern, salary_text)
        if match:
            min_val = float(match.group(1))
            max_val = float(match.group(2))
            if '万' in salary_text:
                min_val *= 10000
                max_val *= 10000
            elif '千' in salary_text:
                min_val *= 1000
                max_val *= 1000
            return int(min_val), int(max_val)
        return 0, 0

    CITY_CODE_MAP = {
        '北京': '010000', '上海': '020000', '广州': '030200', '深圳': '040000',
        '杭州': '080200', '南京': '070200', '苏州': '060200', '武汉': '180200',
        '成都': '090200', '重庆': '060000', '西安': '270200', '天津': '030000',
        '长沙': '190200', '郑州': '150200', '东莞': '030800', '佛山': '030700',
        '宁波': '080300', '青岛': '120200', '无锡': '070300', '济南': '150300',
        '合肥': '150200', '昆明': '250200', '沈阳': '230200', '大连': '230300',
        '福州': '110200', '厦门': '110300', '哈尔滨': '230100', '长春': '250100',
        '石家庄': '050200', '贵阳': '260200', '太原': '250200',
    }

    def _get_city_code(self, city: str) -> str:
        """获取城市代码"""
        return self.CITY_CODE_MAP.get(city, '040000')

    def _extract_city_from_area(self, area: str) -> str:
        """从地区中提取城市"""
        for city in ['深圳', '广州', '北京', '上海', '杭州', '南京', '苏州', '武汉', '成都', '重庆']:
            if city in area:
                return city
        return '深圳'

    def _extract_area(self, area: str) -> str:
        """从地区字符串中提取区县"""
        for city in ['深圳市', '广州市', '北京市', '上海市', '杭州市', '南京市', '苏州市', '武汉市', '成都市', '重庆市']:
            if area.startswith(city):
                return area[len(city):]
        return area

    def _extract_city(self, area: str) -> str:
        """从地区字符串中提取城市名"""
        if not area:
            return ''
        cities = ['北京', '上海', '广州', '深圳', '杭州', '南京', '苏州', '武汉',
                  '成都', '重庆', '西安', '天津', '长沙', '郑州', '东莞', '佛山',
                  '宁波', '青岛', '无锡', '济南', '合肥', '昆明', '沈阳', '大连',
                  '福州', '厦门', '哈尔滨', '长春', '石家庄', '贵阳', '太原']
        for city in cities:
            if city in area:
                return city
        return area

    # ========== 获取职位详情 ==========

    async def get_job_detail(self, job_url: str) -> Dict:
        """获取职位详情 - 人类行为模拟为主，事前防御策略"""
        detail = {}
        page = None

        try:
            # 检查取消
            self._check_cancel()

            page = await self.new_page(force_new=True)
            if not page:
                print(f"[51job] 创建新页面失败，无法获取详情")
                return detail

            # 直接访问详情页
            await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
            self._check_cancel()  # 导航后检查取消
            await self._human_delay(1000, 2000)

            # 打印实际 URL 和页面标题用于调试
            actual_url = page.url
            if actual_url and 'jobs.51job.com' not in actual_url:
                print(f"[51job] 详情页 URL 不对: {actual_url} (期望包含 jobs.51job.com)")

            # 滚动到顶部
            await page.evaluate("window.scrollTo(0, 0)")
            await self._human_delay(1000, 2000)

            # 随机滚动几次，模拟在浏览
            for _ in range(random.randint(2, 4)):
                await self._human_scroll(page, 'random')
                await self._human_delay(500, 1500)

            # 获取职位描述
            desc_elem = await page.query_selector('.job_msg')
            if not desc_elem:
                desc_elem = await page.query_selector('.job_detail')
            if not desc_elem:
                desc_elem = await page.query_selector('[class*="job_msg"]')
            description = await desc_elem.inner_text() if desc_elem else ''

            # 获取职位要求
            req_elem = await page.query_selector('.job_require')
            requirements = await req_elem.inner_text() if req_elem else ''

            # 获取标题和公司
            title_elem = await page.query_selector('h1')
            title = await title_elem.inner_text() if title_elem else ''
            company_elem = await page.query_selector('.c_name a')
            company = await company_elem.inner_text() if company_elem else ''

            # 调试日志
            print(f"[51job] 详情获取: title='{title[:30] if title else ''}', desc长度={len(description)}")

            # 检测验证码
            captcha_detected = False
            captcha_selectors = [
                '.geetest_panel', '.geetest_item', '.geetest_button',
                '.nc_wrapper', '.slider_knob',
                '[class*="captcha"]', '[class*="verify"]',
                '[class*="slider"]', '.nc_wrapper .slider',
            ]
            for cap_sel in captcha_selectors:
                cap_elem = await page.query_selector(cap_sel)
                if cap_elem:
                    is_visible = await cap_elem.is_visible()
                    if is_visible:
                        print(f"[51job] 检测到验证码元素: {cap_sel}")
                        captcha_detected = True
                        break

            # 离开前再随机移动一下鼠标
            await self._random_mouse_wander(page)
            await self._human_delay(300, 800)

            return {
                'title': title.strip() if title else '',
                'company': company.strip() if company else '',
                'description': description.strip() if description else '',
                'requirements': requirements.strip() if requirements else '',
                'captcha': captcha_detected,
            }

        except Exception as e:
            return {'description': '', 'requirements': '', 'error': str(e), 'captcha': False}

        finally:
            if page is not None:
                try:
                    if not page.is_closed():
                        await page.close()
                except Exception:
                    pass

    # ========== 投递职位 ==========

    async def apply_job(self, job_url: str, **kwargs) -> Dict:
        """投递职位"""
        result = {
            'success': False,
            'message': '',
            'status': 'unknown'
        }

        try:
            if not await self.ensure_browser_ready():
                print(f"[51job] 浏览器不可用，无法投递")
                result['message'] = '浏览器不可用'
                result['status'] = 'failed'
                return result

            page = await self.persistent_context.new_page()
            await page.goto('about:blank')
            await self._human_delay(500, 1500)
            await self._random_mouse_wander(page)

            print(f"[51job] 访问职位详情: {job_url}")
            await page.goto(job_url, wait_until='domcontentloaded')
            await self._human_delay(1000, 2000)

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.8)")
            await self._human_delay(500, 1000)

            apply_btn_selectors = [
                'button.btn_apply',
                '.btn_apply',
                'a.btn_apply',
                'button:has-text("投递简历")',
                'a:has-text("投递简历")',
            ]

            applied = False
            for selector in apply_btn_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn and await btn.is_visible():
                        print(f"[51job] 找到投递按钮: {selector}")
                        await btn.click()
                        await self._human_delay(1000, 2000)
                        applied = True
                        break
                except Exception:
                    continue

            if applied:
                confirm_selectors = [
                    'button.confirm',
                    '.confirm-btn',
                    'a:has-text("确认投递")',
                ]
                for selector in confirm_selectors:
                    try:
                        confirm_btn = await page.query_selector(selector)
                        if confirm_btn and await confirm_btn.is_visible():
                            await confirm_btn.click()
                            await self._human_delay(500, 1000)
                            break
                    except Exception:
                        continue

                result['success'] = True
                result['message'] = '投递成功'
                result['status'] = 'submitted'
                print(f"[51job] 投递成功")
            else:
                result['message'] = '未找到投递按钮'
                result['status'] = 'failed'
                print(f"[51job] 未找到投递按钮")

            await page.close()

        except Exception as e:
            print(f"[51job] 投递异常: {e}")
            result['message'] = str(e)
            result['status'] = 'error'

        return result
