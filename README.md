# Qing Agent - 智能求职投递 Agent

**版本:** v1.0.0 (Phase 1)
**状态:** 开发中

---

## 系统概述

Qing Agent 是一个智能求职投递系统，通过 Playwright 浏览器自动化技术，自动完成在各大招聘平台（智联招聘、51job、猎聘）上的职位搜索、筛选和投递。

### 核心功能

- 多平台职位搜索（智联、51job、猎聘）
- 自动过滤重复投递
- 智能简历匹配
- 投递状态追踪
- 风险控制系统（防止账号异常）

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Vue 3 前端                              │
│                  (localhost:5173)                           │
│  ┌─────────────┬──────────────┬───────────────────────┐   │
│  │ 用户画像配置  │  实时进度查看  │     投递记录列表       │   │
│  └─────────────┴──────────────┴───────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/REST
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI 后端                             │
│                  (localhost:8000)                            │
│  ┌─────────────┬──────────────┬───────────────────────┐   │
│  │  用户认证    │   REST API   │      任务调度          │   │
│  │  (Auth0 JWT) │              │    (APScheduler)       │   │
│  └─────────────┴──────────────┴───────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────────┐   ┌─────────────────────────────────┐
│     PostgreSQL           │   │   Playwright 浏览器自动化        │
│     数据库                │   │   (独立进程)                    │
│                         │   │  ┌─────────────────────────┐   │
│  - 用户数据              │   │  │  智联招聘 / 51job / 猎聘  │   │
│  - 投递记录              │   │  └─────────────────────────┘   │
│  - 任务状态              │   └─────────────────────────────────┘
└─────────────────────────┘
```

---

## 目录结构

```
qing-agent/
├── frontend/                      # Vue 3 前端应用
│   ├── src/
│   │   ├── api/                   # API 调用模块
│   │   ├── components/            # 公共组件
│   │   ├── views/                  # 页面组件
│   │   │   ├── Home.vue           # 首页
│   │   │   └── Login.vue          # 登录页
│   │   ├── stores/                # Pinia 状态管理
│   │   ├── router/                # Vue Router 配置
│   │   ├── App.vue                # 根组件
│   │   └── main.js                # 入口文件
│   ├── package.json
│   └── vite.config.js
│
├── backend/                       # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI 入口
│   │   ├── api/                  # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── jobs.py           # 职位相关 API
│   │   │   ├── applications.py  # 投递相关 API
│   │   │   ├── users.py          # 用户相关 API
│   │   │   ├── tasks.py          # 任务调度 API
│   │   │   ├── auth.py           # 认证 API
│   │   │   └── v34.py            # v3.4 版本 API
│   │   ├── models/               # SQLAlchemy 模型
│   │   │   ├── user.py
│   │   │   ├── job.py
│   │   │   ├── application.py
│   │   │   ├── task_run.py
│   │   │   └── user_profile.py
│   │   ├── schemas/              # Pydantic schemas
│   │   │   ├── user.py
│   │   │   ├── job.py
│   │   │   ├── application.py
│   │   │   └── task.py
│   │   ├── services/             # 业务逻辑服务
│   │   │   ├── crawler_runner.py # 爬虫运行器
│   │   │   ├── task_manager.py   # 任务管理器
│   │   │   └── phone_login_manager.py  # 手机登录管理
│   │   └── core/                 # 核心配置
│   │       ├── config.py
│   │       └── database.py
│   ├── alembic/                  # 数据库迁移
│   │   ├── versions/            # 迁移版本
│   │   └── script.py.mako
│   ├── alembic.ini
│   ├── main.py
│   ├── requirements.txt
│   └── run.sh / run.ps1         # 启动脚本
│
├── playwright/                   # Playwright 浏览器自动化
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py              # Playwright 入口
│   │   ├── platforms/           # 平台适配器
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # 基类
│   │   │   ├── zhilian.py       # 智联招聘
│   │   │   ├── job51.py         # 51job
│   │   │   └── liepin.py        # 猎聘
│   │   └── services/            # Playwright 服务
│   ├── requirements.txt
│   └── run.sh                   # 启动脚本
│
├── docs/                         # 文档
│   └── superpowers/
│       └── plans/               # 开发计划
│
├── .env.example                 # 环境变量模板
├── docker-compose.yml           # Docker 部署配置
├── CLAUDE.md                    # 开发准则
└── README.md                    # 本文件
```

---

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Playwright

### 1. 克隆项目

```bash
git clone https://github.com/Ching-W0121/Qing-agent.git
cd Qing-agent
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env
```

编辑 `.env` 文件，配置以下内容：

```env
# ===================
# 后端配置
# ===================

