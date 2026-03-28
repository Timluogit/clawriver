"""数据模型 - Pydantic schemas"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

# ============ Agent/用户 ============

class AgentCreate(BaseModel):
    """注册Agent"""
    name: str = Field(..., min_length=2, max_length=50, description="Agent名称")
    description: Optional[str] = Field(None, max_length=500, description="Agent描述")

class AgentResponse(BaseModel):
    """Agent信息"""
    agent_id: str
    name: str
    description: Optional[str]
    api_key: Optional[str] = None  # 仅在注册时返回
    credits: int
    reputation_score: float
    total_sales: int
    total_purchases: int
    created_at: datetime

class AgentBalance(BaseModel):
    """账户余额"""
    agent_id: str
    credits: int
    total_earned: int
    total_spent: int

class CreditTransaction(BaseModel):
    """积分流水记录"""
    tx_id: str
    tx_type: str
    amount: int
    balance_after: int
    related_id: Optional[str] = None
    description: Optional[str] = None
    commission: Optional[int] = None
    created_at: datetime

class CreditHistoryList(BaseModel):
    """积分流水列表"""
    items: List[CreditTransaction]
    total: int
    page: int
    page_size: int

# ============ 记忆 ============

class MemoryContent(BaseModel):
    """记忆内容（结构化）"""
    title: str = Field(..., min_length=2, max_length=200)
    summary: str = Field(..., min_length=10, max_length=500)
    content: dict = Field(..., description="记忆具体内容（JSON）")
    format_type: str = Field(default="template", description="格式：template/strategy/data/case/warning")

class MemoryCreate(BaseModel):
    """上传记忆"""
    title: str = Field(..., min_length=2, max_length=200)
    category: Optional[str] = Field(None, description="分类路径，如：Douyin/Marketing。留空则自动分类")
    tags: List[str] = Field(default=[], description="标签列表")
    content: dict = Field(..., description="记忆内容（JSON）")
    summary: str = Field(..., min_length=10, max_length=500)
    format_type: str = Field(default="template", description="类型：template/strategy/data/case/warning")
    price: int = Field(default=0, ge=0, description="建议星尘数（0=免费汲取）")
    verification_data: Optional[dict] = Field(None, description="验证数据（可选）")
    expires_days: Optional[int] = Field(None, description="有效期天数（可选）")

class MemoryUpdate(BaseModel):
    """更新记忆"""
    content: Optional[dict] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    changelog: Optional[str] = None

class MemoryResponse(BaseModel):
    """记忆信息"""
    memory_id: str
    seller_agent_id: str
    seller_name: str
    seller_reputation: float
    seller_level: Optional[str] = Field(default=None, description="卖家等级: newbie/bronze/silver/gold")
    title: str
    category: str
    tags: List[str]
    summary: str
    content_preview: Optional[str] = Field(default=None, description="内容预览（前50字）")
    format_type: str
    price: int = Field(description="价格（积分）")
    purchase_count: int
    favorite_count: int
    avg_score: float
    verification_score: Optional[float]
    executability_score: int = Field(default=0, description="Agent可执行度（0-100）")
    message: Optional[str] = Field(default=None, description="提示信息（如隐私脱敏警告）")
    created_at: datetime
    updated_at: datetime

class MemoryDetail(MemoryResponse):
    """记忆详情（购买后）"""
    content: dict
    verification_data: Optional[dict]

class MemoryList(BaseModel):
    """记忆列表"""
    items: List[MemoryResponse]
    total: int
    page: int
    page_size: int

class MemoryVersionResponse(BaseModel):
    """记忆版本信息"""
    version_id: str
    memory_id: str
    version_number: int
    title: str
    category: str
    tags: List[str]
    summary: str
    content: dict
    format_type: str
    price: int
    changelog: Optional[str]
    created_at: datetime

class MemoryVersionList(BaseModel):
    """记忆版本列表"""
    items: List[MemoryVersionResponse]
    total: int

# ============ 交易 ============

class PurchaseRequest(BaseModel):
    """购买记忆"""
    memory_id: str

class PurchaseResponse(BaseModel):
    """购买结果"""
    success: bool
    message: str
    memory_id: str
    credits_spent: int
    remaining_credits: int
    memory_content: Optional[dict] = None

class RateRequest(BaseModel):
    """评价记忆"""
    memory_id: str
    score: int = Field(..., ge=1, le=5, description="评分1-5")
    comment: Optional[str] = Field(None, max_length=500)
    effectiveness: Optional[int] = Field(None, ge=1, le=5, description="实际效果1-5")

class RateResponse(BaseModel):
    """评价结果"""
    success: bool
    message: str
    new_avg_score: float

class AppreciateRequest(BaseModel):
    """随缘打赏"""
    stardust: int = Field(..., ge=1, le=10000, description="随缘星尘数")
    message: Optional[str] = Field(None, max_length=200, description="感谢留言（可选）")

class AppreciateResponse(BaseModel):
    """打赏结果"""
    success: bool
    message: str
    stardust_given: int
    remaining_balance: int

# ============ 验证 ============

class VerificationRequest(BaseModel):
    """验证记忆"""
    score: int = Field(..., ge=1, le=5, description="验证分数 1-5")
    comment: Optional[str] = Field(None, max_length=500, description="验证评论")

class VerificationResponse(BaseModel):
    """验证结果"""
    success: bool
    message: str
    memory_id: str
    verification_score: float
    verification_count: int
    reward_credits: int

# ============ 市场 ============

class MarketTrend(BaseModel):
    """市场趋势"""
    category: str
    memory_count: int
    total_sales: int
    avg_price: float
    trending_tags: List[str]

class TrendResponse(BaseModel):
    """趋势响应"""
    trends: List[MarketTrend]
    period: str

# ============ API响应 ============

class APIResponse(BaseModel):
    """通用响应"""
    success: bool
    message: str
    data: Optional[dict] = None

# ============ 经验捕获 ============

class CaptureRequest(BaseModel):
    """捕获单个经验"""
    task_description: str = Field(..., min_length=2, max_length=200, description="任务描述")
    work_log: str = Field(..., min_length=10, description="工作日志（做了什么、尝试了什么、结果如何）")
    outcome: str = Field(..., description="结果类型: success(成功) | failure(失败) | partial(部分成功)")
    category: Optional[str] = Field(None, description="分类（可选，如：抖音/投流）")
    tags: Optional[List[str]] = Field(default=[], description="标签列表（可选）")

class CaptureAnalysis(BaseModel):
    """捕获分析结果"""
    title: str
    summary: str
    content: dict
    category: str
    tags: List[str]
    format_type: str
    price: int

class CaptureResponse(BaseModel):
    """捕获单个经验结果"""
    success: bool
    message: str
    memory_id: Optional[str] = None
    analysis: Optional[CaptureAnalysis] = None

class BatchCaptureRequest(BaseModel):
    """批量捕获经验"""
    items: List[CaptureRequest] = Field(..., min_items=1, max_items=10, description="批量捕获项（最多10个）")

class BatchCaptureResponse(BaseModel):
    """批量捕获结果"""
    success: bool
    message: str
    results: List[CaptureResponse]
    success_count: int
    failure_count: int

# ============ 团队管理 ============

class TeamCreate(BaseModel):
    """创建团队"""
    name: str = Field(..., min_length=2, max_length=50, description="团队名称")
    description: Optional[str] = Field(None, max_length=500, description="团队描述")

class TeamUpdate(BaseModel):
    """更新团队"""
    name: Optional[str] = Field(None, min_length=2, max_length=50, description="团队名称")
    description: Optional[str] = Field(None, max_length=500, description="团队描述")

class TeamResponse(BaseModel):
    """团队信息"""
    team_id: str
    name: str
    description: Optional[str]
    owner_agent_id: str
    owner_name: str
    member_count: int
    memory_count: int
    credits: int
    total_earned: int
    total_spent: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

class TeamMemberResponse(BaseModel):
    """团队成员信息"""
    id: int
    team_id: str
    agent_id: str
    agent_name: str
    role: str
    joined_at: datetime
    is_active: bool

class TeamInviteCodeCreate(BaseModel):
    """生成邀请码"""
    expires_days: int = Field(7, ge=1, le=30, description="有效期天数")

class TeamInviteCodeResponse(BaseModel):
    """邀请码信息"""
    invite_code_id: str
    team_id: str
    code: str
    is_active: bool
    expires_at: datetime
    created_at: datetime

class TeamInviteCodeJoin(BaseModel):
    """通过邀请码加入团队"""
    code: str = Field(..., min_length=8, max_length=8, description="邀请码")

class TeamMemberRoleUpdate(BaseModel):
    """更新成员角色"""
    role: str = Field(..., pattern="^(owner|admin|member)$", description="角色: owner/admin/member")

class TeamCreditAdd(BaseModel):
    """充值积分"""
    amount: int = Field(..., gt=0, description="充值金额（分）")

class TeamCreditTransfer(BaseModel):
    """转账"""
    to_agent_id: str = Field(..., description="接收者Agent ID")
    amount: int = Field(..., gt=0, description="转账金额（分）")

class TeamCreditTransaction(BaseModel):
    """团队积分流水记录"""
    tx_id: str
    team_id: str
    agent_id: Optional[str]
    agent_name: Optional[str]
    tx_type: str
    amount: int
    balance_after: int
    related_id: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

class TeamCreditHistoryList(BaseModel):
    """团队积分流水列表"""
    items: List[TeamCreditTransaction]
    total: int
    page: int
    page_size: int

class TeamCreditsInfo(BaseModel):
    """团队积分池信息"""
    team_id: str
    credits: int
    total_earned: int
    total_spent: int

# ============ 团队记忆协作 ============

class TeamMemoryCreate(BaseModel):
    """创建团队共享记忆"""
    title: str = Field(..., min_length=2, max_length=200, description="标题")
    category: str = Field(..., description="分类路径")
    tags: List[str] = Field(default=[], description="标签列表")
    content: dict = Field(..., description="记忆内容（JSON）")
    summary: str = Field(..., min_length=10, max_length=500, description="摘要")
    format_type: str = Field(default="template", description="类型：template/strategy/data/case/warning")
    price: int = Field(default=0, ge=0, description="价格（积分）")
    team_access_level: str = Field(
        default="team_only",
        pattern="^(private|team_only|public)$",
        description="可见性：private=仅创建者|team_only=仅团队|public=公开"
    )
    verification_data: Optional[dict] = Field(None, description="验证数据（可选）")
    expires_days: Optional[int] = Field(None, description="有效期天数（可选）")

class TeamMemoryUpdate(BaseModel):
    """更新团队记忆"""
    content: Optional[dict] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    changelog: Optional[str] = None

class TeamMemoryResponse(BaseModel):
    """团队记忆信息"""
    memory_id: str
    team_id: Optional[str]
    team_name: Optional[str]
    created_by_agent_id: str
    created_by_name: str
    title: str
    category: str
    tags: List[str]
    summary: str
    format_type: str
    price: int
    purchase_count: int
    favorite_count: int
    avg_score: float
    verification_score: Optional[float]
    team_access_level: str
    created_at: datetime
    updated_at: datetime

class TeamMemoryDetail(TeamMemoryResponse):
    """团队记忆详情"""
    content: dict
    verification_data: Optional[dict]

class TeamMemoryList(BaseModel):
    """团队记忆列表"""
    items: List[TeamMemoryResponse]
    total: int
    page: int
    page_size: int

class TeamMemoryPurchase(BaseModel):
    """团队购买记忆"""
    memory_id: str

class TeamMemoryPurchaseResponse(BaseModel):
    """团队购买结果"""
    success: bool
    message: str
    memory_id: str
    credits_spent: int
    team_credits_remaining: int
    memory_content: Optional[dict] = None

# ============ 团队统计 ============

class TeamStatsResponse(BaseModel):
    """团队统计数据"""
    team_id: str
    name: str
    member_count: int
    memory_count: int
    team_memories_count: int
    total_purchases: int
    total_sales: int
    credits: int
    total_earned: int
    total_spent: int
    active_members_7d: int  # 7天活跃成员数
    active_members_30d: int  # 30天活跃成员数
    created_at: datetime

class MemberActivityStats(BaseModel):
    """成员活跃度统计"""
    agent_id: str
    agent_name: str
    role: str
    memories_created: int  # 创建的记忆数
    memories_purchased: int  # 汲取的知识数
    purchases_count: int  # 总汲取次数
    last_active_at: datetime  # 最后活跃时间

# ============ 团队活动日志 ============

class TeamActivityLog(BaseModel):
    """团队活动日志"""
    activity_id: str
    team_id: str
    agent_id: Optional[str]
    agent_name: Optional[str]
    activity_type: str  # memory_created/memory_updated/memory_deleted/memory_purchased/member_joined/member_left
    description: str
    related_id: Optional[str]  # 关联ID（记忆ID、购买ID等）
    extra_data: Optional[dict]  # 额外信息
    created_at: datetime

class TeamActivityList(BaseModel):
    """团队活动日志列表"""
    items: List[TeamActivityLog]
    total: int
    page: int
    page_size: int


# ============ 搜索分析 ============

class SearchLogCreate(BaseModel):
    """创建搜索日志"""
    agent_id: str
    query: str
    search_type: str = "hybrid"
    category: Optional[str] = None
    platform: Optional[str] = None
    format_type: Optional[str] = None
    min_score: Optional[float] = None
    max_price: Optional[int] = None
    sort_by: Optional[str] = None
    result_count: int
    top_result_id: Optional[str] = None
    response_time_ms: int
    semantic_score: Optional[float] = None
    keyword_score: Optional[float] = None
    ab_test_id: Optional[str] = None
    ab_test_group: Optional[str] = None
    session_id: Optional[str] = None

class SearchLogResponse(BaseModel):
    """搜索日志信息"""
    log_id: str
    agent_id: str
    agent_name: str
    query: str
    search_type: str
    category: Optional[str]
    platform: Optional[str]
    format_type: Optional[str]
    min_score: Optional[float]
    max_price: Optional[int]
    sort_by: Optional[str]
    result_count: int
    top_result_id: Optional[str]
    response_time_ms: int
    semantic_score: Optional[float]
    keyword_score: Optional[float]
    ab_test_id: Optional[str]
    ab_test_group: Optional[str]
    session_id: Optional[str]
    created_at: datetime

class SearchClickCreate(BaseModel):
    """创建搜索点击记录"""
    agent_id: str
    search_log_id: str
    memory_id: str
    position: int
    click_type: str = "detail"
    ab_test_id: Optional[str] = None
    ab_test_group: Optional[str] = None

class SearchClickResponse(BaseModel):
    """搜索点击信息"""
    click_id: str
    search_log_id: str
    memory_id: str
    memory_title: str
    position: int
    agent_id: str
    agent_name: str
    click_type: str
    ab_test_id: Optional[str]
    ab_test_group: Optional[str]
    created_at: datetime

class SearchTrend(BaseModel):
    """搜索趋势"""
    query: str
    count: int
    avg_result_count: float
    avg_response_time_ms: float
    top_categories: List[str]

class SearchQualityMetrics(BaseModel):
    """搜索质量指标"""
    total_searches: int
    unique_users: int
    avg_result_count: float
    avg_response_time_ms: float
    ctr: float  # 点击率
    zero_results_rate: float  # 零结果率
    top_queries: List[str]
    top_zero_result_queries: List[str]

class SearchPerformanceStats(BaseModel):
    """搜索性能统计"""
    period: str  # hour/day/week
    search_count: int
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    slow_searches_count: int  # 慢查询数量（>1s）

class UserSearchBehavior(BaseModel):
    """用户搜索行为"""
    agent_id: str
    agent_name: str
    total_searches: int
    unique_queries: int
    avg_searches_per_day: float
    avg_result_count: float
    ctr: float
    last_search_at: datetime
    favorite_queries: List[str]

class SearchAnalyticsResponse(BaseModel):
    """搜索分析响应"""
    trends: List[SearchTrend]
    quality: SearchQualityMetrics
    performance: SearchPerformanceStats
    zero_results_queries: List[str]
    user_behavior: List[UserSearchBehavior]

# ============ A/B测试 ============

class ABTestCreate(BaseModel):
    """创建A/B测试"""
    name: str
    description: Optional[str] = None
    test_type: str  # algorithm/reranking/filtering/sorting
    start_at: datetime
    end_at: datetime
    split_ratio: dict  # {"A": 0.5, "B": 0.5}
    group_configs: dict  # {"A": {...}, "B": {...}}
    metrics: List[str]  # ["ctr", "zero_results_rate", "avg_response_time"]

class ABTestResponse(BaseModel):
    """A/B测试信息"""
    test_id: str
    name: str
    description: Optional[str]
    created_by_agent_id: str
    created_by_name: str
    test_type: str
    start_at: datetime
    end_at: datetime
    split_ratio: dict
    group_configs: dict
    metrics: List[str]
    total_searches: int
    group_stats: Optional[dict]
    results: Optional[dict]
    significance: Optional[float]
    winner: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

class ABTestList(BaseModel):
    """A/B测试列表"""
    items: List[ABTestResponse]
    total: int

class ABTestGroupStats(BaseModel):
    """A/B测试组统计"""
    group: str
    searches: int
    clicks: int
    ctr: float
    avg_result_count: float
    avg_response_time_ms: float
    zero_results_rate: float

class ABTestResult(BaseModel):
    """A/B测试结果"""
    test_id: str
    name: str
    status: str
    group_stats: List[ABTestGroupStats]
    metrics_comparison: dict
    significance: Optional[float]
    winner: Optional[str]
    recommendation: str
