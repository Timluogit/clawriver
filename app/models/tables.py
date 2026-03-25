"""数据库表模型"""
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime, JSON, ForeignKey, UniqueConstraint, Index
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
    
    # 元数据
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Memory(Base):
    """记忆表"""
    __tablename__ = "memories"

    memory_id = Column(String(50), primary_key=True, default=lambda: gen_id("mem"))
    seller_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    # 团队协作字段
    team_id = Column(String(50), ForeignKey("teams.team_id"), nullable=True, index=True)
    team_access_level = Column(String(20), default="private")  # private/team_only/public
    created_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True, index=True)  # 记忆创建者（团队记忆场景）

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

    # 验证
    verification_data = Column(JSON, nullable=True)
    verification_score = Column(Float, nullable=True)

    # Agent可执行度评分（0-100，自动计算）
    executability_score = Column(Integer, default=0)

    # 状态
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)

    # 自动遗忘字段
    expiry_time = Column(DateTime, nullable=True, index=True)  # 记忆过期时间（自动遗忘）
    ttl_days = Column(Integer, nullable=True)  # 生存时间（天），用于计算expiry_time

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    team = relationship("Team", back_populates="memories", foreign_keys=[team_id])
    created_by = relationship("Agent", foreign_keys=[created_by_agent_id])

    # 索引
    __table_args__ = (
        Index('idx_memories_team_access', 'team_id', 'team_access_level'),
        Index('idx_memories_expiry', 'expiry_time', 'is_active'),
        Index('idx_memories_ttl', 'ttl_days'),
    )

class Purchase(Base):
    """购买记录表"""
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

class Verification(Base):
    """记忆验证表"""
    __tablename__ = "verifications"

    verification_id = Column(String(50), primary_key=True, default=lambda: gen_id("ver"))
    memory_id = Column(String(50), ForeignKey("memories.memory_id"), nullable=False, index=True)
    verifier_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    score = Column(Integer, nullable=False)  # 验证分数 1-5
    comment = Column(Text, nullable=True)  # 验证评论

    created_at = Column(DateTime, server_default=func.now())

class MemoryVersion(Base):
    """记忆版本表"""
    __tablename__ = "memory_versions"

    version_id = Column(String(50), primary_key=True, default=lambda: gen_id("ver"))
    memory_id = Column(String(50), ForeignKey("memories.memory_id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    # 快照数据
    title = Column(String(200), nullable=False)
    category = Column(String(200), nullable=False)
    tags = Column(JSON, default=[])
    summary = Column(Text, nullable=False)
    content = Column(JSON, nullable=False)
    format_type = Column(String(50), default="template")
    price = Column(Integer, nullable=False)

    # 更新说明
    changelog = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

class PlatformStats(Base):
    """平台统计表"""
    __tablename__ = "platform_stats"

    stats_id = Column(String(50), primary_key=True, default=lambda: gen_id("stats"))

    # 累计数据
    total_transactions = Column(Integer, default=0)  # 总交易数
    total_revenue = Column(Integer, default=0)  # 平台总收入（佣金）
    total_volume = Column(Integer, default=0)  # 总交易额（含佣金）

    # 当日数据
    daily_transactions = Column(Integer, default=0)  # 当日交易数
    daily_revenue = Column(Integer, default=0)  # 当日佣金收入
    daily_volume = Column(Integer, default=0)  # 当日交易额

    date = Column(DateTime, nullable=True)  # 统计日期
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Team(Base):
    """团队表"""
    __tablename__ = "teams"

    team_id = Column(String(50), primary_key=True, default=lambda: gen_id("team"))

    # 基本信息
    name = Column(String(50), nullable=False, index=True)  # 团队名称
    description = Column(Text, nullable=True)  # 团队描述

    # Owner 信息
    owner_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    # 统计
    member_count = Column(Integer, default=1)  # 成员数量（含 Owner）
    memory_count = Column(Integer, default=0)  # 团队记忆数量

    # 积分池
    credits = Column(Integer, default=0)  # 团队积分
    total_earned = Column(Integer, default=0)  # 总收入
    total_spent = Column(Integer, default=0)  # 总支出

    # 状态
    is_active = Column(Boolean, default=True)  # 是否活跃
    archived_at = Column(DateTime, nullable=True)  # 归档时间（解散时）

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="team", cascade="all, delete-orphan")
    invite_codes = relationship("TeamInviteCode", back_populates="team", cascade="all, delete-orphan")
    credit_transactions = relationship("TeamCreditTransaction", back_populates="team", cascade="all, delete-orphan")
    owner = relationship("Agent", foreign_keys=[owner_agent_id])


class TeamMember(Base):
    """团队成员表"""
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, autoincrement=True)

    team_id = Column(String(50), ForeignKey("teams.team_id"), nullable=False, index=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    # 角色枚举
    role = Column(String(20), nullable=False, default="member")  # owner/admin/member

    # 元数据
    joined_at = Column(DateTime, server_default=func.now())  # 加入时间
    left_at = Column(DateTime, nullable=True)  # 离开时间（退出或被移除）
    is_active = Column(Boolean, default=True)  # 是否活跃

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    team = relationship("Team", back_populates="members")
    agent = relationship("Agent")

    # 索引和约束
    __table_args__ = (
        UniqueConstraint('team_id', 'agent_id', name='uq_team_member'),
        Index('idx_team_members_active', 'team_id', 'is_active'),
    )


class TeamInviteCode(Base):
    """团队邀请码表"""
    __tablename__ = "team_invite_codes"

    invite_code_id = Column(String(50), primary_key=True, default=lambda: gen_id("inv"))

    team_id = Column(String(50), ForeignKey("teams.team_id"), nullable=False, index=True)
    code = Column(String(8), unique=True, nullable=False, index=True)  # 8位邀请码

    # 状态
    is_active = Column(Boolean, default=True)  # 是否有效
    used_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True)  # 使用者
    used_at = Column(DateTime, nullable=True)  # 使用时间

    # 有效期
    expires_at = Column(DateTime, nullable=False)  # 过期时间（默认7天）

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    team = relationship("Team", back_populates="invite_codes")
    used_by = relationship("Agent")