# 数据库连接
DATABASE_URL=postgresql://qing_agent:your_password@localhost:5432/qing_agent

# Auth0 认证配置（用于 JWT 验证）
AUTH0_DOMAIN=your-domain.au.auth0.com
AUTH0_CLIENT_ID=your_client_id
AUTH0_API_AUDIENCE=https://qing-agent-api
SECRET_KEY=your-secret-key-min-32-chars

# ===================
# 前端配置
# ===================

# 前端 API 基础路径
VITE_API_BASE_URL=http://localhost:8000
```

### 3. 启动 PostgreSQL 数据库

**方式一：Docker（推荐）**

```bash
docker run -d \
  --name qing-agent-db \
  -e POSTGRES_USER=qing_agent \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=qing_agent \
  -p 5432:5432 \
  postgres:15
```

**方式二：本地安装**

下载并安装 [PostgreSQL 15](https://www.postgresql.org/download/)，然后创建数据库：

```sql
CREATE USER qing_agent WITH PASSWORD 'your_password';
CREATE DATABASE qing_agent OWNER qing_agent;
```

### 4. 启动后端

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置数据库（首次）
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload --port 8000
```

后端 API 文档地址：http://localhost:8000/docs

### 5. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端访问地址：http://localhost:5173

### 6. 安装 Playwright 浏览器

```bash
cd playwright

# 安装依赖
pip install -r requirements.txt

# 安装 Chromium 浏览器
playwright install chromium
```

---

## 配置说明

### Auth0 配置

