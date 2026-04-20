from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class RiskScoreRecord(Base):
    """RiskScore历史记录"""
    __tablename__ = 'risk_score_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)

    # 风险评估
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)  # low/medium/high
    threshold = Column(Float, nullable=False)
    risk_factors = Column(Text, nullable=True)  # JSON

    # 上下文
    page_type = Column(String(50), nullable=True)
    job_url = Column(String(500), nullable=True)
    action_taken = Column(String(50), nullable=True)  # auto_recovery/confirm/skip/modify

    # 结果
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class DynamicThresholdState(Base):
    """动态阈值状态"""
    __tablename__ = 'dynamic_threshold_states'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)

    consecutive_success = Column(Integer, default=0)
    consecutive_fail = Column(Integer, default=0)
    current_threshold = Column(Float, default=0.7)

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JobQueueItem(Base):
    """Job队列项"""
    __tablename__ = 'job_queue_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True)

    job_url = Column(String(500), nullable=False)
    job_title = Column(String(200), nullable=True)
    company = Column(String(200), nullable=True)

    status = Column(String(20), default='pending')  # pending/running/completed/failed/skipped/relocated
    priority = Column(Integer, default=0)
    attempts = Column(Integer, default=0)

    # 投递结果
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)
    result = Column(String(50), nullable=True)

    # 重定位
    relocator_source = Column(String(500), nullable=True)
    similarity_score = Column(Float, nullable=True)

    # 错误
    error_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class StealthConfig(Base):
    """Stealth模式配置"""
    __tablename__ = 'stealth_configs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)

    enabled = Column(Boolean, default=True)
    remove_webdriver = Column(Boolean, default=True)
    randomize_ua = Column(Boolean, default=True)
    randomize_canvas = Column(Boolean, default=True)
    randomize_webgl = Column(Boolean, default=True)
    randomize_audio = Column(Boolean, default=True)
    human_scroll = Column(Boolean, default=True)
    human_mouse = Column(Boolean, default=True)
    random_delay_min = Column(Integer, default=1)
    random_delay_max = Column(Integer, default=3)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
