# 求职 Agent Phase 1 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 在本地快速跑通求职 Agent 核心流程：Vue 前端 + FastAPI 后端 + PostgreSQL + Playwright 浏览器自动化

**架构：** 单体简化版，前后端分离，浏览器脚本独立运行，通过数据库通信

**技术栈：**
- 前端：Vue 3 + Vite + Pinia + Vue Router
- 后端：FastAPI + SQLAlchemy 2.0 + Pydantic v2
- 数据库：PostgreSQL
- 认证：Auth0 JWT
- 浏览器自动化：Playwright
- 任务调度：APScheduler

---

## 项目目录结构

```
qing-agent/
├── frontend/                    # Vue 前端
│   ├── src/
│   │   ├── api/                # API 调用
│   │   ├── components/         # 公共组件
│   │   ├── views/              # 页面
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── router/             # 路由
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
│
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── api/                # API 路由
│   │   ├── models/             # SQLAlchemy 模型
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # 业务逻辑
│   │   ├── core/               # 核心配置
│   │   └── main.py
│   ├── requirements.txt
│   └── alembic/                # 数据库迁移
│
├── playwright/                   # Playwright 浏览器脚本
│   ├── src/
│   │   ├── browsers/           # 浏览器控制器
│   │   ├── platforms/          # 平台适配器 (智联, 51job, 猎聘)
│   │   ├── services/           # 任务执行逻辑
│   │   └── main.py             # 入口
│   ├── requirements.txt
│   └── config/
│
├── docker-compose.yml           # Docker 部署（未来）
├── .env.example                # 环境变量示例
└── README.md
```

---

## Task 1: 初始化项目结构

**Files:**
- Create: `qing-agent/frontend/package.json`
- Create: `qing-agent/backend/requirements.txt`
- Create: `qing-agent/playwright/requirements.txt`
- Create: `qing-agent/.env.example`
- Create: `qing-agent/README.md`

- [ ] **Step 1: 创建前端 package.json**

```json
{
  "name": "qing-agent-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

- [ ] **Step 2: 创建后端 requirements.txt**

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
pydantic==2.5.0
python-jose[cryptography]==3.3.0
auth0==4.4.0
apscheduler==3.10.4
python-dotenv==1.0.0
alembic==1.13.1
playwright==1.41.0
```

- [ ] **Step 3: 创建 .env.example**

```
# 后端配置
DATABASE_URL=postgresql://user:password@localhost:5432/qing_agent
AUTH0_DOMAIN=qing-personal-domain.au.auth0.com
AUTH0_CLIENT_ID=81DY4R0s11wzhFyJNCZd6NbSQrrULVF9
AUTH0_API_AUDIENCE=https://qing-agent-api
SECRET_KEY=your-secret-key-here

# 前端配置
VITE_API_BASE_URL=http://localhost:8000
```

---

## Task 2: 后端核心 - 数据库模型

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/job.py`
- Create: `backend/app/models/application.py`
- Create: `backend/app/models/user_profile.py`

- [ ] **Step 1: 创建用户模型**

```python
# backend/app/models/user.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    auth0_id = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    username = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    applications = relationship("Application", back_populates="user")
```

- [ ] **Step 2: 创建用户画像模型**

```python
# backend/app/models/user_profile.py
from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    # 目标岗位
    target_positions = Column(JSON, default=list)  # ["品牌策划", "视觉设计"]
    target_cities = Column(JSON, default=["深圳"])
    exclude_areas = Column(JSON, default=["宝安区"])

    # 薪资期望
    salary_min = Column(Integer, default=8000)
    salary_max = Column(Integer, default=15000)

    # 经验要求
    experience_min = Column(Integer, default=1)
    experience_max = Column(Integer, default=5)

    # 平台 Cookie/密码（加密存储）
    platform_credentials = Column(JSON, default=dict)

    # 用户关联
    user = relationship("User", back_populates="profile")