class TeamCreditTransaction(Base):
    """团队积分交易流水表"""
    __tablename__ = "team_credit_transactions"

    tx_id = Column(String(50), primary_key=True, default=lambda: gen_id("tctx"))

    team_id = Column(String(50), ForeignKey("teams.team_id"), nullable=False, index=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True, index=True)  # 操作者（充值时为成员，其他可为空）

    tx_type = Column(String(50), nullable=False)  # recharge（充值）/purchase（购买）/sale（销售）/refund（退款）
    amount = Column(Integer, nullable=False)  # 正数=收入，负数=支出
    balance_after = Column(Integer, nullable=False)  # 交易后余额

    related_id = Column(String(50), nullable=True)  # 关联ID（记忆ID、购买ID等）
    description = Column(String(200), nullable=True)  # 说明

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    team = relationship("Team", back_populates="credit_transactions")
    agent = relationship("Agent")


class TeamActivityLog(Base):
    """团队活动日志表"""
    __tablename__ = "team_activity_logs"

    activity_id = Column(String(50), primary_key=True, default=lambda: gen_id("act"))

    team_id = Column(String(50), ForeignKey("teams.team_id"), nullable=False, index=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True, index=True)  # 操作者（可为空，如系统操作）

    activity_type = Column(String(50), nullable=False, index=True)  # memory_created/memory_updated/memory_deleted/memory_purchased/member_joined/member_left/credits_added/credits_spent
    description = Column(Text, nullable=False)  # 活动描述
    related_id = Column(String(50), nullable=True, index=True)  # 关联ID（记忆ID、购买ID等）
    extra_data = Column(JSON, nullable=True)  # 额外信息（避免使用 metadata 保留字）

    # 时间戳
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # 关系
    team = relationship("Team")
    agent = relationship("Agent")

    # 索引
    __table_args__ = (
        Index('idx_team_activity_team_type', 'team_id', 'activity_type'),
        Index('idx_team_activity_created', 'team_id', 'created_at'),
    )


class AuditLog(Base):
    """审计日志表"""
    __tablename__ = "audit_logs"

    log_id = Column(String(50), primary_key=True, default=lambda: gen_id("audit"))

    # 操作者信息
    actor_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True, index=True)
    actor_name = Column(String(100), nullable=True)  # 操作者名称快照（即使删除用户也能追溯）

    # 操作信息
    action_type = Column(String(50), nullable=False, index=True)  # login/create/update/delete/purchase/export/...
    action_category = Column(String(50), nullable=False, index=True)  # auth/memory/team/transaction/system

    # 目标对象
    target_type = Column(String(50), nullable=True, index=True)  # agent/memory/team/purchase/...
    target_id = Column(String(50), nullable=True, index=True)
    target_name = Column(String(200), nullable=True)  # 目标对象名称快照

    # 请求信息
    http_method = Column(String(10), nullable=True)  # GET/POST/PUT/DELETE
    endpoint = Column(String(200), nullable=True)  # API endpoint
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(String(500), nullable=True)

    # 操作结果
    status = Column(String(20), nullable=False, index=True)  # success/failure/forbidden/not_found/error
    status_code = Column(Integer, nullable=True)  # HTTP状态码
    error_message = Column(Text, nullable=True)

    # 详细信息（脱敏后）
    request_data = Column(JSON, nullable=True)  # 请求数据（敏感信息已脱敏）
    response_data = Column(JSON, nullable=True)  # 响应数据（敏感信息已脱敏）
    changes = Column(JSON, nullable=True)  # 变更详情（update操作）

    # 安全信息
    session_id = Column(String(100), nullable=True)  # 会话ID
    request_id = Column(String(100), nullable=True, index=True)  # 请求追踪ID

    # 不可篡改签名
    signature = Column(String(100), nullable=True)  # 日志内容的数字签名
    signature_algorithm = Column(String(50), nullable=True)  # 签名算法（如 RSA-SHA256）
    signature_timestamp = Column(DateTime, nullable=True)  # 签名时间戳

    # 时间戳
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # 关系
    actor = relationship("Agent", foreign_keys=[actor_agent_id])

    # 索引
    __table_args__ = (
        Index('idx_audit_actor_action', 'actor_agent_id', 'action_type'),
        Index('idx_audit_target', 'target_type', 'target_id'),
        Index('idx_audit_time_range', 'created_at', 'action_type'),
        Index('idx_audit_status_time', 'status', 'created_at'),
    )


