# Job Feed + Recommendation 系统重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将求职Agent从"自动投递"重构为"智能推荐+用户决策"系统

**Architecture:**
- 前端改为Job Feed流展示（类似抖音信息流）
- Playwright仅用于数据采集（不再投递）
- 后端新增Job Pool、推荐引擎、行为追踪
- 核心：匹配度评分 + 匹配原因解释

**Tech Stack:** Vue3 + FastAPI + Playwright + SQLite

---

## 架构变化

```
旧架构:
搜索 → 匹配 → 自动投递 ❌

新架构:
Playwright采集 → Job Pool → Matching + Ranking → 推荐列表 → 用户决策
                                                        ↓
                                              行为追踪 → 推荐进化
```

---

## Task 1: 数据库模型扩展

**Files:**
- Create: `backend/app/models/user_behavior.py`
- Modify: `backend/app/models/job.py`
- Modify: `backend/alembic/versions/002_add_user_behavior.py`

- [ ] **Step 1: 创建 user_behavior 模型**

```python
# backend/app/models/user_behavior.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from app.core.database import Base
import datetime

class UserBehavior(Base):
    __tablename__ = "user_behaviors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    action = Column(String(20))  # view, click, like, dislike, apply, favorite
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
```

- [ ] **Step 2: 修改 job 模型，添加 publish_time 和 tags**

```python
# 在 job.py 中添加
from sqlalchemy import Column, String, JSON, DateTime
import datetime

# 添加字段
publish_time = Column(DateTime, default=datetime.datetime.utcnow)
tags = Column(JSON, default=list)  # 职位标签
source = Column(String(50), default="zhilian")  # 来源平台
is_exposed = Column(Boolean, default=False)  # 是否已推送给用户
```

- [ ] **Step 3: 创建数据库迁移**

```bash
cd backend
alembic revision --autogenerate -m "Add user_behavior and job fields"
alembic upgrade head
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/models/user_behavior.py backend/app/models/job.py
git add backend/alembic/versions/002_*.py
git commit -m "feat: add user behavior model and job fields"
```

---

## Task 2: Job Pool 服务

**Files:**
- Create: `backend/app/services/job_pool.py`
- Modify: `backend/app/models/job.py`

- [ ] **Step 1: 创建 job_pool 服务**

```python
# backend/app/services/job_pool.py
from app.core.database import SessionLocal
from app.models.job import Job
from datetime import datetime, timedelta

class JobPool:
    """Job Pool 管理：只保留最近3天的职位"""

    @staticmethod
    def get_recent_jobs(days: int = 3):
        """获取最近N天的职位"""
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            jobs = db.query(Job).filter(
                Job.publish_time >= cutoff
            ).order_by(Job.publish_time.desc()).all()
            return jobs
        finally:
            db.close()

    @staticmethod
    def clean_old_jobs(days: int = 7):
        """清理超过N天的职位"""
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            db.query(Job).filter(
                Job.publish_time < cutoff
            ).delete()
            db.commit()
        finally:
            db.close()
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/job_pool.py
git commit -m "feat: add job pool service"
```

---

## Task 3: 推荐引擎

**Files:**
- Create: `backend/app/services/recommendation.py`
- Modify: `backend/app/services/job_pool.py`

- [ ] **Step 1: 创建推荐引擎**