```

- [ ] **Step 3: 创建职位模型**

```python
# backend/app/models/job.py
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, Boolean
from datetime import datetime
from app.core.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), index=True)  # zhilian, 51job, liepin
    platform_job_id = Column(String(255), index=True)
    title = Column(String(255))
    company = Column(String(255))
    city = Column(String(100))
    area = Column(String(100))
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    experience = Column(String(100))
    education = Column(String(50))
    job_type = Column(String(50))
    description = Column(Text)
    requirements = Column(Text)
    skills = Column(JSON, default=list)
    industry = Column(String(100))
    source_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 复合唯一索引（平台+平台ID）
    __table_args__ = (
        UniqueConstraint('platform', 'platform_job_id', name='uq_platform_job_id'),
    )
```

- [ ] **Step 4: 创建投递记录模型**

```python
# backend/app/models/application.py
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"           # 待处理
    SUBMITTED = "submitted"       # 已投递
    ALREADY_APPLIED = "already_applied"  # 已投递过
    FAILED = "failed"             # 失败
    REJECTED = "rejected"         # 被拒

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    platform = Column(String(50))

    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING)
    applied_at = Column(DateTime, nullable=True)
    failed_reason = Column(Text, nullable=True)

    # 投递详情
    apply_url = Column(String(500))
    apply_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    user = relationship("User", back_populates="applications")
    job = relationship("Job")
```

- [ ] **Step 5: 创建任务运行记录模型**

```python
# backend/app/models/task_run.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Enum
from datetime import datetime
import enum
from app.core.database import Base