class AuditLogExport(Base):
    """审计日志导出记录表"""
    __tablename__ = "audit_log_exports"

    export_id = Column(String(50), primary_key=True, default=lambda: gen_id("exp"))

    # 导出者信息
    exported_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)
    exported_by_name = Column(String(100), nullable=True)

    # 导出配置
    export_format = Column(String(20), nullable=False)  # csv/json/pdf

    # 过滤条件
    filters = Column(JSON, nullable=False)  # 时间范围、操作类型、用户等过滤条件
    record_count = Column(Integer, default=0)  # 导出的记录数

    # 导出状态
    status = Column(String(20), nullable=False, index=True)  # pending/processing/completed/failed
    progress = Column(Integer, default=0)  # 进度 0-100
    error_message = Column(Text, nullable=True)

    # 文件信息
    file_path = Column(String(500), nullable=True)  # 导出文件存储路径
    file_size = Column(Integer, nullable=True)  # 文件大小（字节）
    file_url = Column(String(500), nullable=True)  # 下载链接（临时）
    expires_at = Column(DateTime, nullable=True)  # 下载链接过期时间

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    # 关系
    exported_by = relationship("Agent", foreign_keys=[exported_by_agent_id])


class SearchLog(Base):
    """搜索日志表"""
    __tablename__ = "search_logs"

    log_id = Column(String(50), primary_key=True, default=lambda: gen_id("search"))

    # 搜索信息
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)
    query = Column(Text, nullable=False)  # 搜索查询
    search_type = Column(String(20), nullable=False, index=True)  # vector/keyword/hybrid

    # 过滤条件
    category = Column(String(200), nullable=True, index=True)
    platform = Column(String(50), nullable=True, index=True)
    format_type = Column(String(50), nullable=True, index=True)
    min_score = Column(Float, nullable=True)
    max_price = Column(Integer, nullable=True)
    sort_by = Column(String(20), nullable=True)  # relevance/created_at/purchase_count/price

    # 搜索结果
    result_count = Column(Integer, default=0)  # 返回的结果数
    top_result_id = Column(String(50), nullable=True)  # 第一个结果ID（用于点击追踪）

    # 性能指标
    response_time_ms = Column(Integer, nullable=False)  # 响应时间（毫秒）
    semantic_score = Column(Float, nullable=True)  # 语义搜索得分（如果有）
    keyword_score = Column(Float, nullable=True)  # 关键词搜索得分（如果有）

    # A/B测试信息
    ab_test_id = Column(String(50), nullable=True, index=True)  # A/B测试ID
    ab_test_group = Column(String(10), nullable=True)  # A/B分组

    # 用户会话信息
    session_id = Column(String(100), nullable=True, index=True)  # 会话ID（追踪搜索路径）

    # 时间戳
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # 关系
    agent = relationship("Agent", foreign_keys=[agent_id])

    # 索引
    __table_args__ = (
        Index('idx_search_logs_agent_time', 'agent_id', 'created_at'),
        Index('idx_search_logs_query_time', 'query', 'created_at'),
        Index('idx_search_logs_type_time', 'search_type', 'created_at'),
    )


class SearchClick(Base):
    """搜索点击记录表"""
    __tablename__ = "search_clicks"

    click_id = Column(String(50), primary_key=True, default=lambda: gen_id("click"))

    # 关联信息
    search_log_id = Column(String(50), ForeignKey("search_logs.log_id"), nullable=False, index=True)
    memory_id = Column(String(50), ForeignKey("memories.memory_id"), nullable=False, index=True)

    # 点击位置
    position = Column(Integer, nullable=False)  # 在搜索结果中的位置（1-based）

    # 用户信息
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    # 点击行为
    click_type = Column(String(20), nullable=False)  # detail/purchase/favorite

    # A/B测试信息（复制自搜索日志）
    ab_test_id = Column(String(50), nullable=True, index=True)
    ab_test_group = Column(String(10), nullable=True)

    # 时间戳
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # 关系
    search_log = relationship("SearchLog", foreign_keys=[search_log_id])
    memory = relationship("Memory", foreign_keys=[memory_id])
    agent = relationship("Agent", foreign_keys=[agent_id])

    # 索引
    __table_args__ = (
        Index('idx_search_clicks_agent_time', 'agent_id', 'created_at'),
        Index('idx_search_clicks_memory_time', 'memory_id', 'created_at'),
    )


