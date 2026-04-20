from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    # ===== 求职方向 =====
    # 支持多选: ['planning'] = 品牌策划方向, ['design'] = 品牌设计方向, ['planning', 'design'] = 两者
    directions = Column(JSON, default=["planning"])

    # 每个方向的投递上限
    planning_daily_limit = Column(Integer, default=10)
    design_daily_limit = Column(Integer, default=10)
    total_daily_limit = Column(Integer, default=20)

    # ===== 职位关键词 =====
    # 可投职位（包含这些关键词优先投递）
    include_keywords = Column(JSON, default=list)
    # 加分关键词（高分投递）
    prefer_keywords = Column(JSON, default=list)
    # 排除职位（直接过滤）
    exclude_keywords = Column(JSON, default=list)

    # ===== 公司边界 =====
    # 优先公司类型
    prefer_companies = Column(JSON, default=list)
    # 排除公司类型
    exclude_companies = Column(JSON, default=list)

    # ===== 行业边界 =====
    # 优先行业
    prefer_industries = Column(JSON, default=list)
    # 排除行业
    exclude_industries = Column(JSON, default=list)

    # ===== 模糊岗位二次打分 =====
    # 需要二次打分的模糊岗位
    fuzzy_keywords = Column(JSON, default=list)
    # 打分阈值 (默认 0.5)
    scoring_threshold = Column(Float, default=0.5)

    # ===== 基础配置 =====
    target_cities = Column(JSON, default=["深圳"])
    exclude_areas = Column(JSON, default=["宝安区"])

    # 薪资期望
    salary_min = Column(Integer, default=6000)
    salary_max = Column(Integer, default=15000)

    # 经验要求
    experience_min = Column(Integer, default=1)
    experience_max = Column(Integer, default=5)

    # ===== 投递配置 =====
    # 每日投递上限
    daily_apply_limit = Column(Integer, default=10)

    # 平台 Cookie/密码（加密存储）
    platform_credentials = Column(JSON, default=dict)

    # 用户关联
    user = relationship("User", back_populates="profile")
