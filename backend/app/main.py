from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.api import users, jobs, applications, tasks, matching, events, recommendations

app = FastAPI(
    title="求职 Agent API",
    description="智联 + 51job + 猎聘 求职自动化系统",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(users.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(tasks.router)
app.include_router(matching.router)
app.include_router(events.router)
app.include_router(recommendations.router)

@app.on_event("startup")
async def startup():
    init_db()
    print("=" * 60)
    print("求职 Agent API 已启动")
    print("API 文档: http://localhost:8000/docs")
    print("=" * 60)

@app.get("/")
async def root():
    return {
        "name": "求职 Agent API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health():
    return {"status": "ok"}