class SearchABTest(Base):
    """搜索A/B测试配置表"""
    __tablename__ = "search_ab_tests"

    test_id = Column(String(50), primary_key=True, default=lambda: gen_id("abtest"))

    # 测试基本信息
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # 创建者信息
    created_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    # 测试配置
    test_type = Column(String(50), nullable=False)  # algorithm/reranking/filtering/sorting
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)

    # 分流配置
    split_ratio = Column(JSON, nullable=False)  # {"A": 0.5, "B": 0.5}

    # A/B组配置
    group_configs = Column(JSON, nullable=False)  # {"A": {"algorithm": "vector"}, "B": {"algorithm": "hybrid"}}

    # 目标指标
    metrics = Column(JSON, nullable=False)  # ["ctr", "zero_results_rate", "avg_response_time"]

    # 统计信息
    total_searches = Column(Integer, default=0)
    group_stats = Column(JSON, nullable=True)  # {"A": {"searches": 100, "clicks": 25}, "B": {...}}

    # 测试结果
    results = Column(JSON, nullable=True)  # 统计分析结果
    significance = Column(Float, nullable=True)  # 统计显著性 p-value
    winner = Column(String(10), nullable=True)  # 获胜组

    # 状态
    status = Column(String(20), nullable=False, default="draft")  # draft/running/completed/cancelled

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    created_by = relationship("Agent", foreign_keys=[created_by_agent_id])

    # 索引
    __table_args__ = (
        Index('idx_search_ab_tests_status', 'status', 'created_at'),
        Index('idx_search_ab_tests_time', 'start_at', 'end_at'),
    )


class AnomalyEvent(Base):
    """异常事件表"""
    __tablename__ = "anomaly_events"

    event_id = Column(String(50), primary_key=True, default=lambda: gen_id("anom"))

    # 异常类型
    anomaly_type = Column(String(50), nullable=False, index=True)  # login/transaction/query/behavior/system
    anomaly_subtype = Column(String(50), nullable=False, index=True)  # remote_login/large_amount/sensitive_word/...
    severity = Column(String(20), nullable=False, index=True)  # critical/warning/info

    # 目标对象
    target_type = Column(String(50), nullable=True, index=True)  # agent/memory/team/...
    target_id = Column(String(50), nullable=True, index=True)

    # 异常详情
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=True)  # 异常证据数据

    # 检测信息
    detected_at = Column(DateTime, server_default=func.now(), index=True)
    detection_rule_id = Column(String(50), ForeignKey("anomaly_rules.rule_id"), nullable=True, index=True)
    confidence = Column(Float, nullable=True)  # 检测置信度 0-1

    # 状态
    status = Column(String(20), nullable=False, default="new", index=True)  # new/investigating/resolved/false_positive
    confirmed_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)

    # 关系
    detection_rule = relationship("AnomalyRule", foreign_keys=[detection_rule_id])
    confirmed_by = relationship("Agent", foreign_keys=[confirmed_by_agent_id])
    alerts = relationship("AnomalyAlert", back_populates="event", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_anomaly_events_type_time', 'anomaly_type', 'detected_at'),
        Index('idx_anomaly_events_severity_time', 'severity', 'detected_at'),
        Index('idx_anomaly_events_status_time', 'status', 'detected_at'),
    )


class AnomalyAlert(Base):
    """异常告警表"""
    __tablename__ = "anomaly_alerts"

    alert_id = Column(String(50), primary_key=True, default=lambda: gen_id("alert"))

    # 关联异常事件
    event_id = Column(String(50), ForeignKey("anomaly_events.event_id"), nullable=False, index=True)

    # 告警信息
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)  # critical/warning/info

    # 通知渠道
    channel_type = Column(String(20), nullable=False, index=True)  # email/webhook/slack
    channel_config = Column(JSON, nullable=True)  # 渠道配置

    # 告警状态
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending/sent/failed/acknowledged
    sent_at = Column(DateTime, nullable=True)
    ack_at = Column(DateTime, nullable=True)
    ack_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True)

    # 错误信息
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # 聚合信息
    aggregation_key = Column(String(100), nullable=True, index=True)  # 聚合键
    aggregated_count = Column(Integer, default=1)  # 聚合数量

    # 时间戳
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # 关系
    event = relationship("AnomalyEvent", back_populates="alerts")
    ack_by = relationship("Agent", foreign_keys=[ack_by_agent_id])

    # 索引
    __table_args__ = (
        Index('idx_anomaly_alerts_status_time', 'status', 'created_at'),
        Index('idx_anomaly_alerts_channel_time', 'channel_type', 'created_at'),
    )


class AnomalyRule(Base):
    """异常检测规则表"""
    __tablename__ = "anomaly_rules"

    rule_id = Column(String(50), primary_key=True, default=lambda: gen_id("rule"))

    # 规则信息
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # 规则配置
    anomaly_type = Column(String(50), nullable=False, index=True)  # login/transaction/query/behavior/system
    anomaly_subtype = Column(String(50), nullable=False, index=True)
    detection_logic = Column(JSON, nullable=False)  # 检测逻辑配置

    # 阈值配置
    threshold_config = Column(JSON, nullable=True)  # 阈值配置

    # 告警配置
    alert_severity = Column(String(20), nullable=False, default="warning")  # critical/warning/info
    alert_channels = Column(JSON, nullable=False)  # ["email", "webhook", "slack"]
    alert_cooldown_minutes = Column(Integer, default=60)  # 告警冷却时间（分钟）

    # 统计信息
    total_detections = Column(Integer, default=0)  # 总检测次数
    true_positive_count = Column(Integer, default=0)  # 真阳性数
    false_positive_count = Column(Integer, default=0)  # 假阳性数

    # 状态
    is_enabled = Column(Boolean, default=True, index=True)

    # 元数据
    created_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    created_by = relationship("Agent", foreign_keys=[created_by_agent_id])

    # 索引
    __table_args__ = (
        Index('idx_anomaly_rules_type_enabled', 'anomaly_type', 'is_enabled'),
    )