1. 登录 [Auth0](https://auth0.com/) 创建应用
2. 选择 **Regular Web Applications** 类型
3. 获取以下配置：
   - **Domain**: 格式如 `your-domain.au.auth0.com`
   - **Client ID**: 应用客户端 ID
4. 创建 API：
   - **Identifier (API Identifier)**: `https://qing-agent-api`
5. 配置 Allowed Callback URLs：
   ```
   http://localhost:5173/callback,http://localhost:8000/callback
   ```

### 数据库配置

DATABASE_URL 格式：
```
postgresql://用户名:密码@主机:端口/数据库名
```

示例：
```
postgresql://qing_agent:my_password@localhost:5432/qing_agent
```

### 平台 Cookie 配置

智联招聘等平台需要登录后的 Cookie：

1. 在浏览器中登录招聘平台
2. 打开开发者工具 (F12)
3. 复制 Cookie（注意：需要持续更新，过期后需重新配置）

---

## 使用说明

### 基本使用流程

1. **登录前端**
   - 访问 http://localhost:5173
   - 使用 Auth0 账号登录

2. **配置用户画像**
   - 设置求职意向（职位、城市等）
   - 上传简历

3. **开始投递**
   - 选择平台和关键词
   - 系统自动搜索并投递

### Playwright 命令行使用

```bash
cd playwright

# 搜索职位
python -m src.main --platform zhilian --keyword "品牌策划" --city 深圳

# 投递职位
python -m src.main --platform zhilian --job-url "https://www.zhaopin.com/job/xxx.htm"

# 运行测试
python -m pytest src/test_zhilian.py -v
```

### API 调用

```bash
# 健康检查
curl http://localhost:8000/health

# 获取职位列表
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/jobs/?keyword=品牌策划&city=深圳

# 投递职位
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"job_url": "https://www.zhaopin.com/job/xxx.htm"}' \
     http://localhost:8000/api/applications/
```

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/users/` | 创建用户 |
| GET | `/api/users/{id}` | 获取用户信息 |
| PUT | `/api/users/{id}/profile` | 更新用户画像 |
| GET | `/api/jobs/` | 搜索职位 |
| GET | `/api/jobs/{id}` | 获取职位详情 |
| GET | `/api/applications/user/{id}` | 获取用户投递列表 |
| GET | `/api/applications/user/{id}/stats` | 获取投递统计 |
| POST | `/api/tasks/run` | 触发投递任务 |
| GET | `/api/tasks/{id}/status` | 获取任务状态 |

---

## 数据库模型

### 用户 (User)
- id, email, created_at, updated_at

### 用户画像 (UserProfile)
- user_id, resume_text, preferences, risk_tolerance

### 职位 (Job)
- id, platform, title, company, city, salary, url, requirements

### 投递记录 (Application)
- id, user_id, job_id, status, applied_at

### 任务记录 (TaskRun)
- id, user_id, platform, status, started_at, completed_at

---

## 技术栈

| 模块 | 技术 | 版本 |
|------|------|------|
| 前端框架 | Vue 3 | 3.x |
| 构建工具 | Vite | 5.x |
| 状态管理 | Pinia | 2.x |
| 路由 | Vue Router | 4.x |
| 后端框架 | FastAPI | 0.109+ |
| ORM | SQLAlchemy | 2.0+ |
| 数据库 | PostgreSQL | 15 |
| 认证 | Auth0 JWT | - |
| 浏览器自动化 | Playwright | 1.40+ |
| 任务调度 | APScheduler | 3.x |

---

## 平台支持状态

| 平台 | 状态 | 搜索 | 投递 | 备注 |
|------|------|------|------|------|
| 智联招聘 | ✅ 已实现 | ✅ | ✅ | 主要平台 |
| 51job | ✅ 已实现 | ✅ | ✅ | 主要平台 |
| 猎聘 | ✅ 已实现 | ✅ | ✅ | 辅助平台 |
| BOSS 直聘 | ❌ 暂不支持 | - | - | 反爬太强 |

---

## 开发指南

### 代码规范

项目遵循 `CLAUDE.md` 中的开发准则：

1. **Think Before Coding** - 不要假设，明确陈述假设
2. **Simplicity First** - 解决问题所需的最少代码
3. **Surgical Changes** - 只触碰必须触碰的
4. **Goal-Driven Execution** - 定义成功标准，循环验证

### Playwright 开发注意事项

- 改动后验证语法: `python -m py_compile platforms/xxx.py`
- 每次改动的代码行都应能追溯到具体需求
- 不要在未确认前假设反检测失效原因
- 使用 headless 模式进行自动化测试

### 前端开发注意事项

- 不随意重构或"改进"已有的组件逻辑
- 只改用户指出的问题区域

---

## 数据库迁移

```bash
cd backend

# 创建迁移
alembic revision --autogenerate -m "描述本次更改"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1

# 查看当前版本
alembic current

# 查看迁移历史
alembic history
```

---

## Docker 部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重新构建
docker-compose up -d --build
```

---

## 常见问题

### Q: Playwright 找不到浏览器
```bash
playwright install chromium
```

### Q: 数据库连接失败
检查 PostgreSQL 是否运行：
```bash
pg_isready -h localhost -p 5432
```

### Q: Auth0 认证失败
确认 `.env` 中的 `AUTH0_DOMAIN` 和 `AUTH0_CLIENT_ID` 正确，且 API 已启用。

### Q: Cookie 过期
招聘平台 Cookie 通常有效期较短，需要定期更新。登录对应平台获取新的 Cookie。

---

## 相关文档

- [Phase 1 开发计划](./docs/superpowers/plans/2026-03-30-qing-agent-phase1.md)
- [系统架构文档](./docs/architecture/)（如有）

---

## License

MIT
