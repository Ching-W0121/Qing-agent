"""
爬虫任务执行器
调用 Playwright 进行职位搜索和采集(入库)
V3.1: 列表页优先,JD详情按需抓取
V3.3: Vision + Embedding + Decision Engine 智能执行
"""

import asyncio
import sys
import random
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

# 添加项目 playwright 目录到路径
# __file__ = backend/app/services/crawler_runner.py
# parent.parent.parent = backend/
# grandparent = qing-agent/
playwright_root = Path(__file__).parent.parent.parent.parent / 'playwright' / 'src'
sys.path.insert(0, str(playwright_root))

# Windows asyncio fix - must use ProactorEventLoop for subprocess support
if sys.platform == 'win32':
    asyncio.set_event_loop(asyncio.ProactorEventLoop())

from app.models.user import User
from app.models.job import Job
from app.models.application import Application, ApplicationStatus
from app.services.job_filter import JobFilterService
from app.services.phone_login_manager import phone_login_manager, PhoneLoginState

# V3.3 Services
from services.v3_crawler_runner import V3CrawlerRunner


class CrawlerRunner:
    """爬虫任务执行器"""

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.profile = self._get_profile()
        self.filter_service = JobFilterService(db, user_id)
        self.platform = None
        self.collected_count = 0

    def _get_profile(self) -> Optional[Dict]:
        """获取用户画像"""
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if not user:
            print(f"[DEBUG] User {self.user_id} not found")
            return None
        if not user.profile:
            print(f"[DEBUG] User {self.user_id} has no profile")
            return None
        p = user.profile
        print(f"[DEBUG] platform_credentials: {p.platform_credentials}")
        return {
            'directions': p.directions or ['planning'],
            'planning_daily_limit': getattr(p, 'planning_daily_limit', 10) or 10,
            'design_daily_limit': getattr(p, 'design_daily_limit', 10) or 10,
            'total_daily_limit': getattr(p, 'total_daily_limit', 20) or 20,
            'include_keywords': p.include_keywords or [],
            'prefer_keywords': p.prefer_keywords or [],
            'exclude_keywords': p.exclude_keywords or [],
            'platform_credentials': p.platform_credentials or {},
            'target_cities': p.target_cities or ['深圳'],
        }

    async def run_search_collect(self, platform_name: str = 'zhilian') -> Dict:
        """
        执行搜索+采集流程
        1. 初始化浏览器并登录
        2. 搜索职位
        3. 匹配过滤
        4. 采集入库直到达到上限
        """
        if not self.profile:
            return {'success': False, 'error': '用户画像未配置'}

        directions = self.profile.get('directions', ['planning'])
        planning_limit = self.profile.get('planning_daily_limit', 10)
        design_limit = self.profile.get('design_daily_limit', 10)
        total_limit = self.profile.get('total_daily_limit', 20)
        credentials = self.profile.get('platform_credentials', {}).get(platform_name, {})

        # 初始化平台
        if platform_name == 'zhilian':
            from platforms.zhilian import ZhilianPlatform
            self.platform = ZhilianPlatform()
        else:
            return {'success': False, 'error': f'不支持的平台: {platform_name}'}

        try:
            # 1. 初始化浏览器
            await self.platform.init(headless=True)

            # 2. 登录
            login_success = False
            if credentials.get('cookie'):
                login_success = await self.platform.login(cookie=credentials['cookie'])
            elif credentials.get('username') and credentials.get('password'):
                login_success = await self.platform.login(
                    username=credentials['username'],
                    password=credentials['password']
                )

            if not login_success:
                return {'success': False, 'error': '登录失败'}

            # 3. 搜索职位
            keywords = self.profile.get('include_keywords', ['品牌策划'])
            cities = self.profile.get('target_cities', ['深圳'])

            all_jobs = []
            for city in cities:  # 搜索所有城市
                for keyword in keywords:  # 搜索所有关键词
                    for page in range(1, 4):  # 每关键词搜索前3页
                        jobs = await self.platform.search_jobs(keyword, city, page)
                        if not jobs:
                            break  # 没有更多结果，停止翻页
                        all_jobs.extend(jobs)

                        # V3.1: 页间延迟（3-8秒），模拟人类翻页行为
                        if page < 3:  # 最后一页不需要等待
                            delay = random.uniform(3, 8)
                            print(f"[爬虫] 翻页等待 {delay:.1f}秒...")
                            await asyncio.sleep(delay)

            print(f"[爬虫] 共找到 {len(all_jobs)} 个职位")

            # 4. 匹配过滤
            matched_jobs = self._filter_jobs(all_jobs)

            # 5. 采集入库（V3.1: 只入库列表页数据，不立即抓取JD详情）
            collected = []
            failed_jobs = []  # 记录采集失败的职位
            for i, job in enumerate(matched_jobs[:total_limit]):
                result = await self._collect_job(job)

                if result['success']:
                    collected.append(result)
                else:
                    failed_jobs.append({
                        'job_title': job.get('title', ''),
                        'company': job.get('company', ''),
                        'source_url': job.get('source_url', ''),
                        'error': result.get('error', '')
                    })

                # V3.1: 低频抓取 - 每个职位处理后等待3-8秒
                if i < len(matched_jobs[:total_limit]) - 1:  # 最后一个不需要等
                    delay = random.uniform(3, 8)
                    print(f"[爬虫] 低频等待 {delay:.1f}秒...")
                    await asyncio.sleep(delay)

            return {
                'success': True,
                'searched': len(all_jobs),
                'matched': len(matched_jobs),
                'collected': len(collected),
                'failed_jobs': len(failed_jobs),
                'results': collected
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

        finally:
            if self.platform:
                await self.platform.close()

    def _filter_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """根据用户画像过滤职位"""
        filtered = []

        for job_data in jobs:
            # 创建临时 Job 对象用于过滤
            job = Job(
                platform=job_data.get('platform', 'zhilian'),
                platform_job_id=job_data.get('platform_job_id', job_data.get('job_id', '')),
                title=job_data.get('title', ''),
                company=job_data.get('company', ''),
                city=job_data.get('city', ''),
                area=job_data.get('area', ''),
                salary_min=job_data.get('salary_min', 0),
                salary_max=job_data.get('salary_max', 0),
                description=job_data.get('description', ''),
                requirements=job_data.get('requirements', ''),
            )

            keep, score, reason = self.filter_service.filter_job(job)
            if keep:
                filtered.append({**job_data, 'score': score, 'reason': reason})

        # 按分数排序
        filtered.sort(key=lambda x: x.get('score', 0), reverse=True)
        return filtered

    async def _collect_job(self, job: Dict) -> Dict:
        """采集单个职位 - V3.1版:只入库列表页数据,JD详情按需抓取"""
        try:
            job_url = job.get('source_url') or job.get('url')
            if not job_url:
                return {'success': False, 'job_title': job.get('title', ''), 'error': '无URL'}

            # V3.1: 不再立即抓取JD详情，只保存列表页数据
            # JD详情将在用户点击"查看详情"时按需抓取

            # 确保Job记录存在
            platform_job_id = job.get('platform_job_id') or job.get('job_id', '')
            db_job = self.db.query(Job).filter(
                Job.platform == job.get('platform', 'zhilian'),
                Job.platform_job_id == platform_job_id
            ).first()

            if not db_job:
                # 创建新Job记录（只使用列表页数据）
                db_job = Job(
                    platform=job.get('platform', 'zhilian'),
                    platform_job_id=platform_job_id,
                    title=job.get('title', ''),
                    company=job.get('company', ''),
                    city=job.get('city', ''),
                    area=job.get('area', ''),
                    salary_min=job.get('salary_min', 0),
                    salary_max=job.get('salary_max', 0),
                    description='',  # V3.1: 详情页按需抓取
                    requirements='',
                    source_url=job_url,
                    # V3.1: 新增字段
                    publish_time=datetime.utcnow(),  # 列表页有发布时间
                    is_exposed=False,  # 是否已推送给用户
                )
                self.db.add(db_job)
                self.db.commit()
                self.db.refresh(db_job)
            else:
                # 更新Job信息（使用列表页数据）
                if job.get('title') and len(job.get('title', '')) > len(db_job.title or ''):
                    db_job.title = job.get('title')
                if job.get('company') and len(job.get('company', '')) > len(db_job.company or ''):
                    db_job.company = job.get('company')
                if job.get('city'):
                    db_job.city = job.get('city')
                if job.get('area'):
                    db_job.area = job.get('area')
                if job.get('salary_min'):
                    db_job.salary_min = job.get('salary_min')
                if job.get('salary_max'):
                    db_job.salary_max = job.get('salary_max')
                db_job.source_url = job_url
                # V3.1: 标记为未暴露，等待推荐系统推送
                db_job.is_exposed = False
                self.db.commit()

            return {
                'success': True,
                'job_id': db_job.id,
                'job_title': db_job.title,
                'company': db_job.company,
            }

        except Exception as e:
            return {'success': False, 'job_title': job.get('title', ''), 'error': str(e)}

    async def fetch_job_detail_on_demand(self, job_id: int) -> Dict:
        """V3.1: 按需抓取JD详情（用户点击查看详情时调用）"""
        try:
            db_job = self.db.query(Job).filter(Job.id == job_id).first()
            if not db_job:
                return {'success': False, 'error': '职位不存在'}

            if not db_job.source_url:
                return {'success': False, 'error': '无详情页URL'}

            # 如果已经有详情，不再重复抓取
            if db_job.description and len(db_job.description) > 50:
                return {
                    'success': True,
                    'job_id': db_job.id,
                    'description': db_job.description,
                    'requirements': db_job.requirements,
                    'cached': True
                }

            # V3.1: 按需抓取详情
            if not self.platform:
                return {'success': False, 'error': '平台未初始化'}

            jd_result = await self.platform.get_job_detail(db_job.source_url)

            # 更新数据库
            if jd_result.get('description'):
                db_job.description = jd_result['description']
            if jd_result.get('requirements'):
                db_job.requirements = jd_result['requirements']
            self.db.commit()

            return {
                'success': True,
                'job_id': db_job.id,
                'description': jd_result.get('description', ''),
                'requirements': jd_result.get('requirements', ''),
                'cached': False
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}


async def run_job_collect_task(db: Session, user_id: int, platform: str = 'zhilian') -> Dict:
    """入口函数：运行职位采集任务"""
    runner = CrawlerRunner(db, user_id)
    return await runner.run_search_collect(platform)


async def run_v3_login(db: Session, user_id: int, platform: str = 'zhilian') -> Dict:
    """
    V3.3 登录执行入口
    使用 Vision + Embedding + Decision Engine 进行智能登录
    """
    try:
        # 获取用户凭证
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.profile:
            return {'success': False, 'error': '用户或用户画像不存在'}

        credentials = user.profile.platform_credentials or {}
        platform_cred = credentials.get(platform, {})

        # 初始化平台
        if platform == 'zhilian':
            from platforms.zhilian import ZhilianPlatform
            platform_obj = ZhilianPlatform()
        elif platform == 'boss':
            from platforms.boss import BossPlatform
            platform_obj = BossPlatform()
        elif platform == 'job51':
            from platforms.job51 import Job51Platform
            platform_obj = Job51Platform()
        else:
            return {'success': False, 'error': f'不支持的平台: {platform}'}

        # 使用 V3CrawlerRunner
        runner = V3CrawlerRunner(platform_obj, user_id, platform_cred)
        login_result = await runner.login_with_vision()  # 返回 Dict: {success, username, logs}

        # 关闭浏览器
        await platform_obj.close()

        return {
            'success': login_result.get('success', False),
            'username': login_result.get('username'),
            'logs': runner.get_execution_logs(),
            'learning_stats': runner.get_learning_stats()
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


async def run_v3_auto_apply(db: Session, user_id: int, job_url: str, platform: str = 'zhilian') -> Dict:
    """
    V3.4 自动投递执行入口
    使用 platform.apply_job() 为主路径，Vision 仅用于异常检测

    Args:
        db: 数据库 session
        user_id: 用户ID
        job_url: 职位详情页URL
        platform: 平台名称

    Returns:
        Dict: 投递结果
    """
    try:
        # 获取用户凭证
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.profile:
            return {'success': False, 'error': '用户或用户画像不存在'}

        credentials = user.profile.platform_credentials or {}
        platform_cred = credentials.get(platform, {})

        # 初始化平台
        if platform == 'zhilian':
            from platforms.zhilian import ZhilianPlatform
            platform_obj = ZhilianPlatform()
        elif platform == 'boss':
            from platforms.boss import BossPlatform
            platform_obj = BossPlatform()
        elif platform == 'job51':
            from platforms.job51 import Job51Platform
            platform_obj = Job51Platform()
        else:
            return {'success': False, 'error': f'不支持的平台: {platform}'}

        # 使用 V3CrawlerRunner
        runner = V3CrawlerRunner(platform_obj, user_id, platform_cred)
        result = await runner.apply_job_smart(job_url)  # V3.4 主路径优先策略

        # 关闭浏览器
        await platform_obj.close()

        return {
            **result,
            'logs': runner.get_execution_logs(),
            'learning_stats': runner.get_learning_stats()
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


async def run_v3_full_flow(db: Session, user_id: int, platform: str = 'zhilian', task_id: int = None, cancel_event=None) -> Dict:
    """
    V3.4 完整流程执行入口
    1. V3.4 智能登录
    2. 搜索并匹配职位
    3. 自动投递（platform.apply_job 主路径 + Vision异常检测）
    4. 学习投递结果

    Args:
        db: 数据库会话
        user_id: 用户ID
        platform: 平台名称
        task_id: 任务ID
        cancel_event: 取消事件对象 (asyncio.Event)
    """
    from app.services.task_event_manager import emit_task_step

    def is_cancelled():
        """检查是否已请求取消"""
        return cancel_event and not cancel_event.is_set()

    def check_cancellation():
        """检查取消并抛出异常"""
        if is_cancelled():
            raise asyncio.CancelledError("用户取消任务")

    async def cancellable_sleep(seconds: float):
        """可取消的睡眠，在睡眠期间也能响应取消"""
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < seconds:
            check_cancellation()
            await asyncio.sleep(0.5)  # 每0.5秒检查一次
            if is_cancelled():
                raise asyncio.CancelledError("用户取消任务")

    platform_obj = None
    runner = None
    return_result = None

    try:
        # 检查是否已请求取消（开始时）
        check_cancellation()

        # 获取用户凭证
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.profile:
            return_result = {'success': False, 'error': '用户或用户画像不存在'}
            return return_result

        profile = user.profile
        credentials = profile.platform_credentials or {}
        platform_cred = credentials.get(platform, {})

        # 初始化平台
        if platform == 'zhilian':
            from platforms.zhilian import ZhilianPlatform
            platform_obj = ZhilianPlatform()
        elif platform == 'job51':
            from platforms.job51 import Job51Platform
            platform_obj = Job51Platform()
        elif platform == 'boss':
            from platforms.boss import BossPlatform
            platform_obj = BossPlatform()
        else:
            return_result = {'success': False, 'error': f'不支持的平台: {platform}'}
            return return_result

        # 使用 V3CrawlerRunner
        runner = V3CrawlerRunner(platform_obj, user_id, platform_cred)

        # 注册浏览器控制器到全局注册表
        async def browser_controller(action: str, params: dict):
            """浏览器控制回调函数"""
            print(f"[BrowserController] 收到动作: {action}, params: {params}")
            platform_name = params.get('platform', 'zhilian')
            if action == "open_login_page":
                return await platform_obj.open_login_page()
            elif action == "input_phone":
                phone = params.get('phone', '')
                print(f"[BrowserController] input_phone被调用, phone: {phone}")
                return await platform_obj.input_phone_on_login_page(phone)
            elif action == "input_code":
                return await platform_obj.input_code_on_login_page(params.get('code', ''))
            elif action == "close_login_page":
                return await platform_obj.close_login_page()
            return None

        from app.services.browser_controller import browser_controller_registry
        await browser_controller_registry.register(platform, browser_controller)

        # 1. V3.3 登录
        if task_id:
            await emit_task_step(task_id, "login", "running", "正在登录...")
        print("[V3.3] 开始智能登录...")
        login_result = await runner.login_with_vision()

        # 检查是否已取消
        check_cancellation()

        if not login_result.get('success'):
            error_msg = login_result.get('error', '登录失败')
            print(f"[V3.3] 登录失败: {error_msg}")

            # 检查是否是 Cookie 问题，尝试手机验证码登录
            if 'Cookie' in error_msg or 'cookie' in error_msg.lower():
                if task_id:
                    await emit_task_step(task_id, "login", "failed", f"Cookie失效: {error_msg}")
                    await emit_task_step(task_id, "phone_login_required", "running", "Cookie失效，需要手机验证码登录", {})

                # 触发手机登录流程（phone_login_manager 已在模块级别导入）
                session = await phone_login_manager.create_session(user_id, platform)
                await phone_login_manager.set_state(user_id, PhoneLoginState.WAITING_PHONE, phone=None)

                # 打开登录页面
                controller = await browser_controller_registry.get_controller()
                if controller:
                    try:
                        await browser_controller_registry.execute("open_login_page", {"platform": platform})
                    except Exception as e:
                        print(f"[V3.3] 打开登录页失败: {e}")

                # 等待手机验证完成
                print("[V3.3] 等待手机验证码登录...")
                max_wait = 300  # 等待5分钟
                waited = 0
                while waited < max_wait:
                    await asyncio.sleep(2)
                    waited += 2
                    # 检查是否已取消
                    check_cancellation()
                    status = await phone_login_manager.get_status(user_id)
                    if status.get('state') == 'completed':
                        print("[V3.3] 手机验证码登录成功")
                        break
                    elif status.get('state') == 'failed':
                        print("[V3.3] 手机验证码登录失败")
                        break

                # 验证手机登录后是否成功
                login_result = await runner.login_with_vision()
                if not login_result.get('success'):
                    if task_id:
                        await emit_task_step(task_id, "login", "failed", "登录失败")
                    return {'success': False, 'error': '登录失败', 'username': login_result.get('username'), 'logs': runner.get_execution_logs()}
            else:
                if task_id:
                    await emit_task_step(task_id, "login", "failed", error_msg)
                return {'success': False, 'error': error_msg, 'username': login_result.get('username'), 'logs': runner.get_execution_logs()}

        if task_id:
            await emit_task_step(task_id, "login", "success", f"登录成功: {login_result.get('username')}", {"username": login_result.get('username')})
        print(f"[V3.3] 登录成功，用户: {login_result.get('username')}")

        # 检查是否已取消（登录后）
        check_cancellation()

        # 2. 搜索职位
        if task_id:
            await emit_task_step(task_id, "search", "running", "正在搜索职位...")
        print("[V3.3] 开始搜索职位...")
        keywords = profile.include_keywords or ['品牌策划']
        cities = profile.target_cities or ['深圳']

        all_jobs = []
        search_details = []
        for city in cities:
            for keyword in keywords:
                for page in range(1, 4):
                    # 检查是否已取消（搜索循环中）
                    check_cancellation()
                    jobs = await platform_obj.search_jobs(keyword, city, page)
                    if not jobs:
                        break
                    all_jobs.extend(jobs)
                    search_details.append(f"{keyword}@{city}第{page}页:{len(jobs)}条")
                    await cancellable_sleep(random.uniform(3, 8))

        if task_id:
            await emit_task_step(task_id, "search", "success", f"共找到 {len(all_jobs)} 个职位", {"count": len(all_jobs), "details": search_details})
        print(f"[V3.3] 共找到 {len(all_jobs)} 个职位")

        # 3.1 搜索结果去重（不同关键词可能返回相同职位）
        seen_job_ids = set()
        unique_jobs = []
        for job in all_jobs:
            job_id = job.get('platform_job_id') or job.get('job_id') or ''
            job_url = job.get('source_url') or job.get('url') or ''
            # 通过 job_id 或 URL 去重
            identifier = job_id or job_url
            if identifier and identifier not in seen_job_ids:
                seen_job_ids.add(identifier)
                unique_jobs.append(job)
            elif not identifier:
                # 如果没有ID或URL，也保留（兜底）
                unique_jobs.append(job)
        duplicate_count = len(all_jobs) - len(unique_jobs)
        all_jobs = unique_jobs
        if duplicate_count > 0:
            print(f"[V3.3] 搜索结果去重: 移除 {duplicate_count} 个重复职位")
        print(f"[V3.3] 去重后共 {len(all_jobs)} 个职位")

        # 检查是否已取消（搜索后）
        check_cancellation()

        # 3. 第一轮过滤（基于搜索页已有信息：标题/公司/薪资/城市）
        # 策略：只用标题和城市做粗筛选，不过度依赖description
        # 因为搜索页没有description，所有职位用简化评分
        if task_id:
            await emit_task_step(task_id, "filter", "running", "正在过滤职位...")
        filter_service = JobFilterService(db, user_id)
        profile = filter_service.profile
        matched_jobs = []
        reject_reasons = {}  # 统计过滤原因
        print(f"[V3.3] 第一轮过滤：基于搜索页信息过滤 {len(all_jobs)} 个职位...")

        # 从profile获取关键词用于第一轮过滤
        prefer_kws = [k.lower() for k in (profile.get('prefer_keywords') or [])]
        exclude_kws = [k.lower() for k in (profile.get('exclude_keywords') or [])]
        include_kws = [k.lower() for k in (profile.get('include_keywords') or [])]
        target_cities = profile.get('target_cities') or ['深圳']

        for job_data in all_jobs:
            check_cancellation()
            job = Job(
                platform=job_data.get('platform', 'zhilian'),
                platform_job_id=job_data.get('platform_job_id', job_data.get('job_id', '')),
                title=job_data.get('title', ''),
                company=job_data.get('company', ''),
                city=job_data.get('city', ''),
                area=job_data.get('area', ''),
                salary_min=job_data.get('salary_min', 0),
                salary_max=job_data.get('salary_max', 0),
                description=job_data.get('description', ''),
                requirements=job_data.get('requirements', ''),
            )

            # 第一轮过滤逻辑（简化版，不过度依赖description）
            title_lower = (job.title or '').lower()

            # 1. 检查城市
            if job.city not in target_cities:
                reject_reasons['城市不符'] = reject_reasons.get('城市不符', 0) + 1
                continue

            # 2. 检查排除关键词
            if any(kw in title_lower for kw in exclude_kws):
                reject_reasons['排除关键词'] = reject_reasons.get('排除关键词', 0) + 1
                continue

            # 3. 计算基础分数（只用标题，不依赖description）
            score = 0.0
            reason = "匹配"

            # 包含关键词命中
            if any(kw in title_lower for kw in include_kws):
                score += 0.5

            # 加分关键词命中
            if any(kw in title_lower for kw in prefer_kws):
                score += 0.3

            # 如果没有任何关键词匹配，给一个基础分让它进入详情验证
            if score == 0:
                score = 0.1  # 基础分，让它进入详情验证

            matched_jobs.append({**job_data, 'score': score, 'reason': reason})

        # 按分数排序
        matched_jobs.sort(key=lambda x: x.get('score', 0), reverse=True)
        print(f"[V3.3] 第一轮过滤完成，匹配 {len(matched_jobs)} 个职位")
        print(f"[V3.3] 过滤原因统计: {reject_reasons}")

        # 按分数排序
        matched_jobs.sort(key=lambda x: x.get('score', 0), reverse=True)
        print(f"[V3.3] 第一轮过滤完成，匹配 {len(matched_jobs)} 个职位")

        # 3.5 过滤已投递的职位（只过滤当前平台的）
        applied_identifiers = set()
        try:
            from app.models.application import Application, ApplicationStatus
            # 只查询当前平台的已投递记录，避免跨平台数据干扰
            platform_code = 'zhilian' if platform == 'zhilian' else 'job51'
            existing_applications = db.query(Application).filter(
                Application.user_id == user_id,
                Application.status.in_([ApplicationStatus.SUBMITTED, ApplicationStatus.ALREADY_APPLIED]),
                Application.platform == platform_code  # 按平台过滤
            ).all()
            for app in existing_applications:
                if app.job and app.job.platform_job_id:
                    applied_identifiers.add(app.job.platform_job_id)
                if app.apply_url:
                    applied_identifiers.add(app.apply_url)
                if app.job:
                    combo = f"{app.job.title}@{app.job.company}"
                    applied_identifiers.add(combo)
            print(f"[V3.3] 用户在 {platform} 已投递记录: {len(applied_identifiers)} 个")
        except Exception as e:
            print(f"[V3.3] 查询已投递记录失败: {e}")

        # 排除已投递的
        original_count = len(matched_jobs)
        filtered_by_applied = []
        for job in matched_jobs:
            job_id = job.get('platform_job_id') or job.get('job_id')
            job_url = job.get('source_url') or job.get('url') or ''
            job_combo = f"{job.get('title')}@{job.get('company')}"
            if (job_id and job_id in applied_identifiers) or \
               (job_url and job_url in applied_identifiers) or \
               (job_combo in applied_identifiers):
                print(f"[V3.3] 跳过已投递职位: {job.get('title')}")
                continue
            filtered_by_applied.append(job)
        matched_jobs = filtered_by_applied
        skipped_applied = original_count - len(matched_jobs)

        print(f"[V3.3] 排除已投递后，剩余 {len(matched_jobs)} 个匹配职位")

        # 4. 只为匹配上的职位获取详情（精准过滤）
        # 策略：匹配上的职位才进详情页，避免盲目获取大量详情触发验证
        if task_id:
            await emit_task_step(task_id, "filter", "running", f"正在获取 {len(matched_jobs)} 个匹配职位的详情...")
        print(f"[V3.3] 开始获取 {len(matched_jobs)} 个匹配职位的详情...")
        detail_success = 0
        detail_fail = 0
        captcha_count = 0
        base_delay = 2.0
        current_delay = base_delay
        final_matched = []  # 最终通过详情验证的职位

        for idx, job in enumerate(matched_jobs):
            check_cancellation()

            # 如果连续多次获取失败，增加延迟
            if captcha_count > 0 and captcha_count % 5 == 0:
                current_delay = min(current_delay * 1.5, 30)
                print(f"[V3.3] 连续触发验证码 {captcha_count} 次，增加延迟到 {current_delay:.1f} 秒")
                await cancellable_sleep(5)

            job_url = job.get('source_url') or job.get('url')
            if not job_url:
                continue

            try:
                detail = await platform_obj.get_job_detail(job_url)
                if detail.get('captcha'):
                    captcha_count += 1
                    print(f"[V3.3] 获取详情被验证码阻挡 (累计{captcha_count}次)")
                    extra_wait = min(10 + captcha_count * 2, 30)
                    print(f"[V3.3] 等待 {extra_wait:.0f} 秒让页面恢复...")
                    await cancellable_sleep(extra_wait)
                    # 验证码后停止获取详情，已匹配足够
                    print(f"[V3.3] 验证码恢复等待，停止详情获取，已有 {detail_success} 个详情")
                    break
                elif detail.get('description'):
                    job['description'] = detail.get('description', '')
                    job['requirements'] = detail.get('requirements', '')
                    captcha_count = 0
                    detail_success += 1
                    final_matched.append(job)
                elif detail.get('title'):
                    # 有title但没description，部分成功
                    job['title'] = detail.get('title', '')
                    job['company'] = detail.get('company', '')
                    job['area'] = detail.get('area', '')
                    # description为空说明被验证码阻挡了
                    print(f"[V3.3] 详情页被阻挡: title={detail.get('title')}, desc为空")
                    captcha_count += 1
                else:
                    print(f"[V3.3] 详情获取异常: job_url={job_url}")
                    captcha_count += 1

                if detail.get('requirements'):
                    job['requirements'] = detail.get('requirements', '')

            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[V3.3] 获取详情失败: {e}")
                detail_fail += 1
                captcha_count += 1

            await cancellable_sleep(random.uniform(current_delay * 0.7, current_delay * 1.3))

            if (idx + 1) % 10 == 0:
                print(f"[V3.3] 已获取 {idx+1}/{len(matched_jobs)} 个详情，成功:{detail_success} 失败:{detail_fail} 验证码:{captcha_count}")

        print(f"[V3.3] 详情获取完成，成功:{detail_success} 失败:{detail_fail} 验证码:{captcha_count}")

        # 5. 最终过滤（基于详情信息）
        final_jobs = []
        for job in final_matched:
            check_cancellation()
            job_obj = Job(
                platform=job.get('platform', 'zhilian'),
                platform_job_id=job.get('platform_job_id', job.get('job_id', '')),
                title=job.get('title', ''),
                company=job.get('company', ''),
                city=job.get('city', ''),
                area=job.get('area', ''),
                salary_min=job.get('salary_min', 0),
                salary_max=job.get('salary_max', 0),
                description=job.get('description', ''),
                requirements=job.get('requirements', ''),
            )
            # 最终验证：使用详情信息二次确认
            keep, score, reason = filter_service.filter_job(job_obj)
            if keep:
                final_jobs.append({**job, 'score': score, 'reason': reason})

        final_jobs.sort(key=lambda x: x.get('score', 0), reverse=True)
        matched_jobs = final_jobs

        if task_id:
            await emit_task_step(task_id, "filter", "success", f"匹配成功 {len(matched_jobs)} 个职位", {"count": len(matched_jobs)})
        print(f"[V3.3] 匹配成功 {len(matched_jobs)} 个职位")

        # 检查是否已取消（过滤后，投递前）
        check_cancellation()

        # 5. 自动投递（使用 V3.3 智能投递）
        total_limit = profile.get('total_daily_limit', 20) or 20
        applied_count = 0
        apply_results = []

        for i, job in enumerate(matched_jobs[:total_limit]):
            # 检查是否请求了取消
            if cancel_event and not cancel_event.is_set():
                print("[V3.3] 检测到取消请求，停止投递")
                return_result = {
                    'success': False,
                    'error': '用户取消任务',
                    'jobs_found': len(all_jobs),
                    'jobs_matched': len(matched_jobs),
                    'applied_count': applied_count,
                    'apply_results': apply_results,
                    'stopped': True,
                    'stopped_by_user': True
                }
                return return_result

            job_url = job.get('source_url') or job.get('url')
            if not job_url:
                continue

            # 发送投递步骤开始
            if task_id:
                await emit_task_step(
                    task_id, "apply_start", "running",
                    f"投递 {i+1}/{min(len(matched_jobs), total_limit)}: {job.get('title')}",
                    {"index": i+1, "total": min(len(matched_jobs), total_limit), "job": job.get('title'), "company": job.get('company')}
                )

            print(f"[V3.4] 投递第 {i+1}/{min(len(matched_jobs), total_limit)} 个职位: {job.get('title')}")

            # 使用 V3.4 投递（主路径优先策略）
            if task_id:
                await emit_task_step(task_id, "apply", "running", "正在投递...")
            result = await runner.apply_job_smart(job_url, company=job.get('company', ''), title=job.get('title', ''))

            # 获取决策信息并发送SSE事件
            decision = result.get('decision', {})
            if decision and task_id:
                await emit_task_step(
                    task_id, "decision", "success",
                    f"AI选择: {decision.get('selected_button', '未知')}",
                    decision
                )

            # 获取投递验证详情
            delivery_verify = result.get('delivery_verify', {})
            is_verified = delivery_verify.get('is_delivered', False) if delivery_verify else False

            apply_results.append({
                'job_title': job.get('title'),
                'company': job.get('company'),
                'job_url': job_url,
                'result': result.get('result', 'unknown'),
                'success': result.get('success', False),
                'verified': is_verified,
                'verify_details': delivery_verify
            })

            if result.get('success') and result.get('result') == 'success':
                applied_count += 1

                # 发送投递成功
                if task_id:
                    await emit_task_step(
                        task_id, "apply_success", "success",
                        f"投递成功: {job.get('title')}",
                        {"job": job.get('title'), "company": job.get('company'), "verified": is_verified}
                    )

                # 保存投递记录到数据库
                try:
                    # 确保 Job 记录存在
                    platform_job_id = job.get('platform_job_id') or job.get('job_id', '')
                    db_job = db.query(Job).filter(
                        Job.platform == platform,
                        Job.platform_job_id == platform_job_id
                    ).first()

                    if not db_job:
                        # 创建新 Job 记录
                        db_job = Job(
                            platform=platform,
                            platform_job_id=platform_job_id,
                            title=job.get('title', ''),
                            company=job.get('company', ''),
                            city=job.get('city', ''),
                            area=job.get('area', ''),
                            salary_min=job.get('salary_min', 0),
                            salary_max=job.get('salary_max', 0),
                            source_url=job_url,
                            publish_time=datetime.utcnow(),
                            is_exposed=True
                        )
                        db.add(db_job)
                        db.commit()
                        db.refresh(db_job)

                    # 创建投递记录
                    app_record = Application(
                        user_id=user_id,
                        job_id=db_job.id,
                        platform=platform,
                        status=ApplicationStatus.SUBMITTED,
                        applied_at=datetime.utcnow(),
                        apply_url=job_url,
                        apply_note=f"V3.3智能投递 - 验证状态:{result.get('result')}, 已确认:{is_verified}"
                    )
                    db.add(app_record)
                    db.commit()
                    print(f"[V3.3] 保存投递记录成功: {job.get('title')}")
                except Exception as e:
                    print(f"[V3.3] 保存投递记录失败: {e}")
                    db.rollback()
            else:
                # 检查是否是登录问题导致的失败
                error_msg = result.get('error', '')
                is_login_error = error_msg in ['LOGIN_FAIL', 'CAPTCHA_REQUIRED', 'cookie_expired'] or \
                                 'Cookie' in error_msg or '登录' in error_msg or '验证码' in error_msg

                if is_login_error:
                    # 发送需要手机验证的通知
                    if task_id:
                        await emit_task_step(
                            task_id, "phone_login_required", "running",
                            "需要登录，请使用手机验证码登录",
                            {"job": job.get('title'), "company": job.get('company')}
                        )

                    # 创建手机登录会话
                    session = await phone_login_manager.create_session(user_id, platform)
                    await phone_login_manager.set_state(user_id, PhoneLoginState.WAITING_PHONE)

                    print(f"[V3.3] 检测到登录问题，暂停等待用户手机验证...")

                    # 暂停任务，等待用户完成验证
                    # 轮询检查登录状态，最多等待 300 秒（5分钟）
                    wait_count = 0
                    max_wait = 300  # 5分钟

                    while wait_count < max_wait:
                        await asyncio.sleep(2)
                        wait_count += 2

                        # 检查是否被取消
                        if cancel_event and not cancel_event.is_set():
                            print("[V3.3] 任务被取消")
                            await phone_login_manager.clear_session(user_id)
                            return_result = {
                                'success': False,
                                'error': '用户取消任务',
                                'jobs_found': len(all_jobs),
                                'jobs_matched': len(matched_jobs),
                                'applied_count': applied_count,
                                'apply_results': apply_results,
                                'stopped': True,
                                'stopped_by_user': True
                            }
                            return return_result

                        # 检查登录状态
                        status = await phone_login_manager.get_status(user_id)
                        if status['state'] == PhoneLoginState.COMPLETED.value:
                            print(f"[V3.3] 用户完成手机验证，继续投递")
                            await phone_login_manager.clear_session(user_id)

                            # 重新验证登录状态
                            if task_id:
                                await emit_task_step(
                                    task_id, "phone_login_completed", "success",
                                    "手机验证完成，重新开始投递"
                                )
                            break
                        elif status['state'] == PhoneLoginState.FAILED.value:
                            print(f"[V3.3] 手机验证失败: {status.get('error')}")
                            await phone_login_manager.clear_session(user_id)

                            # 跳过这个职位，继续下一个
                            if task_id:
                                await emit_task_step(
                                    task_id, "phone_login_failed", "failed",
                                    f"手机验证失败: {status.get('error')}"
                                )
                            break

                    if wait_count >= max_wait:
                        print(f"[V3.3] 等待手机验证超时")
                        await phone_login_manager.clear_session(user_id)

                # 发送投递失败
                if task_id:
                    await emit_task_step(
                        task_id, "apply_failed", "failed",
                        f"投递失败: {job.get('title')} - {result.get('error', '未知错误')}",
                        {"job": job.get('title'), "company": job.get('company'), "error": result.get('error')}
                    )

            # 低频等待（使用可取消的sleep）
            if i < len(matched_jobs[:total_limit]) - 1:
                await cancellable_sleep(random.uniform(3, 8))

        # 关闭浏览器
        await platform_obj.close()

        return_result = {
            'success': True,
            'username': login_result.get('username'),
            'jobs_found': len(all_jobs),
            'jobs_matched': len(matched_jobs),
            'applied_count': applied_count,
            'apply_results': apply_results,
            'logs': runner.get_execution_logs(),
            'learning_stats': runner.get_learning_stats()
        }

    except asyncio.CancelledError:
        # 任务被取消
        print("[V3.3] 任务被用户取消")
        return_result = {
            'success': False,
            'error': '用户取消任务',
            'stopped': True,
            'stopped_by_user': True
        }

    except Exception as e:
        return_result = {'success': False, 'error': str(e)}

    finally:
        # 关闭浏览器
        if platform_obj:
            try:
                await platform_obj.close()
                print("[V3.3] 浏览器已关闭")
            except Exception as e:
                print(f"[V3.3] 关闭浏览器时出错: {e}")

        # 取消注册浏览器控制器
        from app.services.browser_controller import browser_controller_registry
        try:
            await browser_controller_registry.unregister()
        except Exception as e:
            print(f"[V3.3] 取消注册浏览器控制器时出错: {e}")

    return return_result