# ============ 细粒度权限系统 ============

class Permission(Base):
    """权限表 - 定义所有权限"""
    __tablename__ = "permissions"

    permission_id = Column(String(50), primary_key=True, default=lambda: gen_id("perm"))

    # 权限基本信息
    code = Column(String(100), unique=True, nullable=False, index=True)  # 权限代码，如：memory.create, team.admin
    name = Column(String(200), nullable=False)  # 权限名称
    description = Column(Text, nullable=True)  # 权限描述
    category = Column(String(50), nullable=False, index=True)  # 权限分类：memory/team/user/system

    # 权限层级
    level = Column(String(20), nullable=False, default="operation")  # operation/resource/system
    resource_type = Column(String(50), nullable=True, index=True)  # 资源类型：memory/team/agent/transaction

    # 权限状态
    is_system = Column(Boolean, default=False)  # 是否系统内置权限（不可删除）
    is_active = Column(Boolean, default=True, index=True)

    # 元数据
    created_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    created_by = relationship("Agent", foreign_keys=[created_by_agent_id])

    # 索引
    __table_args__ = (
        Index('idx_permissions_category_active', 'category', 'is_active'),
    )


class Role(Base):
    """角色表"""
    __tablename__ = "roles"

    role_id = Column(String(50), primary_key=True, default=lambda: gen_id("role"))

    # 角色基本信息
    code = Column(String(100), unique=True, nullable=False, index=True)  # 角色代码，如：admin, user, moderator
    name = Column(String(200), nullable=False)  # 角色名称
    description = Column(Text, nullable=True)  # 角色描述
    category = Column(String(50), nullable=False, index=True)  # 角色分类：system/platform/team

    # 角色层级
    level = Column(Integer, default=0)  # 角色级别（数字越大权限越高）
    inherit_from_id = Column(String(50), ForeignKey("roles.role_id"), nullable=True, index=True)  # 继承自哪个角色

    # 角色状态
    is_system = Column(Boolean, default=False)  # 是否系统内置角色（不可删除）
    is_active = Column(Boolean, default=True, index=True)

    # 统计
    member_count = Column(Integer, default=0)  # 拥有此角色的用户数

    # 元数据
    created_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    created_by = relationship("Agent", foreign_keys=[created_by_agent_id])
    inherit_from = relationship("Role", remote_side=[role_id], foreign_keys=[inherit_from_id])

    # 索引
    __table_args__ = (
        Index('idx_roles_category_active', 'category', 'is_active'),
        Index('idx_roles_level', 'level'),
    )


class RolePermission(Base):
    """角色-权限关系表"""
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    role_id = Column(String(50), ForeignKey("roles.role_id"), nullable=False, index=True)
    permission_id = Column(String(50), ForeignKey("permissions.permission_id"), nullable=False, index=True)

    # 权限限制条件（可选）
    conditions = Column(JSON, nullable=True)  # 条件限制，如：{"resource_type": "memory", "max_count": 10}

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    role = relationship("Role")
    permission = relationship("Permission")

    # 索引和约束
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
        Index('idx_role_permissions_role', 'role_id'),
        Index('idx_role_permissions_permission', 'permission_id'),
    )


class UserPermission(Base):
    """用户-权限关系表"""
    __tablename__ = "user_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)
    permission_id = Column(String(50), ForeignKey("permissions.permission_id"), nullable=False, index=True)

    # 权限类型
    grant_type = Column(String(20), nullable=False, default="allow")  # allow/deny（拒绝优先级更高）

    # 权限范围
    scope = Column(JSON, nullable=True)  # 权限范围，如：{"memory_ids": ["mem_xxx"], "team_ids": ["team_xxx"]}

    # 有效期
    expires_at = Column(DateTime, nullable=True)  # 权限过期时间

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    created_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True)

    # 关系
    agent = relationship("Agent", foreign_keys=[agent_id])
    permission = relationship("Permission")
    created_by = relationship("Agent", foreign_keys=[created_by_agent_id])

    # 索引和约束
    __table_args__ = (
        UniqueConstraint('agent_id', 'permission_id', 'scope', name='uq_user_permission_scope'),
        Index('idx_user_permissions_agent', 'agent_id'),
        Index('idx_user_permissions_permission', 'permission_id'),
        Index('idx_user_permissions_agent_active', 'agent_id', 'expires_at'),
    )


