# Job Application Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable full job search → match → auto-apply flow with browser automation

**Architecture:**
1. User configures profile + platform credentials in Profile page
2. User clicks "立即运行" in Dashboard
3. Backend triggers Playwright to search jobs on zhilian.com using user's credentials
4. Backend matches jobs against user's profile filters
5. Backend auto-applies to matched jobs until `daily_apply_limit` is reached
6. Results stored in DB and displayed in "最近投递"

**Tech Stack:** FastAPI, Playwright, SQLAlchemy, Vue 3

---

## File Structure

```
backend/
├── app/
│   ├── models/
│   │   ├── user_profile.py      # MODIFY: add daily_apply_limit
│   │   └── task_run.py           # MODIFY: add result_data field
│   ├── schemas/
│   │   ├── user.py              # MODIFY: add daily_apply_limit
│   │   └── task.py              # MODIFY: add fields
│   ├── api/
│   │   ├── tasks.py             # MODIFY: implement actual task execution
│   │   └── matching.py          # MODIFY: add batch apply endpoint
│   └── services/
│       ├── job_filter.py        # MODIFY: add search integration
│       └── crawler_runner.py     # CREATE: run Playwright crawler
├── playwright/
│   └── src/
│       └── platforms/
│           ├── zhilian.py        # MODIFY: fix selectors, add full flow
│           └── base.py          # ALREADY EXISTS

frontend/
├── src/
│   ├── views/
│   │   ├── Profile.vue          # MODIFY: add credentials + daily limit
│   │   └── Dashboard.vue        # MODIFY: show task progress
│   └── api/
│       └── index.js             # MODIFY: add task status polling
```

---

## Task 1: Update UserProfile Model - Add daily_apply_limit

**Files:**
- Modify: `backend/app/models/user_profile.py`
- Modify: `backend/app/schemas/user.py`

- [ ] **Step 1: Add daily_apply_limit column to UserProfile**

In `backend/app/models/user_profile.py`, after line 52 (`experience_max`):

```python
    # ===== 投递配置 =====
    # 每日投递上限
    daily_apply_limit = Column(Integer, default=10)
```

- [ ] **Step 2: Add daily_apply_limit to UserProfileUpdate schema**

In `backend/app/schemas/user.py`, after line 39:

```python
    daily_apply_limit: Optional[int] = None
```

- [ ] **Step 3: Verify backend imports work**

Run: `cd /c/Users/TR/qing-agent/backend && python -c "from app.models.user_profile import UserProfile; from app.schemas.user import UserProfileUpdate; print('OK')"`

Expected: OK

- [ ] **Step 4: Commit**

```bash
cd /c/Users/TR/qing-agent
git add backend/app/models/user_profile.py backend/app/schemas/user.py
git commit -m "feat: add daily_apply_limit to user profile"
```

---

## Task 2: Create Platform Credentials UI

**Files:**
- Modify: `frontend/src/views/Profile.vue`

**Changes needed:**
1. Add collapsible credentials section at bottom of Profile page
2. Add "今日投递数量" input field after "求职方向"

- [ ] **Step 1: Add daily_apply_limit input after direction selector**

Find in Profile.vue (around line 29 where direction selector ends):

```vue
        </div>

        <!-- 今日投递数量 -->
        <div class="form-card">
          <h3>投递设置</h3>
          <div class="form-group">
            <label>今日投递上限</label>
            <input v-model.number="profile.daily_apply_limit" type="number" min="1" max="100" placeholder="10" />
            <span class="helper-text">每日自动投递的最大职位数量</span>
          </div>
        </div>

        <!-- 平台凭证 -->
        <div class="form-card credentials-card">
```

- [ ] **Step 2: Add credentials section (collapsible)**

Find the last `</section>` before `</template>` and add before it:

```vue
        <!-- 平台凭证 -->
        <div class="form-card credentials-card">
          <div class="card-header" @click="showCredentials = !showCredentials">
            <h3>🔐 平台账号配置</h3>
            <span class="toggle-icon">{{ showCredentials ? '▼' : '▶' }}</span>
          </div>

          <div v-if="showCredentials" class="credentials-content">
            <p class="helper-text">输入 Cookie 或用户名密码，用于自动登录求职平台</p>

            <div class="platform-section">
              <h4>智联招聘</h4>
              <div class="form-group">
                <label>Cookie</label>
                <textarea v-model="credentials.zhilian.cookie" placeholder="粘贴 Cookie 字符串..." rows="2"></textarea>
              </div>
              <div class="divider-text">或</div>
              <div class="form-row">
                <div class="form-group">
                  <label>用户名</label>
                  <input v-model="credentials.zhilian.username" type="text" placeholder="手机号/邮箱" />
                </div>
                <div class="form-group">
                  <label>密码</label>
                  <input v-model="credentials.zhilian.password" type="password" placeholder="密码" />
                </div>
              </div>
            </div>
          </div>
        </div>
```

- [ ] **Step 3: Add script variables and methods**

Add to `<script setup>`:

```javascript
// 今日投递数量
const newDailyApplyLimit = ref(profile.value.daily_apply_limit || 10)

// 平台凭证
const showCredentials = ref(false)
const credentials = ref({
  zhilian: {
    cookie: '',
    username: '',
    password: ''
  }
})

// Load credentials from profile on mount
const loadCredentials = () => {
  if (profile.value.platform_credentials?.zhilian) {
    credentials.value.zhilian = {
      ...credentials.value.zhilian,
      ...profile.value.platform_credentials.zhilian
    }
  }
}
```

- [ ] **Step 4: Update saveProfile to include credentials and daily_apply_limit**

In the `saveProfile` function, add to the payload:

```javascript
    await api.put(`/users/${userId}/profile`, {
      // ... existing fields ...
      daily_apply_limit: profile.value.daily_apply_limit,
      platform_credentials: credentials.value
    })
```

- [ ] **Step 5: Add credentials CSS**

Add before `</style>`:

```css
/* Credentials Card */
.credentials-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}

.toggle-icon {
  font-size: 12px;
  color: #666;
}

.credentials-content {
  margin-top: 16px;
}

.platform-section {
  margin-top: 16px;
  padding: 16px;
  background: #f9f9f9;
  border-radius: 8px;
}

.platform-section h4 {
  margin-bottom: 12px;
  font-size: 14px;
  color: #333;
}

.divider-text {
  text-align: center;
  color: #999;
  font-size: 12px;
  margin: 12px 0;
}

.credentials-content textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
}
```

- [ ] **Step 6: Test build**

Run: `cd /c/Users/TR/qing-agent/frontend && npm run build 2>&1 | tail -5`

Expected: Build succeeds

- [ ] **Step 7: Commit**

```bash
cd /c/Users/TR/qing-agent
git add frontend/src/views/Profile.vue
git commit -m "feat: add platform credentials UI and daily apply limit"
```

---

## Task 3: Create Crawler Runner Service

**Files:**
- Create: `backend/app/services/crawler_runner.py`

- [ ] **Step 1: Create crawler_runner.py**

