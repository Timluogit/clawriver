"""核心数据库表模型 - 简化版，只保留 5 张核心表"""
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

class Agent(Base):
    """Agent/用户表"""
    __tablename__ = "agents"
    
    agent_id = Column(String(50), primary_key=True, default=lambda: gen_id("agent"))
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    api_key = Column(String(100), unique=True, nullable=False, index=True)
    
    # 积分
    credits = Column(Integer, default=100)
    total_earned = Column(Integer, default=0)
    total_spent = Column(Integer, default=0)
    
    # 统计
    reputation_score = Column(Float, default=5.0)
    total_sales = Column(Integer, default=0)
    total_purchases = Column(Integer, default=0)
    memories_uploaded = Column(Integer, default=0)
    contribution_count = Column(Integer, default=0)  # 贡献次数（用于激励系统）
    
    # 元数据
    is_active = Column(Boolean, default=True)
    role = Column(String(20), default="user")  # user / moderator / admin
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Memory(Base):
    """记忆表"""
    __tablename__ = "memories"

    memory_id = Column(String(50), primary_key=True, default=lambda: gen_id("mem"))
    seller_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    # 内容
    title = Column(String(200), nullable=False)
    category = Column(String(200), nullable=False, index=True)
    tags = Column(JSON, default=[])
    summary = Column(Text, nullable=False)
    content = Column(JSON, nullable=False)  # 结构化内容
    format_type = Column(String(50), default="template")  # template/strategy/data/case/warning

    # 交易
    price = Column(Integer, nullable=False)  # 分
    purchase_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)

    # 评分
    total_score = Column(Integer, default=0)
    score_count = Column(Integer, default=0)
    avg_score = Column(Float, default=0.0)

    # Agent可执行度评分（0-100，自动计算）
    executability_score = Column(Integer, default=0)

    # 状态
    is_active = Column(Boolean, default=True)
    low_quality = Column(Boolean, default=False)  # 低质量标记

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # FTS5 虚拟表索引
    __table_args__ = (
        Index('idx_memories_category', 'category'),
        Index('idx_memories_created', 'created_at'),
        Index('idx_memories_avg_score', 'avg_score'),
    )

class Purchase(Base):
    """购买/汲取记录表"""
    __tablename__ = "purchases"
    
    purchase_id = Column(String(50), primary_key=True, default=lambda: gen_id("pur"))
    buyer_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)
    seller_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)
    memory_id = Column(String(50), ForeignKey("memories.memory_id"), nullable=False, index=True)
    
    amount = Column(Integer, nullable=False)  # 支付金额（分）
    seller_income = Column(Integer, nullable=False)  # 卖家实际收入
    platform_fee = Column(Integer, nullable=False)  # 平台佣金
    
    created_at = Column(DateTime, server_default=func.now())

class Rating(Base):
    """评价表"""
    __tablename__ = "ratings"
    
    rating_id = Column(String(50), primary_key=True, default=lambda: gen_id("rat"))
    memory_id = Column(String(50), ForeignKey("memories.memory_id"), nullable=False, index=True)
    buyer_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False)
    
    score = Column(Integer, nullable=False)  # 1-5
    effectiveness = Column(Integer, nullable=True)  # 1-5
    comment = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())

class Transaction(Base):
    """积分交易流水表"""
    __tablename__ = "transactions"

    tx_id = Column(String(50), primary_key=True, default=lambda: gen_id("tx"))
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    tx_type = Column(String(50), nullable=False)  # purchase/sale/recharge/withdraw/refund/bonus
    amount = Column(Integer, nullable=False)  # 正数=收入，负数=支出
    balance_after = Column(Integer, nullable=False)

    related_id = Column(String(50), nullable=True)  # 关联ID（购买/销售ID）
    description = Column(String(200), nullable=True)
    commission = Column(Integer, nullable=True)  # 平台佣金（仅在销售记录中有值）

    created_at = Column(DateTime, server_default=func.now())


class SearchLog(Base):
    """搜索日志表"""
    __tablename__ = "search_logs"
    
    log_id = Column(String(50), primary_key=True, default=lambda: gen_id("slog"))
    query = Column(String(500), nullable=False, index=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True, index=True)
    result_count = Column(Integer, default=0)
    has_results = Column(Boolean, default=False)
    category = Column(String(200), nullable=True)
    execution_time_ms = Column(Float, default=0.0)
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_search_logs_created', 'created_at'),
        Index('idx_search_logs_query', 'query'),
    )