class ResourcePermission(Base):
    """资源-权限关系表"""
    __tablename__ = "resource_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 资源信息
    resource_type = Column(String(50), nullable=False, index=True)  # memory/team/agent/transaction
    resource_id = Column(String(50), nullable=False, index=True)  # 资源ID

    # 授权对象
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True, index=True)  # 授权给哪个用户
    role_id = Column(String(50), ForeignKey("roles.role_id"), nullable=True, index=True)  # 授权给哪个角色

    # 权限
    permission_code = Column(String(100), nullable=False, index=True)  # 权限代码

    # 权限类型
    grant_type = Column(String(20), nullable=False, default="allow")  # allow/deny

    # 权限条件
    conditions = Column(JSON, nullable=True)  # 条件限制

    # 有效期
    expires_at = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    created_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True)

    # 关系
    agent = relationship("Agent", foreign_keys=[agent_id])
    role = relationship("Role", foreign_keys=[role_id])
    created_by = relationship("Agent", foreign_keys=[created_by_agent_id])

    # 索引
    __table_args__ = (
        Index('idx_resource_permissions_resource', 'resource_type', 'resource_id'),
        Index('idx_resource_permissions_agent', 'agent_id'),
        Index('idx_resource_permissions_role', 'role_id'),
        Index('idx_resource_permissions_permission', 'permission_code'),
        Index('idx_resource_permissions_resource_agent', 'resource_type', 'resource_id', 'agent_id'),
    )


class PermissionCache(Base):
    """权限缓存表 - 用于快速权限检查"""
    __tablename__ = "permission_cache"

    cache_id = Column(String(50), primary_key=True, default=lambda: gen_id("pcache"))

    # 缓存键
    agent_id = Column(String(50), nullable=False, index=True)
    cache_key = Column(String(200), unique=True, nullable=False, index=True)  # 缓存键，如：agent_perm_xxx

    # 缓存内容
    permissions = Column(JSON, nullable=False)  # 权限列表
    roles = Column(JSON, nullable=False)  # 角色列表

    # 缓存元数据
    version = Column(Integer, default=1)  # 版本号（用于失效）
    hit_count = Column(Integer, default=0)  # 命中次数

    # 时间戳
    expires_at = Column(DateTime, nullable=False, index=True)  # 过期时间
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 索引
    __table_args__ = (
        Index('idx_permission_cache_agent', 'agent_id', 'expires_at'),
    )


class PermissionAuditLog(Base):
    """权限操作审计日志表"""
    __tablename__ = "permission_audit_logs"

    log_id = Column(String(50), primary_key=True, default=lambda: gen_id("paudit"))

    # 操作者
    actor_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)
    actor_name = Column(String(100), nullable=False)

    # 操作类型
    action_type = Column(String(50), nullable=False, index=True)  # grant/revoke/check
    action_category = Column(String(50), nullable=False, index=True)  # permission/role/user/resource

    # 操作对象
    target_type = Column(String(50), nullable=True, index=True)  # agent/role/permission/resource
    target_id = Column(String(50), nullable=True, index=True)
    target_name = Column(String(200), nullable=True)

    # 权限详情
    permission_code = Column(String(100), nullable=True, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(50), nullable=True)

    # 操作结果
    status = Column(String(20), nullable=False, index=True)  # success/forbidden/not_found/error
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # 详细信息
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    extra_data = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # 关系
    actor = relationship("Agent", foreign_keys=[actor_agent_id])

    # 索引
    __table_args__ = (
        Index('idx_permission_audit_actor_action', 'actor_agent_id', 'action_type'),
        Index('idx_permission_audit_target', 'target_type', 'target_id'),
        Index('idx_permission_audit_permission', 'permission_code'),
        Index('idx_permission_audit_time_range', 'created_at', 'action_type'),
    )


# ============ 用户画像系统 ============

class UserProfile(Base):
    """用户画像表（静态事实层）"""
    __tablename__ = "user_profiles"

    profile_id = Column(String(50), primary_key=True, default=lambda: gen_id("uprof"))

    # 关联用户
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, unique=True, index=True)

    # 个人信息
    real_name = Column(String(100), nullable=True)  # 真实姓名
    job_title = Column(String(100), nullable=True)  # 职位
    company = Column(String(200), nullable=True)  # 公司
    location = Column(String(200), nullable=True)  # 地点
    timezone = Column(String(50), nullable=True)  # 时区

    # 偏好
    language = Column(String(20), default="zh")  # 首选语言
    editor = Column(String(50), nullable=True)  # 编辑器偏好（VSCode/Vim/Emacs）
    theme = Column(String(20), default="dark")  # 主题偏好（light/dark）
    ui_scale = Column(String(20), default="medium")  # UI缩放（small/medium/large）

    # 习惯
    work_hours = Column(JSON, nullable=True)  # 工作时间 {"start": "09:00", "end": "18:00"}
    work_days = Column(JSON, nullable=True)  # 工作日 ["Monday", "Tuesday", ...]
    preferred_command = Column(String(100), nullable=True)  # 常用命令前缀

    # 技能
    skills = Column(JSON, nullable=True)  # 编程语言和框架 [{"name": "Python", "level": "advanced"}, ...]
    tech_stack = Column(JSON, nullable=True)  # 技术栈 ["Python", "FastAPI", "PostgreSQL"]

    # 兴趣
    interests = Column(JSON, nullable=True)  # 兴趣领域 ["AI", "Machine Learning", "NLP"]
    research_areas = Column(JSON, nullable=True)  # 研究方向 ["NLP", "LLM", "RAG"]

    # 统计
    confidence_score = Column(Float, default=0.5)  # 画像可信度（基于自动提取质量）
    completeness_score = Column(Float, default=0.0)  # 画像完整度（字段填充率）

    # 自动遗忘配置
    default_ttl_days = Column(Integer, default=30)  # 默认TTL（天），用于新事实
    ttl_config = Column(JSON, nullable=True)  # TTL配置 {"personal": 365, "preference": 90, "habit": 180, "skill": 365}

    last_updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    agent = relationship("Agent")
    facts = relationship("ProfileFact", back_populates="profile", cascade="all, delete-orphan")
    changes = relationship("ProfileChange", back_populates="profile", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_user_profiles_agent', 'agent_id'),
        Index('idx_user_profiles_updated', 'last_updated_at'),
    )