```python
"""
爬虫任务执行器
调用 Playwright 进行职位搜索和投递
"""

import asyncio
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.job import Job
from app.models.application import Application, ApplicationStatus
from app.services.job_filter import JobFilterService


class CrawlerRunner:
    """爬虫任务执行器"""

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.profile = self._get_profile()
        self.filter_service = JobFilterService(db, user_id)
        self.platform = None
        self.applied_count = 0

    def _get_profile(self) -> Optional[Dict]:
        """获取用户画像"""
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if not user or not user.profile:
            return None
        p = user.profile
        return {
            'direction': p.direction or 'planning',
            'include_keywords': p.include_keywords or [],
            'prefer_keywords': p.prefer_keywords or [],
            'exclude_keywords': p.exclude_keywords or [],
            'platform_credentials': p.platform_credentials or {},
            'target_cities': p.target_cities or ['深圳'],
            'daily_apply_limit': getattr(p, 'daily_apply_limit', 10),
        }

    async def run_search_apply(self, platform_name: str = 'zhilian') -> Dict:
        """
        执行搜索+投递流程
        1. 初始化浏览器并登录
        2. 搜索职位
        3. 匹配过滤
        4. 自动投递直到达到上限
        """
        if not self.profile:
            return {'success': False, 'error': '用户画像未配置'}

        daily_limit = self.profile.get('daily_apply_limit', 10)
        credentials = self.profile.get('platform_credentials', {}).get(platform_name, {})

        # 初始化平台
        if platform_name == 'zhilian':
            from playwright.src.platforms.zhilian import ZhilianPlatform
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
            for city in cities[:1]:  # 先只搜索第一个城市
                for keyword in keywords[:2]:  # 先只搜索前两个关键词
                    jobs = await self.platform.search_jobs(keyword, city)
                    all_jobs.extend(jobs)

            # 4. 匹配过滤
            matched_jobs = self._filter_jobs(all_jobs)

            # 5. 自动投递
            applied = []
            for job in matched_jobs[:daily_limit]:
                result = await self._apply_job(job)
                if result['success']:
                    applied.append(result)

            return {
                'success': True,
                'searched': len(all_jobs),
                'matched': len(matched_jobs),
                'applied': len(applied),
                'results': applied
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

    async def _apply_job(self, job: Dict) -> Dict:
        """投递单个职位"""
        try:
            job_url = job.get('source_url') or job.get('url')
            if not job_url:
                return {'success': False, 'job_title': job.get('title', ''), 'error': '无URL'}

            result = await self.platform.apply_job(job_url)

            # 记录到数据库
            existing = self.db.query(Application).filter(
                Application.user_id == self.user_id,
                Application.job_id == job.get('job_id')
            ).first()

            if not existing:
                application = Application(
                    user_id=self.user_id,
                    job_id=job.get('job_id'),
                    platform=job.get('platform', 'zhilian'),
                    status=ApplicationStatus.SUBMITTED if result.get('success') else ApplicationStatus.FAILED,
                    apply_url=job_url,
                    failed_reason=result.get('message') if not result.get('success') else None
                )
                self.db.add(application)
                self.db.commit()

            return {
                'success': result.get('success', False),
                'job_title': job.get('title', ''),
                'company': job.get('company', ''),
                'message': result.get('message', '')
            }

        except Exception as e:
            return {'success': False, 'job_title': job.get('title', ''), 'error': str(e)}


async def run_job_application_task(db: Session, user_id: int, platform: str = 'zhilian') -> Dict:
    """入口函数：运行求职任务"""
    runner = CrawlerRunner(db, user_id)
    return await runner.run_search_apply(platform)
```

- [ ] **Step 2: Test import**

Run: `cd /c/Users/TR/qing-agent/backend && python -c "from app.services.crawler_runner import run_job_application_task; print('OK')" 2>&1`