```python
# backend/app/services/recommendation.py
from app.core.database import SessionLocal
from app.models.job import Job
from app.models.user_behavior import UserBehavior
from app.models.user_profile import UserProfile
from app.services.job_pool import JobPool
from typing import List, Dict

class RecommendationEngine:
    """推荐引擎 - 基于用户画像和行为进行推荐"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.db = SessionLocal()

    def get_user_profile(self):
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

    def calculate_match_score(self, job: Job, profile) -> tuple:
        """计算职位匹配度，返回(分数, 匹配原因列表)"""
        score = 0.0
        reasons = []

        # 关键词匹配 (40%)
        include_keywords = profile.include_keywords or []
        job_text = f"{job.title} {job.company}".lower()
        keyword_matches = [kw for kw in include_keywords if kw.lower() in job_text]
        if keyword_matches:
            score += 0.4
            reasons.append(f"关键词: {', '.join(keyword_matches[:3])}")

        # 薪资匹配 (30%)
        if job.salary_min and profile.salary_min:
            if job.salary_min >= profile.salary_min * 0.8:
                score += 0.3
                reasons.append("薪资符合")

        # 城市匹配 (20%)
        if job.city in (profile.target_cities or []):
            score += 0.2
            reasons.append(f"城市: {job.city}")

        # 区域排除 (10%)
        exclude_areas = profile.exclude_areas or []
        if job.area and job.area not in exclude_areas:
            score += 0.1
            reasons.append("区域符合")

        return min(score, 1.0), reasons

    def recommend(self, limit: int = 20) -> List[Dict]:
        """获取推荐职位列表"""
        profile = self.get_user_profile()
        if not profile:
            return []

        exposed_ids = self.get_exposed_job_ids()
        applied_ids = self.get_applied_job_ids()

        # 获取候选池
        jobs = JobPool.get_recent_jobs(days=3)

        # 过滤和评分
        recommendations = []
        for job in jobs:
            if job.id in applied_ids:
                continue

            score, reasons = self.calculate_match_score(job, profile)

            recommendations.append({
                'job_id': job.id,
                'title': job.title,
                'company': job.company,
                'city': job.city,
                'area': job.area,
                'salary': f"{job.salary_min//1000}K-{job.salary_max//1000}K" if job.salary_min else "面议",
                'match_score': round(score * 100),  # 转为百分比
                'match_reasons': reasons,
                'source_url': job.source_url,
                'is_applied': job.id in applied_ids
            })

        # 按匹配度排序
        recommendations.sort(key=lambda x: x['match_score'], reverse=True)

        # 标记已推送
        for rec in recommendations:
            if rec['job_id'] not in exposed_ids:
                self.record_behavior(rec['job_id'], 'view')

        return recommendations[:limit]

    def record_behavior(self, job_id: int, action: str):
        """记录用户行为"""
        behavior = UserBehavior(
            user_id=self.user_id,
            job_id=job_id,
            action=action
        )
        self.db.add(behavior)
        self.db.commit()

    def close(self):
        self.db.close()
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/recommendation.py
git commit -m "feat: add recommendation engine with scoring"
```

---

## Task 4: API 接口扩展

**Files:**
- Create: `backend/app/api/recommendations.py`
- Modify: `backend/app/api/jobs.py`

- [ ] **Step 1: 创建推荐API**

```python
# backend/app/api/recommendations.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.recommendation import RecommendationEngine

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("/recommend/{user_id}")
def get_recommendations(user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """获取推荐职位列表"""
    engine = RecommendationEngine(user_id)
    try:
        recommendations = engine.recommend(limit=limit)
        return recommendations
    finally:
        engine.close()

@router.post("/action")
def record_action(job_id: int, user_id: int, action: str, db: Session = Depends(get_db)):
    """记录用户行为"""
    engine = RecommendationEngine(user_id)
    try:
        engine.record_behavior(job_id, action)
        return {"success": True}
    finally:
        engine.close()
```

- [ ] **Step 2: 修改 main.py 注册路由**

```python
# backend/app/main.py - 添加新路由
from app.api.recommendations import router as recommendations_router

app.include_router(recommendations_router)
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/recommendations.py backend/app/main.py
git commit -m "feat: add recommendation API endpoints"
```

---

## Task 5: 前端 Job Card 组件

**Files:**
- Create: `frontend/src/components/JobCard.vue`

- [ ] **Step 1: 创建 JobCard 组件**

```vue
<!-- frontend/src/components/JobCard.vue -->
<template>
  <div class="job-card">
    <div class="job-header">
      <h3 class="job-title">{{ job.title }}</h3>
      <span class="match-score" :class="scoreClass">{{ job.match_score }}%</span>
    </div>

    <div class="company-name">{{ job.company }}</div>

    <div class="job-info">
      <span class="salary">{{ job.salary }}</span>
      <span class="location">{{ job.city }} {{ job.area }}</span>
    </div>

    <div class="match-reasons" v-if="job.match_reasons?.length">
      <span class="reason-tag" v-for="reason in job.match_reasons" :key="reason">
        {{ reason }}
      </span>
    </div>

    <div class="job-actions">
      <a :href="job.source_url" target="_blank" class="btn-detail">查看详情</a>
      <button @click="handleAction('like')" class="btn-action">👍 感兴趣</button>
      <button @click="handleAction('dislike')" class="btn-action">👎 不感兴趣</button>
      <button @click="handleAction('apply')" class="btn-apply" :disabled="job.is_applied">
        {{ job.is_applied ? '已投递' : '📌 投递' }}
      </button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  job: Object
})

const emit = defineEmits(['action'])

const scoreClass = computed(() => {
  if (props.job.match_score >= 80) return 'high'
  if (props.job.match_score >= 60) return 'medium'
  return 'low'
})

const handleAction = (action) => {
  emit('action', { job_id: props.job.job_id, action })
}
</script>

<style scoped>
.job-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.job-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.match-score {
  padding: 4px 12px;
  border-radius: 20px;
  font-weight: bold;
}
.match-score.high { background: #e6f7e6; color: #52c41a; }
.match-score.medium { background: #fffbe6; color: #faad14; }
.match-score.low { background: #fff1f0; color: #ff4d4f; }
.match-reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 0;
}
.reason-tag {
  background: #f0f5ff;
  color: #1890ff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.job-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.btn-apply:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/JobCard.vue
git commit -m "feat: add JobCard component with match score"
```

