# backend/app/services/recommendation.py
# V3.1 阶段2: 增强匹配与推荐引擎
from app.core.database import SessionLocal
from app.models.job import Job
from app.models.user_behavior import UserBehavior
from app.models.user_profile import UserProfile
from app.services.job_pool import JobPool
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import math


class RecommendationEngine:
    """推荐引擎 V3.1 - 基于用户画像、行为和动态权重进行推荐"""

    # V3.1: 基础权重配置（可被用户行为调整）
    BASE_WEIGHTS = {
        'keyword': 0.25,      # 关键词匹配
        'salary': 0.20,       # 薪资匹配
        'city': 0.15,         # 城市匹配
        'area': 0.10,         # 区域匹配
        'industry': 0.10,      # 行业匹配
        'prefer_keyword': 0.10,  # 加分关键词
        'time_decay': 0.10,   # 时间衰减
    }

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.db = SessionLocal()
        # V3.1: 动态权重（基于用户行为学习）
        self.weights = self._learn_weights_from_behavior()

    def _learn_weights_from_behavior(self) -> Dict[str, float]:
        """
        V3.1: 基于用户历史行为学习动态权重
        - 如果用户经常点击某类职位，该类因素权重提高
        - 如果用户忽略某类职位，该类因素权重降低
        """
        weights = self.BASE_WEIGHTS.copy()

        # 获取用户最近30天的行为
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        behaviors = self.db.query(UserBehavior).filter(
            UserBehavior.user_id == self.user_id,
            UserBehavior.created_at >= thirty_days_ago
        ).all()

        if not behaviors:
            return weights

        # 统计各类行为的数量
        action_counts = {'view': 0, 'click': 0, 'like': 0, 'dislike': 0, 'apply': 0}
        for b in behaviors:
            if b.action in action_counts:
                action_counts[b.action] += 1

        total_actions = sum(action_counts.values())
        if total_actions < 5:
            return weights  # 行为数据太少，不做调整

        # V3.1: 根据行为调整权重
        # 如果用户经常点击但很少dislike，说明关键词匹配重要
        click_rate = action_counts['click'] / total_actions
        like_rate = action_counts['like'] / total_actions
        dislike_rate = action_counts['dislike'] / total_actions

        # 如果dislike率高，降低关键词权重，提高行业权重（可能关键词对但行业不对）
        if dislike_rate > 0.2:
            weights['keyword'] *= 0.8
            weights['industry'] *= 1.3
            weights['prefer_keyword'] *= 0.9

        # 如果like率高但click率低，说明推荐准确
        if like_rate > 0.1 and click_rate < 0.3:
            weights['keyword'] *= 1.1
            weights['city'] *= 1.1

        # 如果用户经常apply，说明推荐很准，保持权重
        apply_rate = action_counts['apply'] / total_actions
        if apply_rate > 0.1:
            weights['keyword'] *= 1.2
            weights['salary'] *= 1.1

        # 归一化权重
        total = sum(weights.values())
        weights = {k: v/total for k, v in weights.items()}

        return weights

    def get_user_profile(self) -> Optional[UserProfile]:
        """获取用户画像"""
        return self.db.query(UserProfile).filter(
            UserProfile.user_id == self.user_id
        ).first()

    def get_exposed_job_ids(self) -> set:
        """获取已推送过的职位ID"""
        behaviors = self.db.query(UserBehavior).filter(
            UserBehavior.user_id == self.user_id,
            UserBehavior.action.in_(['view', 'click', 'like', 'dislike'])
        ).all()
        return {b.job_id for b in behaviors}

    def get_applied_job_ids(self) -> set:
        """获取已投递的职位ID"""
        behaviors = self.db.query(UserBehavior).filter(
            UserBehavior.user_id == self.user_id,
            UserBehavior.action == 'apply'
        ).all()
        return {b.job_id for b in behaviors}

    def _get_liked_job_titles(self) -> List[str]:
        """V3.1: 获取用户喜欢的职位标题关键词"""
        behaviors = self.db.query(UserBehavior).filter(
            UserBehavior.user_id == self.user_id,
            UserBehavior.action.in_(['like', 'apply'])
        ).all()
        job_ids = [b.job_id for b in behaviors]
        if not job_ids:
            return []
        jobs = self.db.query(Job).filter(Job.id.in_(job_ids)).all()
        return [job.title.lower() for job in jobs if job.title]

    def _get_disliked_job_titles(self) -> List[str]:
        """V3.1: 获取用户不喜欢的职位标题关键词"""
        behaviors = self.db.query(UserBehavior).filter(
            UserBehavior.user_id == self.user_id,
            UserBehavior.action == 'dislike'
        ).all()
        job_ids = [b.job_id for b in behaviors]
        if not job_ids:
            return []
        jobs = self.db.query(Job).filter(Job.id.in_(job_ids)).all()
        return [job.title.lower() for job in jobs if job.title]

    def _calculate_time_decay(self, job: Job) -> float:
        """V3.1: 计算时间衰减因子（越新的职位分数越高）"""
        if not job.publish_time:
            return 0.5  # 无发布时间，默认中间值

        days_since_publish = (datetime.utcnow() - job.publish_time).days
        if days_since_publish <= 0:
            return 1.0  # 今天发布
        elif days_since_publish >= 7:
            return 0.3  # 7天前发布
        else:
            # 线性衰减: 1天=1.0, 7天=0.3
            return 1.0 - (days_since_publish - 1) * 0.1

    def calculate_match_score(self, job: Job, profile) -> tuple:
        """
        V3.1: 动态匹配分数，结合技能、城市、薪资、发布时间、用户行为
        返回: (分数, 匹配原因列表, 详细分数字典)
        """
        score = 0.0
        reasons = []
        score_details = {}

        # ===== 1. 关键词匹配 (动态权重) =====
        keyword_score = 0.0
        include_keywords = profile.include_keywords or []
        if include_keywords:
            job_text = f"{job.title} {job.company}".lower()
            keyword_matches = [kw for kw in include_keywords if kw.lower() in job_text]
            if keyword_matches:
                keyword_score = min(len(keyword_matches) * 0.15, 0.4)  # 最多0.4
                reasons.append(f"关键词: {', '.join(keyword_matches[:3])}")
        score_details['keyword'] = keyword_score

        # ===== 2. 加分关键词 (V3.1新增) =====
        prefer_score = 0.0
        prefer_keywords = profile.prefer_keywords or []
        if prefer_keywords:
            job_text = f"{job.title} {job.company}".lower()
            prefer_matches = [kw for kw in prefer_keywords if kw.lower() in job_text]
            if prefer_matches:
                prefer_score = min(len(prefer_matches) * 0.08, 0.16)
                reasons.append(f"加分: {', '.join(prefer_matches[:2])}")
        score_details['prefer_keyword'] = prefer_score

        # ===== 3. 薪资匹配 (动态权重) =====
        salary_score = 0.0
        if job.salary_min and profile.salary_min:
            # 薪资在期望范围内
            if profile.salary_min <= job.salary_min <= (profile.salary_max or 999999):
                salary_score = self.weights['salary']
                reasons.append("薪资符合")
            # 薪资略低于期望但可接受
            elif job.salary_min >= profile.salary_min * 0.8:
                salary_score = self.weights['salary'] * 0.5
                reasons.append("薪资略低")
        elif not job.salary_min:
            salary_score = self.weights['salary'] * 0.3  # 面议给部分分数
        score_details['salary'] = salary_score

        # ===== 4. 城市匹配 (动态权重) =====
        city_score = 0.0
        if job.city in (profile.target_cities or []):
            city_score = self.weights['city']
            reasons.append(f"城市: {job.city}")
        score_details['city'] = city_score

        # ===== 5. 区域匹配 (V3.1优化) =====
        area_score = 0.0
        exclude_areas = profile.exclude_areas or []
        if job.area:
            if job.area not in exclude_areas:
                area_score = self.weights['area']
                if job.area:
                    reasons.append(f"区域: {job.area}")
            # 如果在排除列表，给负分
            else:
                area_score = -0.1
        score_details['area'] = area_score

        # ===== 6. 行业匹配 (V3.1新增) =====
        industry_score = 0.0
        prefer_industries = profile.prefer_industries or []
        if prefer_industries and job.industry:
            if any(ind in job.industry for ind in prefer_industries):
                industry_score = self.weights['industry']
                reasons.append(f"行业匹配")
        score_details['industry'] = industry_score

        # ===== 7. 时间衰减 (V3.1新增) =====
        time_decay_score = self.weights['time_decay'] * self._calculate_time_decay(job)
        score_details['time_decay'] = time_decay_score

        # ===== 8. 用户行为反馈调整 (V3.1新增) =====
        liked_titles = self._get_liked_job_titles()
        disliked_titles = self._get_disliked_job_titles()
        job_title_lower = job.title.lower() if job.title else ''

        behavior_adjustment = 0.0
        # 如果用户喜欢过类似职位，加分
        for liked in liked_titles[:5]:  # 只看最近5个
            if liked in job_title_lower or job_title_lower in liked:
                behavior_adjustment += 0.05
                break

        # 如果用户不喜欢过类似职位，减分
        for disliked in disliked_titles[:3]:
            if disliked in job_title_lower or job_title_lower in disliked:
                behavior_adjustment -= 0.1
                break

        score_details['behavior'] = behavior_adjustment

        # ===== 计算总分 =====
        score = (keyword_score + prefer_score + salary_score + city_score +
                area_score + industry_score + time_decay_score + behavior_adjustment)

        return max(0.0, min(score, 1.0)), reasons, score_details

    def recommend(self, limit: int = 20, min_score: float = 0.3) -> List[Dict]:
        """
        V3.1: 获取推荐职位列表
        - 支持Top-N推荐
        - 支持最低分数过滤
        - 返回推荐理由
        """
        profile = self.get_user_profile()
        if not profile:
            return []

        exposed_ids = self.get_exposed_job_ids()
        applied_ids = self.get_applied_job_ids()

        # 获取候选池（最近3天）
        jobs = JobPool.get_recent_jobs(days=3)

        # 过滤和评分
        recommendations = []
        for job in jobs:
            # 跳过已投递的
            if job.id in applied_ids:
                continue

            score, reasons, score_details = self.calculate_match_score(job, profile)

            # V3.1: 过滤低于最低分数的
            if score < min_score:
                continue

            # 薪资范围格式化
            if job.salary_min:
                salary_str = f"{job.salary_min//1000}K-{job.salary_max//1000}K" if job.salary_max else f"{job.salary_min//1000}K+"
            else:
                salary_str = "面议"

            recommendations.append({
                'job_id': job.id,
                'title': job.title,
                'company': job.company,
                'city': job.city,
                'area': job.area,
                'salary': salary_str,
                'salary_min': job.salary_min,
                'salary_max': job.salary_max,
                'industry': job.industry,
                'match_score': round(score * 100),  # 转为百分比
                'match_score_raw': round(score, 3),  # 原始分数
                'match_reasons': reasons,
                'score_breakdown': {k: round(v, 3) for k, v in score_details.items()},
                'source_url': job.source_url,
                'is_applied': job.id in applied_ids,
                'is_exposed': job.id in exposed_ids,
                'publish_time': job.publish_time.isoformat() if job.publish_time else None,
            })

        # 按匹配度排序
        recommendations.sort(key=lambda x: x['match_score'], reverse=True)

        # 标记已推送（用于去重）
        newly_exposed = []
        for rec in recommendations:
            if rec['job_id'] not in exposed_ids:
                self.record_behavior(rec['job_id'], 'view')
                newly_exposed.append(rec['job_id'])

        # 返回Top-N
        return recommendations[:limit]

    def recommend_for_feed(self, limit: int = 10, offset: int = 0) -> Dict:
        """
        V3.1: 为Job Feed提供推荐
        返回格式更适合前端展示
        """
        profile = self.get_user_profile()
        if not profile:
            return {'jobs': [], 'total': 0, 'has_more': False}

        exposed_ids = self.get_exposed_job_ids()
        applied_ids = self.get_applied_job_ids()

        # 获取候选池
        jobs = JobPool.get_recent_jobs(days=3)

        # 过滤和评分
        recommendations = []
        for job in jobs:
            if job.id in applied_ids:
                continue

            score, reasons, score_details = self.calculate_match_score(job, profile)
            if score < 0.2:  # Feed只显示分数>=20%的
                continue

            salary_str = f"{job.salary_min//1000}K-{job.salary_max//1000}K" if job.salary_min else "面议"

            # V3.1: 判断是否已曝光
            is_new = job.id not in exposed_ids

            recommendations.append({
                'job_id': job.id,
                'title': job.title,
                'company': job.company,
                'city': job.city,
                'area': job.area,
                'salary': salary_str,
                'match_score': round(score * 100),
                'match_reasons': reasons,
                'source_url': job.source_url,
                'is_applied': job.id in applied_ids,
                'is_new': is_new,  # 是否是新曝光的
                'publish_time': job.publish_time.isoformat() if job.publish_time else None,
            })

        # 排序：新品优先，然后按分数
        recommendations.sort(key=lambda x: (not x['is_new'], -x['match_score']))

        total = len(recommendations)
        paginated = recommendations[offset:offset + limit]

        # 标记新曝光的职位
        for rec in paginated:
            if rec['is_new']:
                self.record_behavior(rec['job_id'], 'view')

        return {
            'jobs': paginated,
            'total': total,
            'has_more': offset + limit < total,
            'weights': {k: round(v, 3) for k, v in self.weights.items()},  # V3.1: 返回当前权重
        }

    def record_behavior(self, job_id: int, action: str):
        """记录用户行为"""
        behavior = UserBehavior(
            user_id=self.user_id,
            job_id=job_id,
            action=action
        )
        self.db.add(behavior)
        self.db.commit()

    def get_recommendation_explanation(self, job_id: int) -> Dict:
        """
        V3.1: 获取某个职位的详细推荐解释
        """
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {'error': 'Job not found'}

        profile = self.get_user_profile()
        if not profile:
            return {'error': 'Profile not found'}

        score, reasons, score_details = self.calculate_match_score(job, profile)

        # 获取类似职位的推荐历史
        similar_jobs = []
        liked_titles = self._get_liked_job_titles()
        if liked_titles:
            job_title_lower = job.title.lower() if job.title else ''
            for liked in liked_titles[:3]:
                if liked in job_title_lower or job_title_lower in liked:
                    similar_jobs.append(liked)
                    if len(similar_jobs) >= 3:
                        break

        return {
            'job_id': job_id,
            'title': job.title,
            'company': job.company,
            'match_score': round(score * 100),
            'match_reasons': reasons,
            'score_breakdown': {k: round(v, 3) for k, v in score_details.items()},
            'weights': {k: round(v, 3) for k, v in self.weights.items()},
            'similar_liked_jobs': similar_jobs,
            'recommendation_tip': self._generate_tip(score, reasons, liked_titles),
        }

    def _generate_tip(self, score: float, reasons: List[str], liked_titles: List[str]) -> str:
        """V3.1: 生成推荐提示语"""
        if score >= 0.8:
            return "这是为您精选的高匹配职位，强烈推荐！"
        elif score >= 0.6:
            return "匹配度较高，符合您的求职偏好。"
        elif score >= 0.4:
            if any('关键词' in r for r in reasons):
                return "职位关键词与您匹配，可以尝试投递。"
            return "基础条件符合，不妨了解一下。"
        else:
            return "根据您的偏好推荐，您可以先查看详情再决定。"

    def close(self):
        self.db.close()