Expected: OK (may show import warning, that's fine)

- [ ] **Step 3: Commit**

```bash
cd /c/Users/TR/qing-agent
git add backend/app/services/crawler_runner.py
git commit -m "feat: add crawler runner service for job search and apply"
```

---

## Task 4: Update Tasks API - Implement Actual Task Execution

**Files:**
- Modify: `backend/app/api/tasks.py`

- [ ] **Step 1: Rewrite tasks.py to run actual task**

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.task_run import TaskRun, TaskType, TaskStatus
from app.schemas.task import TaskCreate, TaskResponse
from app.services.crawler_runner import run_job_application_task
import asyncio

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.post("/run", response_model=TaskResponse)
async def trigger_task(task: TaskCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """触发任务"""
    # 创建任务记录
    task_run = TaskRun(
        user_id=task.user_id,
        task_type=TaskType(task.task_type),
        status=TaskStatus.RUNNING
    )
    db.add(task_run)
    db.commit()
    db.refresh(task_run)

    # 后台执行
    background_tasks.add_task(execute_task, task_run.id, task.user_id, task.task_type, db)

    return task_run

async def execute_task(task_id: int, user_id: int, task_type: str, db: Session):
    """执行任务"""
    from app.models.task_run import TaskRun, TaskStatus

    try:
        # 运行爬虫
        result = await run_job_application_task(db, user_id, 'zhilian')

        # 更新任务状态
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            task_run.status = TaskStatus.COMPLETED if result.get('success') else TaskStatus.FAILED
            task_run.result_data = result
            db.commit()

    except Exception as e:
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            task_run.status = TaskStatus.FAILED
            task_run.result_data = {'error': str(e)}
            db.commit()

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskRun).filter(TaskRun.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/user/{user_id}")
def get_user_tasks(user_id: int, db: Session = Depends(get_db)):
    """获取用户的所有任务"""
    tasks = db.query(TaskRun).filter(TaskRun.user_id == user_id).order_by(TaskRun.created_at.desc()).limit(10).all()
    return tasks
```

- [ ] **Step 2: Add result_data to TaskRun model**

Check `backend/app/models/task_run.py`:

```python
from sqlalchemy import Column, Integer, String, JSON, DateTime, Enum
import enum

class TaskType(str, enum.Enum):
    apply = "apply"
    search = "search"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    task_type = Column(String(50))
    status = Column(String(20), default="pending")
    result_data = Column(JSON, nullable=True)  # ADD THIS
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 3: Test backend imports**

Run: `cd /c/Users/TR/qing-agent/backend && python -c "from app.api.tasks import router; print('OK')" 2>&1`

Expected: OK

- [ ] **Step 4: Commit**

```bash
cd /c/Users/TR/qing-agent
git add backend/app/api/tasks.py backend/app/models/task_run.py
git commit -m "feat: implement actual task execution with Playwright"
```

---

## Task 5: Update zhilian.py - Fix Selectors and Full Flow

**Files:**
- Modify: `playwright/src/platforms/zhilian.py`

- [ ] **Step 1: Update zhilian.py with correct selectors and full flow**

The current zhilian.py has outdated selectors. We need to rewrite it with correct selectors for 2024智联招聘:

```python
from typing import List, Dict
from playwright.src.platforms.base import BasePlatform
import asyncio


class ZhilianPlatform(BasePlatform):
    """智联招聘平台适配器"""

    def __init__(self):
        super().__init__('智联招聘')
        self.base_url = 'https://www.zhaopin.com'
        self.city_codes = {
            '深圳': '765',
            '北京': '530',
            '上海': '538',
            '广州': '753',
        }

    async def login(self, cookie: str = None, username: str = None, password: str = None) -> bool:
        """登录智联招聘"""
        page = await self.new_page()

        try:
            await page.goto(f'{self.base_url}/', wait_until='domcontentloaded')

            if cookie:
                # 使用 Cookie 登录
                await page.context.add_cookies([
                    {'name': 'zp_token', 'value': cookie, 'url': self.base_url}
                ])
                await page.reload()
                await page.wait_for_timeout(2000)
            elif username and password:
                # 点击登录
                await page.click('text=登录')
                await page.wait_for_timeout(1000)

                # 输入账号密码
                await page.fill('input[name="loginname"]', username)
                await page.fill('input[name="password"]', password)
                await page.click('button[type="submit"]')

                await page.wait_for_timeout(5000)

            # 验证登录成功
            await page.wait_for_timeout(1000)
            return True

        except Exception as e:
            print(f"[智联] 登录失败: {e}")
            return False

        finally:
            await page.close()

    async def search_jobs(self, keyword: str, city: str = '深圳', page: int = 1) -> List[Dict]:
        """搜索职位"""
        page = await self.new_page()
        jobs = []

        try:
            city_code = self.city_codes.get(city, '765')
            search_url = f'https://sou.zhaopin.com/?jl={city_code}&kw={keyword}&p={page}'

            print(f"[智联] 搜索: {keyword} @ {city}")
            await page.goto(search_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)

            # 等待职位列表加载
            await page.wait_for_selector('.joblist-box', timeout=10000)

            # 提取职位卡片 - 使用更通用的选择器
            job_cards = await page.query_selector_all('.joblist-box > div')

            for card in job_cards:
                try:
                    # 获取职位链接
                    link_elem = await card.query_selector('a[href*="zhaopin.com"]')
                    if not link_elem:
                        continue

                    job_url = await link_elem.get_attribute('href')
                    title = await link_elem.inner_text() or ''

                    # 公司名称
                    company_elem = await card.query_selector('.companyName')
                    company = await company_elem.inner_text() if company_elem else ''

                    # 薪资
                    salary_elem = await card.query_selector('.salary')
                    salary = await salary_elem.inner_text() if salary_elem else ''

                    # 地区
                    area_elem = await card.query_selector('.info-location')
                    area = await area_elem.inner_text() if area_elem else ''

                    # 解析薪资
                    salary_min, salary_max = self._parse_salary(salary)

                    job = {
                        'platform': 'zhilian',
                        'platform_job_id': job_url.split('/')[-1].replace('.htm', '') if job_url else '',
                        'title': title.strip(),
                        'company': company.strip() if company else '',
                        'city': city,
                        'area': area.strip() if area else '',
                        'salary': salary,
                        'salary_min': salary_min,
                        'salary_max': salary_max,
                        'source_url': job_url,
                    }
                    jobs.append(job)

                except Exception as e:
                    continue

            print(f"[智联] 找到 {len(jobs)} 个职位")

        except Exception as e:
            print(f"[智联] 搜索失败: {e}")

        finally:
            await page.close()

        return jobs

    def _parse_salary(self, salary_text: str) -> tuple:
        """解析薪资文本返回 min, max"""
        import re
        if not salary_text or '面议' in salary_text:
            return 0, 0

        # 例如 "8-15K" 或 "8-15千"
        pattern = r'(\d+)[kK千]?\s*[-~]\s*(\d+)[kK千]?'
        match = re.search(pattern, salary_text, re.IGNORECASE)
        if match:
            min_sal = int(match.group(1)) * 1000
            max_sal = int(match.group(2)) * 1000
            return min_sal, max_sal

        return 0, 0

    async def apply_job(self, job_url: str) -> Dict:
        """投递职位"""
        page = await self.new_page()
        result = {'success': False, 'message': '', 'status': ''}

        try:
            await page.goto(job_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)

            # 点击投递按钮
            apply_btn = await page.query_selector('button.btn-apply, .btn-apply, [class*="apply"]')

            if not apply_btn:
                result['message'] = '不可投递或已投递'
                result['status'] = 'not_applicable'
                await page.close()
                return result

            await apply_btn.click()
            await page.wait_for_timeout(3000)

            # 检查是否成功
            success_text = await page.query_selector('text=/已申请|投递成功/')
            if success_text:
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
```

- [ ] **Step 2: Verify syntax**

Run: `cd /c/Users/TR/qing-agent/playwright && python -m py_compile src/platforms/zhilian.py 2>&1`

Expected: No errors

- [ ] **Step 3: Commit**

```bash
cd /c/Users/TR/qing-agent
git add playwright/src/platforms/zhilian.py
git commit -m "feat(playwright): update zhilian.py with correct selectors"
```

---

## Task 6: Update Dashboard - Show Task Progress

**Files:**
- Modify: `frontend/src/views/Dashboard.vue`

- [ ] **Step 1: Update Dashboard to show task status and results**

Replace the `fetchData` and `runNow` functions:

```javascript
const fetchData = async () => {
  try {
    const userId = localStorage.getItem('user_id') || 1

    // 获取投递记录
    const [appsRes, statsRes] = await Promise.all([
      api.get(`/applications/user/${userId}`),
      api.get(`/applications/user/${userId}/stats`)
    ])
    applications.value = appsRes || []
    stats.value = statsRes || { pending: 0, submitted: 0, failed: 0 }

    // 获取最近任务状态
    const tasksRes = await api.get(`/tasks/user/${userId}`)
    if (tasksRes && tasksRes.length > 0) {
      const latestTask = tasksRes[0]
      if (latestTask.status === 'running') {
        running.value = true
      } else if (latestTask.result_data) {
        lastTaskResult.value = latestTask.result_data
      }
    }
  } catch (error) {
    console.error('获取数据失败:', error)
  }
}

const runNow = async () => {
  running.value = true
  lastTaskResult.value = null
  try {
    const userId = localStorage.getItem('user_id') || 1
    const result = await api.post('/tasks/run', { user_id: Number(userId), task_type: 'apply' })

    // 轮询任务状态
    pollTaskStatus(result.id)

  } catch (error) {
    alert('任务启动失败')
    running.value = false
  }
}

const pollTaskStatus = async (taskId) => {
  const checkStatus = async () => {
    try {
      const task = await api.get(`/tasks/${taskId}`)
      if (task.status === 'completed') {
        running.value = false
        lastTaskResult.value = task.result_data
        await fetchData()  // 刷新投递记录
      } else if (task.status === 'failed') {
        running.value = false
        lastTaskResult.value = { error: task.result_data?.error || '任务失败' }
      } else {
        // 继续轮询
        setTimeout(checkStatus, 3000)
      }
    } catch (e) {
      console.error('检查任务状态失败:', e)
      running.value = false
    }
  }
  setTimeout(checkStatus, 2000)
}
```

- [ ] **Step 2: Add result display in template**

Find the `.recent-section` and update:

```vue
      <section class="recent-section">
        <h3>最近投递</h3>
        <div v-if="lastTaskResult" class="task-result">
          <div v-if="lastTaskResult.error" class="result-error">
            ❌ {{ lastTaskResult.error }}
          </div>
          <div v-else class="result-success">
            ✅ 任务完成：搜索 {{ lastTaskResult.searched }} 个职位，
            匹配 {{ lastTaskResult.matched }} 个，
            投递 {{ lastTaskResult.applied }} 个
          </div>
        </div>
        <div class="applications-list">
          <!-- ... existing code ... -->
        </div>
      </section>
```

Add style:

```css
.task-result {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
}

.result-success {
  background: #d4edda;
  color: #155724;
}

.result-error {
  background: #f8d7da;
  color: #721c24;
}
```

- [ ] **Step 3: Test build**

Run: `cd /c/Users/TR/qing-agent/frontend && npm run build 2>&1 | tail -5`

Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
cd /c/Users/TR/qing-agent
git add frontend/src/views/Dashboard.vue
git commit -m "feat: connect Dashboard to actual task execution"
```

---

## Task 7: Integration Test

**Files:**
- Test: Manual browser testing

- [ ] **Step 1: Start backend**

Run: `cd /c/Users/TR/qing-agent/backend && python main.py`

- [ ] **Step 2: Start frontend**

Run: `cd /c/Users/TR/qing-agent/frontend && npm run dev`

- [ ] **Step 3: Test flow**

1. Go to Profile page
2. Configure: set keywords, city, daily limit (e.g., 3)
3. Expand credentials section, enter zhilian cookie or username/password
4. Go to Dashboard
5. Click "立即运行"
6. Watch task execute and see results

---

## Verification Checklist

- [ ] Profile page shows credentials section (collapsible)
- [ ] Profile page shows "今日投递数量" input
- [ ] Credentials saved to backend
- [ ] Dashboard "立即运行" triggers backend task
- [ ] Task status polling works
- [ ] Playwright searches zhilian.com
- [ ] Jobs are matched against profile
- [ ] Applications appear in "最近投递"
