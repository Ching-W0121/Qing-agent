from typing import List, Dict
from platforms.base import BasePlatform


class LiepinPlatform(BasePlatform):
    """猎聘平台适配器"""

    def __init__(self):
        super().__init__('猎聘')
        self.base_url = 'https://www.liepin.com'

    async def login(self, cookie: str = None, username: str = None, password: str = None) -> bool:
        """登录猎聘"""
        page = await self.new_page()

        try:
            await page.goto(f'{self.base_url}/')

            if cookie:
                await page.context.add_cookies([
                    {'name': 'liepin', 'value': cookie, 'url': self.base_url}
                ])
                await page.reload()
            else:
                await page.click('text=登录')
                await page.wait_for_selector('.username-input', timeout=10000)
                await page.fill('.username-input', username)
                await page.fill('.password-input', password)
                await page.click('.login-btn')
                await page.wait_for_load_state('networkidle')

            await page.close()
            return True

        except Exception as e:
            print(f"[猎聘] 登录失败: {e}")
            await page.close()
            return False

    async def search_jobs(self, keyword: str, city: str = '深圳', page: int = 1) -> List[Dict]:
        """搜索职位"""
        page = await self.new_page()
        jobs = []

        if not page:
            print(f"[猎聘] 创建页面失败，无法搜索")
            return jobs

        try:
            search_url = f'{self.base_url}/jobs/?keyword={keyword}&city={city}&curPage={page}'
            print(f"[猎聘] 搜索: {keyword} @ {city} (页码: {page})")

            await page.goto(search_url)
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)

            job_list = await page.query_selector_all('.job-card')

            for job_card in job_list:
                try:
                    job = await self._parse_job_card(job_card)
                    if job:
                        jobs.append(job)
                except:
                    continue

            print(f"[猎聘] 找到 {len(jobs)} 个职位")

        except Exception as e:
            print(f"[猎聘] 搜索失败: {e}")

        finally:
            if page:
                await page.close()

        return jobs

    async def _parse_job_card(self, card) -> Dict:
        """解析职位卡片"""
        try:
            title_elem = await card.query_selector('.job-title')
            company_elem = await card.query_selector('.company-name')
            salary_elem = await card.query_selector('.salary')

            return {
                'platform': 'liepin',
                'title': await title_elem.inner_text() if title_elem else '',
                'company': await company_elem.inner_text() if company_elem else '',
                'salary': await salary_elem.inner_text() if salary_elem else '',
            }
        except:
            return None

    async def get_job_detail(self, job_url: str) -> Dict:
        """获取职位详情"""
        page = await self.new_page()
        detail = {}

        if not page:
            print(f"[猎聘] 创建页面失败，无法获取详情")
            return detail

        try:
            await page.goto(job_url)
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)

            title_elem = await page.query_selector('.job-title')
            detail = {'title': await title_elem.inner_text() if title_elem else ''}

        except Exception as e:
            print(f"[猎聘] 获取详情失败: {e}")

        finally:
            if page:
                await page.close()

        return detail

    async def apply_job(self, job_url: str) -> Dict:
        """投递职位"""
        page = await self.new_page()
        result = {'success': False, 'message': '', 'status': ''}

        if not page:
            print(f"[猎聘] 创建页面失败，无法投递")
            result['message'] = '创建页面失败'
            result['status'] = 'failed'
            return result

        try:
            await page.goto(job_url)
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)

            apply_btn = await page.query_selector('button:has-text("立即投递")')

            if not apply_btn:
                result['message'] = '不可投递或已投递'
                result['status'] = 'not_applicable'
                if page:
                    await page.close()
                return result

            await apply_btn.click()
            await page.wait_for_timeout(3000)

            success_elem = await page.query_selector('text=已投递')
            if success_elem:
                result['success'] = True
                result['message'] = '投递成功'
                result['status'] = 'submitted'

        except Exception as e:
            result['message'] = f'投递失败: {e}'
            result['status'] = 'failed'

        finally:
            if page:
                await page.close()

        return result