class TaskType(str, enum.Enum):
    SEARCH = "search"           # 搜索召回
    APPLY = "apply"              # 投递
    VERIFY = "verify"            # 状态验证

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    task_type = Column(Enum(TaskType))
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)

    # 统计
    jobs_found = Column(Integer, default=0)
    jobs_filtered = Column(Integer, default=0)
    applications_submitted = Column(Integer, default=0)
    applications_failed = Column(Integer, default=0)

    # 详情
    details = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## Task 3: 后端核心 - API 路由

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/users.py`
- Create: `backend/app/api/jobs.py`
- Create: `backend/app/api/applications.py`
- Create: `backend/app/api/tasks.py`

- [ ] **Step 1: 创建用户路由**

```python
# backend/app/api/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.user import UserCreate, UserResponse, UserProfileUpdate

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(
        auth0_id=user.auth0_id,
        email=user.email,
        username=user.username
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}/profile", response_model=UserResponse)
def update_profile(user_id: int, profile: UserProfileUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.profile:
        user.profile = UserProfile(user_id=user_id)

    # 更新字段
    for key, value in profile.dict(exclude_unset=True).items():
        setattr(user.profile, key, value)

    db.commit()
    db.refresh(user)
    return user
```

- [ ] **Step 2: 创建职位路由**

```python
# backend/app/api/jobs.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.job import Job
from app.schemas.job import JobResponse, JobCreate

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("/", response_model=List[JobResponse])
def list_jobs(
    skip: int = 0,
    limit: int = 20,
    platform: Optional[str] = None,
    city: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Job).filter(Job.is_active == True)
    if platform:
        query = query.filter(Job.platform == platform)
    if city:
        query = query.filter(Job.city == city)
    return query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
```

- [ ] **Step 3: 创建投递路由**

```python
# backend/app/api/applications.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.application import Application, ApplicationStatus
from app.schemas.application import ApplicationResponse

router = APIRouter(prefix="/api/applications", tags=["applications"])

@router.get("/user/{user_id}", response_model=List[ApplicationResponse])
def list_user_applications(
    user_id: int,
    status: Optional[ApplicationStatus] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Application).filter(Application.user_id == user_id)
    if status:
        query = query.filter(Application.status == status)
    return query.order_by(Application.created_at.desc()).all()

@router.get("/user/{user_id}/stats")
def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    apps = db.query(Application).filter(Application.user_id == user_id).all()
    return {
        "total": len(apps),
        "submitted": len([a for a in apps if a.status == ApplicationStatus.SUBMITTED]),
        "pending": len([a for a in apps if a.status == ApplicationStatus.PENDING]),
        "failed": len([a for a in apps if a.status == ApplicationStatus.FAILED]),
    }
```

- [ ] **Step 4: 创建任务路由**

```python
# backend/app/api/tasks.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.task_run import TaskRun, TaskType, TaskStatus
from app.schemas.task import TaskCreate, TaskResponse

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.post("/run", response_model=TaskResponse)
def trigger_task(task: TaskCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 创建任务记录
    task_run = TaskRun(
        user_id=task.user_id,
        task_type=TaskType(task.task_type),
        status=TaskStatus.PENDING
    )
    db.add(task_run)
    db.commit()
    db.refresh(task_run)

    # TODO: 触发 Playwright 脚本执行
    # background_tasks.add_task(run_playwright_task, task_run.id)

    return task_run

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskRun).filter(TaskRun.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
```

---

## Task 4: 后端核心 - FastAPI 入口

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: 创建配置模块**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/qing_agent"

    # Auth0
    AUTH0_DOMAIN: str = "qing-personal-domain.au.auth0.com"
    AUTH0_CLIENT_ID: str = "81DY4R0s11wzhFyJNCZd6NbSQrrULVF9"
    AUTH0_API_AUDIENCE: str = "https://qing-agent-api"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 2: 创建数据库连接**

```python
# backend/app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 3: 创建 FastAPI 主入口**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.api import users, jobs, applications, tasks

app = FastAPI(
    title="求职 Agent API",
    description="智联 + 51job + 猎聘 求职自动化系统",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(users.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(tasks.router)

@app.on_event("startup")
async def startup():
    init_db()
    print("求职 Agent API 已启动")

@app.get("/health")
def health():
    return {"status": "ok"}
```

---

## Task 5: 前端 - Vue 项目初始化

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/vite.config.js`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.js`

- [ ] **Step 1: 创建 vite.config.js**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 2: 创建 main.js**

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- [ ] **Step 3: 创建 App.vue**

```vue
<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
</style>
```

- [ ] **Step 4: 创建路由**

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import Profile from '../views/Profile.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/login', name: 'Login', component: Login },
  { path: '/dashboard', name: 'Dashboard', component: Dashboard },
  { path: '/profile', name: 'Profile', component: Profile },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

---

## Task 6: 前端 - 页面组件

**Files:**
- Create: `frontend/src/views/Home.vue`
- Create: `frontend/src/views/Login.vue`
- Create: `frontend/src/views/Dashboard.vue`
- Create: `frontend/src/views/Profile.vue`
- Create: `frontend/src/components/Navbar.vue`

- [ ] **Step 1: 创建 Home.vue**

```vue
<template>
  <div class="home">
    <h1>求职 Agent</h1>
    <p>精准投递，而非乱投</p>
    <div class="features">
      <div class="feature">
        <h3>多平台支持</h3>
        <p>智联招聘、前程无忧、猎聘</p>
      </div>
      <div class="feature">
        <h3>智能筛选</h3>
        <p>硬过滤 + 动态评分，只投真正匹配的岗位</p>
      </div>
      <div class="feature">
        <h3>实时跟踪</h3>
        <p>投递状态实时查看</p>
      </div>
    </div>
    <button @click="$router.push('/login')">开始使用</button>
  </div>
</template>

<script setup>
</script>

<style scoped>
.home {
  text-align: center;
  padding: 50px 20px;
}
.features {
  display: flex;
  gap: 30px;
  justify-content: center;
  margin: 40px 0;
}
.feature {
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  width: 200px;
}
button {
  padding: 12px 30px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
}
</style>
```

- [ ] **Step 2: 创建 Dashboard.vue**

```vue
<template>
  <div class="dashboard">
    <Navbar />
    <div class="content">
      <h2>控制台</h2>

      <div class="stats">
        <div class="stat">
          <span class="label">待投递</span>
          <span class="value">{{ stats.pending }}</span>
        </div>
        <div class="stat">
          <span class="label">已投递</span>
          <span class="value">{{ stats.submitted }}</span>
        </div>
        <div class="stat">
          <span class="label">失败</span>
          <span class="value">{{ stats.failed }}</span>
        </div>
      </div>

      <div class="actions">
        <button @click="runNow" :disabled="running">
          {{ running ? '运行中...' : '立即运行' }}
        </button>
        <button @click="setSchedule">设置定时任务</button>
      </div>

      <div class="recent-applications">
        <h3>最近投递</h3>
        <div v-for="app in applications" :key="app.id" class="application-card">
          <div class="job-info">
            <h4>{{ app.job.title }}</h4>
            <p>{{ app.job.company }} · {{ app.job.city }}</p>
          </div>
          <span :class="['status', app.status]">{{ app.status }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Navbar from '../components/Navbar.vue'
import axios from 'axios'

const stats = ref({ pending: 0, submitted: 0, failed: 0 })
const applications = ref([])
const running = ref(false)

onMounted(async () => {
  // TODO: 获取用户统计数据
})

const runNow = async () => {
  running.value = true
  try {
    await axios.post('/api/tasks/run', { user_id: 1, task_type: 'apply' })
  } finally {
    running.value = false
  }
}

const setSchedule = () => {
  // TODO: 定时任务设置
}
</script>

<style scoped>
.dashboard { padding: 20px; }
.stats { display: flex; gap: 20px; margin: 20px 0; }
.stat { padding: 20px; background: #f5f5f5; border-radius: 8px; text-align: center; }
.stat .value { font-size: 32px; font-weight: bold; color: #007bff; }
.actions { display: flex; gap: 10px; margin: 20px 0; }
.application-card { display: flex; justify-content: space-between; padding: 15px; border: 1px solid #ddd; margin: 10px 0; border-radius: 6px; }
.status.submitted { color: green; }
.status.failed { color: red; }
</style>
```

- [ ] **Step 3: 创建 Profile.vue**

```vue
<template>
  <div class="profile">
    <Navbar />
    <div class="content">
      <h2>求职画像</h2>

      <form @submit.prevent="saveProfile">
        <div class="form-group">
          <label>目标岗位</label>
          <input v-model="profile.target_positions" type="text" placeholder="品牌策划, 视觉设计" />
        </div>

        <div class="form-group">
          <label>目标城市</label>
          <input v-model="profile.target_cities" type="text" placeholder="深圳" />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>薪资下限</label>
            <input v-model.number="profile.salary_min" type="number" />
          </div>
          <div class="form-group">
            <label>薪资上限</label>
            <input v-model.number="profile.salary_max" type="number" />
          </div>
        </div>

        <div class="form-group">
          <label>排除区域</label>
          <input v-model="profile.exclude_areas" type="text" placeholder="宝安区" />
        </div>

        <button type="submit">保存</button>
      </form>

      <h3>平台 Cookie 配置</h3>
      <div class="platform-config">
        <div v-for="platform in platforms" :key="platform.name" class="platform-item">
          <span>{{ platform.name }}</span>
          <input v-model="platform.cookie" type="password" placeholder="粘贴 Cookie" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Navbar from '../components/Navbar.vue'
import axios from 'axios'

const profile = ref({
  target_positions: '品牌策划, 品牌设计',
  target_cities: '深圳',
  salary_min: 8000,
  salary_max: 15000,
  exclude_areas: '宝安区'
})

const platforms = ref([
  { name: '智联招聘', cookie: '' },
  { name: '51job', cookie: '' },
  { name: '猎聘', cookie: '' }
])

const saveProfile = async () => {
  // TODO: 调用 API 保存
}
</script>

<style scoped>
.form-group { margin-bottom: 15px; }
.form-group label { display: block; margin-bottom: 5px; font-weight: 500; }
.form-group input { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
.form-row { display: flex; gap: 15px; }
.platform-item { display: flex; align-items: center; gap: 10px; margin: 10px 0; }
.platform-item span { width: 100px; }
button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
</style>
```

---

## Task 7: Playwright 浏览器自动化

**Files:**
- Create: `playwright/src/__init__.py`
- Create: `playwright/src/platforms/__init__.py`
- Create: `playwright/src/platforms/base.py`
- Create: `playwright/src/platforms/zhilian.py`
- Create: `playwright/src/platforms/job51.py`
- Create: `playwright/src/main.py`

- [ ] **Step 1: 创建平台基类**

```python
# playwright/src/platforms/base.py
from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Page
from typing import List, Dict

class BasePlatform(ABC):
    def __init__(self, name: str):
        self.name = name
        self.playwright = None
        self.browser = None
        self.context = None

    async def init(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    @abstractmethod
    async def login(self, cookie: str = None, username: str = None, password: str = None):
        """登录平台"""
        pass

    @abstractmethod
    async def search_jobs(self, keyword: str, city: str, page: int = 1) -> List[Dict]:
        """搜索职位"""
        pass

    @abstractmethod
    async def apply_job(self, job_url: str) -> bool:
        """投递职位"""
        pass
```

- [ ] **Step 2: 创建智联招聘适配器**

```python
# playwright/src/platforms/zhilian.py
from playwright.src.platforms.base import BasePlatform
from typing import List, Dict

class ZhilianPlatform(BasePlatform):
    def __init__(self):
        super().__init__('zhilian')
        self.base_url = 'https://www.zhaopin.com'

    async def login(self, cookie: str = None, username: str = None, password: str = None):
        page = await self.context.new_page()

        if cookie:
            # 使用 Cookie 登录
            await page.goto(self.base_url)
            await page.context.add_cookies([{'name': 'cookie', 'value': cookie, 'url': self.base_url}])
        else:
            # 使用账号密码登录
            await page.goto(f'{self.base_url}/login')
            await page.fill('#username', username)
            await page.fill('#password', password)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')

        await page.close()

    async def search_jobs(self, keyword: str, city: str, page: int = 1) -> List[Dict]:
        page = await self.context.new_page()
        jobs = []

        try:
            # 访问搜索页面
            search_url = f'{self.base_url}/s/{keyword}?jl={city}&isadv=0'
            await page.goto(search_url)
            await page.wait_for_load_state('networkidle')

            # 解析职位列表
            job_cards = await page.query_selector_all('.jobinfo')

            for card in job_cards:
                job = await self._parse_job_card(card)
                if job:
                    jobs.append(job)

        finally:
            await page.close()

        return jobs

    async def apply_job(self, job_url: str) -> bool:
        page = await self.context.new_page()

        try:
            await page.goto(job_url)
            await page.wait_for_load_state('networkidle')

            # 检查是否可投递
            apply_btn = await page.query_selector('button:has-text("立即投递")')

            if not apply_btn:
                return False

            await apply_btn.click()
            await page.wait_for_timeout(2000)

            # 验证投递状态
            success = await page.query_selector('text=已申请')
            return success is not None

        finally:
            await page.close()

    async def _parse_job_card(self, card) -> Dict:
        try:
            title_elem = await card.query_selector('.jobname')
            company_elem = await card.query_selector('.companyname')
            salary_elem = await card.query_selector('.salary')

            return {
                'title': await title_elem.inner_text() if title_elem else '',
                'company': await company_elem.inner_text() if company_elem else '',
                'salary': await salary_elem.inner_text() if salary_elem else '',
            }
        except:
            return None
```

- [ ] **Step 3: 创建主入口**

```python
# playwright/src/main.py
import asyncio
import argparse
from playwright.src.platforms.zhilian import ZhilianPlatform
from playwright.src.platforms.job51 import Job51Platform

async def run_search(platform_name: str, keyword: str, city: str = '深圳'):
    platform = ZhilianPlatform() if platform_name == 'zhilian' else Job51Platform()

    try:
        await platform.init()
        await platform.login()  # 需要先配置 Cookie/账号
        jobs = await platform.search_jobs(keyword, city)
        print(f"找到 {len(jobs)} 个职位")
        for job in jobs:
            print(f"  - {job['title']} @ {job['company']} ({job['salary']})")
    finally:
        await platform.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', default='zhilian')
    parser.add_argument('--keyword', required=True)
    parser.add_argument('--city', default='深圳')
    args = parser.parse_args()

    asyncio.run(run_search(args.platform, args.keyword, args.city))
```

---

## Task 8: 数据库迁移

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/001_initial.py`

- [ ] **Step 1: 初始化 Alembic**

```bash
cd backend
alembic init alembic
```

- [ ] **Step 2: 配置 env.py**

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import Base
from app.models import user, job, application, user_profile, task_run

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: 运行迁移**

```bash
cd backend
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

---

## Task 9: 整合测试

- [ ] **Step 1: 启动后端测试**

```bash
cd backend
uvicorn app.main:app --reload
# 访问 http://localhost:8000/health
```

- [ ] **Step 2: 启动前端测试**

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

- [ ] **Step 3: 验证 API 连接**

```bash
curl http://localhost:8000/health
# 预期: {"status": "ok"}
```

---

## 执行方式选择

**Plan complete and saved to `docs/superpowers/plans/2026-03-30-qing-agent-phase1.md`**

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
