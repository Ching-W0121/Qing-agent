"""
职位过滤与匹配服务
根据用户画像规则过滤职位
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.job import Job


class JobFilterService:
    """职位过滤服务"""

    # 打分权重
    SCORE_BRAND = 0.4       # 涉及品牌
    SCORE_STRATEGY = 0.3    # 涉及策略
    SCORE_CREATIVE = 0.2    # 涉及创意
    SCORE_EXECUTION = -0.5  # 仅执行

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.profile = self._get_user_profile()
        self.jobs = []  # 过滤后的职位

    def _get_user_profile(self) -> Optional[Dict]:
        """获取用户画像配置"""
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if not user or not user.profile:
            return None

        p = user.profile
        return {
            'directions': p.directions or ['planning'],
            'include_keywords': p.include_keywords or [],
            'prefer_keywords': p.prefer_keywords or [],
            'exclude_keywords': p.exclude_keywords or [],
            'prefer_companies': p.prefer_companies or [],
            'exclude_companies': p.exclude_companies or [],
            'prefer_industries': p.prefer_industries or [],
            'exclude_industries': p.exclude_industries or [],
            'fuzzy_keywords': p.fuzzy_keywords or [],
            'scoring_threshold': p.scoring_threshold or 0.5,
            'target_cities': p.target_cities or ['深圳'],
            'exclude_areas': p.exclude_areas or [],
            'salary_min': p.salary_min or 0,
            'salary_max': p.salary_max or 999999,
            'experience_min': p.experience_min or 0,
            'experience_max': p.experience_max or 99,
        }

    def _calculate_score(self, job: Job) -> float:
        """计算职位匹配分数"""
        if not self.profile:
            return 0.0

        score = 0.0
        title = (job.title or '').lower()
        description = ((job.description or '') + (job.requirements or '')).lower()

        # 检查排除关键词（直接排除）
        for exclude_kw in self.profile['exclude_keywords']:
            if exclude_kw.lower() in title or exclude_kw.lower() in description:
                return -1.0  # 排除

        # 检查加分关键词
        for prefer_kw in self.profile['prefer_keywords']:
            if prefer_kw.lower() in title or prefer_kw.lower() in description:
                score += 0.3  # 加分关键词命中

        # 模糊岗位需要二次打分
        is_fuzzy = False
        for fuzzy_kw in self.profile['fuzzy_keywords']:
            if fuzzy_kw.lower() in title:
                is_fuzzy = True
                break

        if is_fuzzy:
            # 二次打分
            if '品牌' in title:
                score += self.SCORE_BRAND
            if any(kw in description for kw in ['策略', '战略', '方案', '规划']):
                score += self.SCORE_STRATEGY
            if any(kw in description for kw in ['创意', '策划', 'idea', 'concept']):
                score += self.SCORE_CREATIVE
            if any(kw in description for kw in ['执行', '落地', '跟进', '操作']):
                score += self.SCORE_EXECUTION
        else:
            # 非模糊岗位，直接检查 include 关键词
            for include_kw in self.profile['include_keywords']:
                if include_kw.lower() in title:
                    score += 0.5
                    break

        return score

    def filter_job(self, job: Job) -> Tuple[bool, float, str]:
        """
        过滤单个职位
        返回: (是否保留, 分数, 原因)
        """
        if not self.profile:
            return True, 0.0, "无画像配置"

        # 1. 检查城市
        if job.city not in self.profile['target_cities']:
            return False, 0.0, f"城市不符: {job.city}"

        # 2. 检查排除区域
        for area in self.profile['exclude_areas']:
            if area and area in (job.area or ''):
                return False, 0.0, f"排除区域: {area}"

        # 3. 检查薪资
        if job.salary_max and job.salary_max < self.profile['salary_min']:
            return False, 0.0, f"薪资过低: {job.salary_max}"
        if job.salary_min and job.salary_min > self.profile['salary_max']:
            return False, 0.0, f"薪资过高: {job.salary_min}"

        # 4. 计算匹配分数
        score = self._calculate_score(job)

        # 5. 检查排除关键词
        if score < 0:
            return False, 0.0, "命中排除关键词"

        # 6. 检查阈值
        threshold = self.profile['scoring_threshold']
        if score < threshold:
            return False, score, f"分数不足: {score:.2f} < {threshold}"

        return True, score, "匹配"

    def filter_jobs(self, jobs: List[Job]) -> List[Dict]:
        """
        过滤职位列表
        返回过滤后的职位详情列表
        """
        if not self.profile:
            return []

        results = []
        for job in jobs:
            keep, score, reason = self.filter_job(job)
            if keep:
                results.append({
                    'job': job,
                    'score': score,
                    'reason': reason
                })

        # 按分数排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results


def match_jobs_for_user(db: Session, user_id: int, raw_jobs: List[Dict]) -> List[Dict]:
    """
    为用户匹配职位
    1. 创建/更新 Job 记录
    2. 根据用户画像过滤
    3. 返回匹配结果
    """
    from app.models.job import Job
    from app.models.application import Application

    filter_service = JobFilterService(db, user_id)
    matched_jobs = []

    for job_data in raw_jobs:
        # 创建或获取 Job 记录
        existing_job = db.query(Job).filter(
            Job.platform == job_data['platform'],
            Job.platform_job_id == job_data['platform_job_id']
        ).first()

        if existing_job:
            job = existing_job
        else:
            job = Job(
                platform=job_data['platform'],
                platform_job_id=job_data['platform_job_id'],
                title=job_data['title'],
                company=job_data['company'],
                city=job_data.get('city', '深圳'),
                area=job_data.get('area'),
                salary_min=job_data.get('salary_min'),
                salary_max=job_data.get('salary_max'),
                experience=job_data.get('experience'),
                education=job_data.get('education'),
                description=job_data.get('description'),
                requirements=job_data.get('requirements'),
                skills=job_data.get('skills', []),
                industry=job_data.get('industry'),
                source_url=job_data.get('source_url'),
            )
            db.add(job)
            db.commit()
            db.refresh(job)

        # 过滤
        keep, score, reason = filter_service.filter_job(job)

        # 检查是否已投递
        existing_application = db.query(Application).filter(
            Application.user_id == user_id,
            Application.job_id == job.id
        ).first()

        matched_jobs.append({
            'job_id': job.id,
            'platform': job.platform,
            'title': job.title,
            'company': job.company,
            'city': job.city,
            'area': job.area,
            'salary': f"{job.salary_min/1000:.0f}K-{job.salary_max/1000:.0f}K" if job.salary_min and job.salary_max else '薪资面议',
            'score': score,
            'reason': reason,
            'matched': keep,
            'already_applied': existing_application is not None,
            'source_url': job.source_url,
        })

    # 过滤只保留匹配的，并按分数排序
    matched_jobs = [j for j in matched_jobs if j['matched']]
    matched_jobs.sort(key=lambda x: x['score'], reverse=True)

    return matched_jobs
