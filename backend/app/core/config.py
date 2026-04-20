import os
from typing import Optional

class Settings:
    # 数据库 - 使用 SQLite 用于本地测试，PostgreSQL 用于生产
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./qing_agent.db"  # 本地 SQLite 测试
    )

    # Auth0
    AUTH0_DOMAIN: str = os.getenv("AUTH0_DOMAIN", "qing-personal-domain.au.auth0.com")
    AUTH0_CLIENT_ID: str = os.getenv("AUTH0_CLIENT_ID", "81DY4R0s11wzhFyJNCZd6NbSQrrULVF9")
    AUTH0_API_AUDIENCE: str = os.getenv("AUTH0_API_AUDIENCE", "https://qing-agent-api")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

settings = Settings()