---

## Task 6: Dashboard 重构为 Job Feed

**Files:**
- Modify: `frontend/src/views/Dashboard.vue`

- [ ] **Step 1: 重构 Dashboard 为 Job Feed**

```javascript
// 在 Dashboard.vue 中添加
const jobFeed = ref([])
const loading = ref(false)

const fetchRecommendations = async () => {
  loading.value = true
  try {
    const userId = localStorage.getItem('user_id') || 1
    const res = await api.get(`/api/jobs/recommend/${userId}`)
    jobFeed.value = res || []
  } catch (e) {
    console.error('获取推荐失败:', e)
  } finally {
    loading.value = false
  }
}

const handleJobAction = async ({ job_id, action }) => {
  try {
    await api.post('/api/jobs/action', { job_id, user_id: 1, action })
    // 更新本地状态
    const job = jobFeed.value.find(j => j.job_id === job_id)
    if (job) {
      if (action === 'like') job.is_liked = true
      if (action === 'apply') job.is_applied = true
    }
  } catch (e) {
    console.error('记录行为失败:', e)
  }
}

onMounted(() => {
  fetchRecommendations()
})
```

- [ ] **Step 2: 模板更新为 Feed 流**

```vue
<!-- 替换原有的表格部分 -->
<div class="job-feed" v-if="jobFeed.length">
  <JobCard
    v-for="job in jobFeed"
    :key="job.job_id"
    :job="job"
    @action="handleJobAction"
  />
</div>
<div v-else-if="!loading" class="empty-state">
  暂无推荐职位，请先采集数据
</div>
```

- [ ] **Step 3: 移除旧的投递表格，保留统计卡片**

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/Dashboard.vue
git commit -m "refactor: transform Dashboard to Job Feed"
```

---

## Task 7: 数据采集任务调整

**Files:**
- Modify: `backend/app/services/crawler_runner.py`
- Modify: `backend/app/api/tasks.py`

- [ ] **Step 1: 修改 crawler_runner，只采集不投递**

```python
# 修改 run_search_apply 方法
async def run_search_apply(self, total_limit: int = 10) -> Dict:
    """搜索 + 入库（不再投递）"""
    # ... 搜索逻辑不变 ...

    # 改为入库而不是投递
    for job_data in matched_jobs[:total_limit]:
        # 创建或更新 Job 记录
        job = Job(...)
        self.db.add(job)
    self.db.commit()

    return {
        'success': True,
        'collected': len(matched_jobs),
        'added': len(matched_jobs[:total_limit])
    }
```

- [ ] **Step 2: 修改任务状态文案**

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/crawler_runner.py
git commit -m "refactor: crawler only collects jobs, no auto-apply"
```

---

## Task 8: 集成测试

- [ ] **Step 1: 测试数据采集**

```bash
curl -X POST http://localhost:8000/api/tasks/run \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "task_type": "collect"}'
```

- [ ] **Step 2: 测试推荐API**

```bash
curl http://localhost:8000/api/jobs/recommend/1
```

- [ ] **Step 3: 测试行为记录**

```bash
curl -X POST "http://localhost:8000/api/jobs/action?job_id=1&user_id=1&action=view"
```

- [ ] **Step 4: 前端测试** - 访问 http://localhost:5173 查看 Job Feed

---

## 总结

完成以上任务后，系统将从：

| 旧系统 | 新系统 |
|---------|---------|
| 搜索→匹配→自动投递 | 采集→候选池→推荐→用户决策 |
| 分页列表 | Job Feed 信息流 |
| 无匹配解释 | 87%匹配 + 匹配原因 |
| 无法进化 | 👍👎📌→推荐进化 |

用户可以通过"👍 感兴趣"和"👎 不感兴趣"来训练推荐系统，让它越来越懂你的偏好。