class ProfileFact(Base):
    """画像事实表（结构化的事实存储）"""
    __tablename__ = "profile_facts"

    fact_id = Column(String(50), primary_key=True, default=lambda: gen_id("fact"))

    # 关联画像
    profile_id = Column(String(50), ForeignKey("user_profiles.profile_id"), nullable=False, index=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    # 事实内容
    fact_type = Column(String(50), nullable=False, index=True)  # personal/preference/habit/skill/interest
    fact_key = Column(String(100), nullable=False, index=True)  # 事实键（如：language/editor）
    fact_value = Column(JSON, nullable=False)  # 事实值（可以是字符串、数字、数组等）
    confidence = Column(Float, default=0.8)  # 置信度（0-1）
    source = Column(String(50), nullable=True)  # 来源（manual/auto_extraction）
    source_reference = Column(String(200), nullable=True)  # 来源引用（对话ID等）

    # 过期控制
    expires_at = Column(DateTime, nullable=True)  # 过期时间（用于自动遗忘）
    is_valid = Column(Boolean, default=True, index=True)  # 是否有效

    # 时间戳
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    profile = relationship("UserProfile", back_populates="facts")
    agent = relationship("Agent")

    # 索引
    __table_args__ = (
        Index('idx_profile_facts_profile_type', 'profile_id', 'fact_type'),
        Index('idx_profile_facts_agent_valid', 'agent_id', 'is_valid'),
        Index('idx_profile_facts_expires', 'expires_at', 'is_valid'),
    )


class UserDynamicContext(Base):
    """用户动态上下文表（动态上下文层）"""
    __tablename__ = "user_dynamic_contexts"

    context_id = Column(String(50), primary_key=True, default=lambda: gen_id("ucont"))

    # 关联用户
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    # 动态上下文
    current_task = Column(String(200), nullable=True)  # 当前任务
    current_project = Column(String(200), nullable=True)  # 当前项目
    current_focus = Column(String(200), nullable=True)  # 当前关注点

    # 工作状态
    work_state = Column(String(50), default="active")  # active/away/busy/offline
    recent_activities = Column(JSON, nullable=True)  # 最近活动 [{"type": "search", "query": "...", "timestamp": ...}, ...]

    # 会话信息
    last_session_id = Column(String(100), nullable=True)  # 最后会话ID
    last_search_query = Column(Text, nullable=True)  # 最后搜索查询
    last_interacted_memory = Column(String(50), nullable=True)  # 最后交互的记忆

    # 推荐信息
    recommended_categories = Column(JSON, nullable=True)  # 推荐分类
    suggested_topics = Column(JSON, nullable=True)  # 建议主题

    # 统计
    session_count_today = Column(Integer, default=0)  # 今日会话数
    search_count_today = Column(Integer, default=0)  # 今日搜索数
    last_updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    agent = relationship("Agent")

    # 索引
    __table_args__ = (
        Index('idx_user_dynamic_contexts_agent', 'agent_id'),
        Index('idx_user_dynamic_contexts_updated', 'last_updated_at'),
        Index('idx_user_dynamic_contexts_work_state', 'agent_id', 'work_state'),
    )


class ProfileChange(Base):
    """画像变更历史表"""
    __tablename__ = "profile_changes"

    change_id = Column(String(50), primary_key=True, default=lambda: gen_id("pchange"))

    # 关联画像
    profile_id = Column(String(50), ForeignKey("user_profiles.profile_id"), nullable=False, index=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    # 变更信息
    change_type = Column(String(50), nullable=False, index=True)  # created/updated/deleted/expired
    field_name = Column(String(100), nullable=False, index=True)  # 变更字段
    old_value = Column(JSON, nullable=True)  # 旧值
    new_value = Column(JSON, nullable=True)  # 新值

    # 变更来源
    source = Column(String(50), nullable=False)  # manual/auto_extraction/auto_forget
    source_reference = Column(String(200), nullable=True)  # 来源引用

    # 变更原因
    change_reason = Column(Text, nullable=True)  # 变更原因

    # 时间戳
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # 关系
    profile = relationship("UserProfile", back_populates="changes")
    agent = relationship("Agent")

    # 索引
    __table_args__ = (
        Index('idx_profile_changes_profile', 'profile_id', 'created_at'),
        Index('idx_profile_changes_agent', 'agent_id', 'created_at'),
        Index('idx_profile_changes_type_field', 'change_type', 'field_name'),
    )


# ============ AWS IAM-like 权限策略系统 ============

class PermissionPolicy(Base):
    """
    权限策略表 - AWS IAM Policy 风格

    支持 AWS IAM 风格的 JSON 策略文档：
    {
        "Version": "2024-01-01",
        "Statement": [
            {
                "Sid": "AllowMemoryRead",
                "Effect": "Allow",
                "Action": ["memory:get", "memory:list"],
                "Resource": ["memory:*"],
                "Condition": {
                    "StringEquals": {"category": "技术"},
                    "IpAddress": {"source_ip": "10.0.0.0/8"}
                }
            }
        ]
    }
    """
    __tablename__ = "permission_policies"

    policy_id = Column(String(50), primary_key=True, default=lambda: gen_id("pol"))

    # 策略基本信息
    name = Column(String(200), nullable=False, index=True)  # 策略名称
    description = Column(Text, nullable=True)  # 策略描述
    policy_type = Column(String(20), nullable=False, default="custom", index=True)  # managed/custom/inline

    # 策略文档（AWS IAM 风格 JSON）
    policy_document = Column(JSON, nullable=False)  # 完整的策略文档

    # 策略状态
    is_active = Column(Boolean, default=True, index=True)
    is_system = Column(Boolean, default=False)  # 系统内置策略（不可删除）

    # 版本管理
    default_version_id = Column(String(50), nullable=True)  # 默认版本ID
    version_count = Column(Integer, default=1)  # 版本数量

    # 统计信息
    attachment_count = Column(Integer, default=0)  # 附加次数

    # 元数据
    created_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    created_by = relationship("Agent", foreign_keys=[created_by_agent_id])
    versions = relationship("PolicyVersion", back_populates="policy", cascade="all, delete-orphan")
    attachments = relationship("PolicyAttachment", back_populates="policy", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_policies_type_active', 'policy_type', 'is_active'),
        Index('idx_policies_created_by', 'created_by_agent_id'),
    )


class PolicyVersion(Base):
    """
    策略版本表 - 支持策略版本管理

    类似 AWS IAM PolicyVersion，最多保留 N 个版本
    """
    __tablename__ = "policy_versions"

    version_id = Column(String(50), primary_key=True, default=lambda: gen_id("pver"))

    # 关联策略
    policy_id = Column(String(50), ForeignKey("permission_policies.policy_id"), nullable=False, index=True)

    # 版本信息
    version_number = Column(Integer, nullable=False)  # 版本号（1, 2, 3...）
    is_default = Column(Boolean, default=False)  # 是否为默认版本

    # 策略文档快照
    policy_document = Column(JSON, nullable=False)  # 该版本的策略文档

    # 变更说明
    changelog = Column(Text, nullable=True)  # 变更说明

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    policy = relationship("PermissionPolicy", back_populates="versions")

    # 索引和约束
    __table_args__ = (
        UniqueConstraint('policy_id', 'version_number', name='uq_policy_version'),
        Index('idx_policy_versions_policy', 'policy_id', 'version_number'),
        Index('idx_policy_versions_default', 'policy_id', 'is_default'),
    )


class PolicyAttachment(Base):
    """
    策略附加表 - 将策略附加到用户或角色

    类似 AWS IAM PolicyAttachment，支持 managed 和 inline 策略
    """
    __tablename__ = "policy_attachments"

    attachment_id = Column(String(50), primary_key=True, default=lambda: gen_id("patt"))

    # 关联策略
    policy_id = Column(String(50), ForeignKey("permission_policies.policy_id"), nullable=False, index=True)

    # 附加目标（二选一）
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True, index=True)  # 附加到用户
    role_id = Column(String(50), ForeignKey("roles.role_id"), nullable=True, index=True)  # 附加到角色

    # 附加类型
    attachment_type = Column(String(20), nullable=False, default="managed")  # managed/inline

    # 资源范围限制（可选）
    resource_scope = Column(JSON, nullable=True)  # {"resource_types": ["memory", "team"], "resource_ids": ["mem_xxx"]}

    # 条件覆盖（可选，在策略条件基础上额外限制）
    condition_overrides = Column(JSON, nullable=True)  # 覆盖或附加条件

    # 有效期
    expires_at = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    created_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True)

    # 关系
    policy = relationship("PermissionPolicy", back_populates="attachments")
    agent = relationship("Agent", foreign_keys=[agent_id])
    role = relationship("Role", foreign_keys=[role_id])
    created_by = relationship("Agent", foreign_keys=[created_by_agent_id])

    # 索引和约束
    __table_args__ = (
        Index('idx_policy_attachments_policy', 'policy_id'),
        Index('idx_policy_attachments_agent', 'agent_id'),
        Index('idx_policy_attachments_role', 'role_id'),
        Index('idx_policy_attachments_agent_active', 'agent_id', 'expires_at'),
        Index('idx_policy_attachments_role_active', 'role_id', 'expires_at'),
    )
