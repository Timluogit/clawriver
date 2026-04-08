"""记忆服务 - 统一版本

升级后的记忆服务，集成 Qdrant 向量搜索和团队记忆功能
"""
import json
import re
from typing import Optional, List, Literal, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_, or_, desc, case, literal_column
from sqlalchemy.orm import selectinload
from app.models.tables import Agent, Memory, Purchase, Rating, Transaction

# Optional: 向后兼容，这些表不再使用
try:
    from app.models.tables import (
        Verification, PlatformStats, MemoryVersion, 
        Team, TeamMember, TeamActivityLog
    )
except ImportError:
    Verification = None
    PlatformStats = None
    MemoryVersion = None
    Team = None
    TeamMember = None
    TeamActivityLog = None
from app.models.schemas import (
    MemoryCreate, MemoryUpdate, MemoryResponse, MemoryDetail,
    MemoryList, PurchaseResponse, RateRequest, RateResponse,
    VerificationRequest, VerificationResponse,
    TeamMemoryCreate, TeamMemoryUpdate, TeamMemoryResponse,
    TeamMemoryDetail, TeamMemoryList
)
from app.core.config import settings
from app.core.exceptions import AppError, NOT_FOUND, FORBIDDEN
try:
    from app.search.hybrid_search import get_hybrid_engine
    _has_qdrant = True
except ImportError:
    _has_qdrant = False
import uuid
from datetime import datetime
from math import log10


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ============ 自动分类 ============

CATEGORY_KEYWORDS = {
    "Douyin/Marketing": ["抖音", "douyin", "tiktok", "投流", "dou+", "千川", "短视频", "直播", "带货"],
    "Douyin/Content": ["抖音", "douyin", "爆款", "viral", "视频创作", "脚本", "拍摄"],
    "Xiaohongshu/Marketing": ["小红书", "xiaohongshu", "RED", "种草", "笔记", "蒲公英"],
    "Xiaohongshu/Content": ["小红书", "笔记", "封面", "标题", "爆款笔记"],
    "WeChat/Official": ["微信", "wechat", "公众号", "服务号", "小程序"],
    "WeChat/Private": ["微信", "社群", "私域", "朋友圈", "社群运营"],
    "Bilibili/Creator": ["B站", "bilibili", "UP主", "投稿", "番剧"],
    "AI/Development": ["AI", "LLM", "GPT", "模型", "prompt", "agent", "MCP", "RAG", "embedding", "向量"],
    "AI/Tools": ["AI工具", "claude", "cursor", "copilot", "chatgpt", "openai", "api"],
    "Programming/Python": ["python", "pip", "django", "flask", "fastapi", "pandas", "numpy"],
    "Programming/JavaScript": ["javascript", "js", "node", "npm", "react", "vue", "typescript"],
    "Programming/General": ["代码", "code", "编程", "programming", "开发", "debug", "bug", "git"],
    "Database": ["数据库", "database", "SQL", "MySQL", "PostgreSQL", "SQLite", "Redis", "MongoDB"],
    "DevOps": ["部署", "deploy", "docker", "k8s", "kubernetes", "CI/CD", "nginx", "服务器", "linux"],
    "General/Tools": ["工具", "tools", "效率", "快捷键", "workflow"],
    "General/Data": ["数据", "data", "分析", "analytics", "报表", "可视化"],
}


def auto_classify(title: str, summary: str, content: dict) -> str:
    """根据标题、摘要和内容自动分类"""
    text = f"{title} {summary} {json.dumps(content, ensure_ascii=False)}".lower()

    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > 0:
            scores[category] = score

    if scores:
        best = max(scores, key=scores.get)
        if scores[best] >= 2:
            return best
        # 单关键词匹配也返回，但优先级低
        return best

    return "General"


def calc_executability_score(content: dict, summary: str = "") -> dict:
    """计算知识的Agent可执行度（0-100）

    评判标准（Agent视角）：
    - 有没有可填充的变量模板 {xxx}
    - 有没有条件判断逻辑 (if/else/when)
    - 有没有明确的输入输出格式
    - 内容是否结构化（JSON层数、字段数）
    - 是否包含可执行的命令/API/代码

    Returns:
        {"score": int, "reasons": list, "level": str}
    """
    import re

    score = 0
    reasons = []
    full_text = json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else str(content)
    full_text += " " + (summary or "")

    # 1. 变量模板检测 {variable_name} - 最关键的指标
    # 匹配 {中文或英文变量名} — 模板变量如 {人群}、{topic}
    variables = re.findall(r'\{[a-zA-Z_\u4e00-\u9fff][a-zA-Z0-9_\u4e00-\u9fff]{0,29}\}', full_text)
    if variables:
        score += min(len(variables) * 15, 45)
        reasons.append(f"包含{len(variables)}个可填充变量")
    else:
        reasons.append("无可填充变量模板")

    # 2. 条件逻辑检测
    logic_patterns = re.findall(r'(if|when|否则|如果|条件|判断|case|switch|elif|else)', full_text, re.IGNORECASE)
    if logic_patterns:
        score += min(len(logic_patterns) * 8, 20)
        reasons.append(f"包含{len(logic_patterns)}处条件逻辑")

    # 3. 结构化程度（JSON层数和字段数）
    if isinstance(content, dict):
        field_count = len(content)
        # 检查嵌套层数
        max_depth = 0
        def get_depth(d, depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            if isinstance(d, dict):
                for v in d.values():
                    get_depth(v, depth + 1)
            elif isinstance(d, list):
                for item in d:
                    get_depth(item, depth + 1)
        get_depth(content)

        if field_count >= 3:
            score += 10
            reasons.append(f"结构化内容({field_count}个字段)")
        if max_depth >= 2:
            score += 5
            reasons.append(f"多层嵌套({max_depth}层)")

    # 4. 可执行命令/API检测
    exec_patterns = re.findall(r'(curl|POST|GET|PUT|DELETE|api|endpoint|sdk|pip install|npm install|import|from|def |function|class )', full_text, re.IGNORECASE)
    if exec_patterns:
        score += min(len(exec_patterns) * 5, 15)
        reasons.append(f"包含可执行代码/API({len(exec_patterns)}处)")

    # 5. 步骤/流程检测
    step_patterns = re.findall(r'(步骤|step|第[一二三四五六七八九十\d]步|阶段|流程|流程图|→|=>|->|then)', full_text, re.IGNORECASE)
    if step_patterns:
        score += min(len(step_patterns) * 3, 10)
        reasons.append(f"包含操作步骤({len(step_patterns)}步)")

    # 6. 内容长度（有变量时不惩罚短内容，Agent关心的是模板而非字数）
    content_len = len(full_text)
    if not variables and content_len < 100:
        score = max(score - 20, 0)
        reasons.append("内容过短且无变量模板")
    elif content_len >= 500:
        score += 5
        reasons.append("内容充分(500+字)")
    elif content_len >= 200:
        score += 2

    score = min(score, 100)

    # 等级判定
    if score >= 70:
        level = "excellent"  # 可直接执行
    elif score >= 40:
        level = "usable"  # 需要少量补充
    elif score >= 20:
        level = "partial"  # 需要大量补充
    else:
        level = "useless"  # 正确的废话

    return {"score": score, "reasons": reasons, "level": level}


def get_agent_level(total_transactions: int, avg_score: float = 0) -> str:
    """计算Agent等级"""
    if total_transactions >= 100:
        return "gold"
    elif total_transactions >= 50:
        return "silver"
    elif total_transactions >= 10:
        return "bronze"
    return "newbie"


def memory_to_response(memory: Memory, seller_name: str = "", seller_reputation: float = 5.0, seller_total_sales: int = 0, message: Optional[str] = None) -> MemoryResponse:
    """转换为响应格式"""
    import json as _json

    # 生成内容预览：Agent视角 - 展示结构和变量，而非文字摘要
    content_preview = None
    if memory.content:
        try:
            content = memory.content if isinstance(memory.content, dict) else _json.loads(memory.content)
            if isinstance(content, dict):
                # 提取变量模板作为预览（Agent关心的）
                preview_parts = []
                for k, v in list(content.items())[:3]:
                    if isinstance(v, str):
                        preview_parts.append(f"{k}: {v[:60]}")
                    elif isinstance(v, dict):
                        preview_parts.append(f"{k}: {{...{len(v)}个字段}}")
                    elif isinstance(v, list):
                        preview_parts.append(f"{k}: [{len(v)}项]")
                content_preview = " | ".join(preview_parts)[:120]
            else:
                content_preview = str(content)[:120]
        except (TypeError, ValueError, KeyError):
            content_preview = str(memory.content)[:120]

    return MemoryResponse(
        memory_id=memory.memory_id,
        seller_agent_id=memory.seller_agent_id,
        seller_name=seller_name,
        seller_reputation=seller_reputation,
        seller_level=get_agent_level(seller_total_sales, seller_reputation),
        title=memory.title,
        category=memory.category,
        tags=memory.tags or [],
        summary=memory.summary,
        content_preview=content_preview,
        format_type=memory.format_type,
        price=memory.price,
        purchase_count=memory.purchase_count,
        favorite_count=memory.favorite_count,
        avg_score=memory.avg_score,
        verification_score=memory.verification_score,
        executability_score=getattr(memory, 'executability_score', 0) or 0,
        message=message,
        created_at=memory.created_at,
        updated_at=memory.updated_at
    )


async def upload_memory(db: AsyncSession, seller_id: str, req: MemoryCreate) -> MemoryResponse:
    """上传记忆（带Agent可执行度检测）"""
    # 检查卖家
    seller = await db.execute(select(Agent).where(Agent.agent_id == seller_id))
    seller = seller.scalar_one_or_none()
    if not seller:
        raise ValueError("卖家不存在")

    # ===== Agent可执行度检测 =====
    exec_result = calc_executability_score(req.content, req.summary)

    # 质量门槛：可执行度 < 15 的知识禁止上传
    if exec_result["score"] < 15:
        raise ValueError(
            f"知识可执行度过低({exec_result['score']}/100)。"
            f"Agent视角：{'; '.join(exec_result['reasons'])}。"
            f"请添加可填充的变量模板{{变量名}}、结构化JSON内容或可执行的步骤。"
        )

    # 自动分类（如果未指定）
    category = req.category
    if not category or category.strip() == "":
        category = auto_classify(req.title, req.summary, req.content)

    # 隐私脱敏
    from app.core.privacy import redact_memory_content
    safe_title, safe_summary, safe_content, privacy_findings = redact_memory_content(
        req.title, req.summary, req.content
    )

    memory = Memory(
        memory_id=gen_id("mem"),
        seller_agent_id=seller_id,
        title=safe_title,
        category=category,
        tags=req.tags,
        summary=safe_summary,
        content=safe_content,
        format_type=req.format_type,
        price=req.price,
        verification_data=req.verification_data,
        executability_score=exec_result["score"]
    )

    # 计算验证分数
    if req.verification_data:
        memory.verification_score = _calc_verification_score(req.verification_data)

    # 设置过期时间
    if req.expires_days:
        from datetime import datetime, timedelta
        memory.expires_at = datetime.now() + timedelta(days=req.expires_days)

    db.add(memory)

    # 更新卖家统计
    seller.memories_uploaded += 1

    await db.commit()
    await db.refresh(memory)

    # 创建初始版本快照
    await create_memory_version(db, memory, changelog="初始版本")
    await db.commit()

    # 增量向量化（异步）
    _vectorize_memory_async(memory)

    # 隐私提示信息
    privacy_message = None
    if privacy_findings:
        finding_types = set(f["type"] for f in privacy_findings)
        privacy_message = f"⚠️ 检测到 {len(privacy_findings)} 处敏感信息已自动脱敏，类型：{', '.join(finding_types)}"

    return memory_to_response(memory, seller.name, seller.reputation_score, message=privacy_message)


async def _fallback_search(
    db: AsyncSession,
    base_stmt,
    query: str,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "relevance"
) -> dict:
    """纯 SQL 关键词搜索 — 单次 JOIN 查询（避免 N+1）"""
    # ===== 修复: 使用 JOIN 避免 N+1 =====
    stmt = base_stmt  # base_stmt 已包含 .join(Agent)

    # 关键词匹配（大小写不敏感）
    search_filter = None
    if query:
        q = query.lower()
        search_filter = or_(
            func.lower(Memory.title).contains(q),
            func.lower(Memory.summary).contains(q),
            func.lower(Memory.category).contains(q),
        )
        stmt = stmt.where(search_filter)

    # 排序
    if sort_by == "created_at":
        stmt = stmt.order_by(desc(Memory.created_at))
    elif sort_by == "purchase_count":
        stmt = stmt.order_by(desc(Memory.purchase_count))
    elif sort_by == "price":
        stmt = stmt.order_by(Memory.price)
    elif sort_by == "rating":
        stmt = stmt.order_by(desc(Memory.avg_score))
    else:
        # 相关度排序（默认）：关键词匹配位置 > 标题匹配 > 摘要匹配 > 评分 > 购买数
        if query:
            q_lower = query.lower()
            # 计算相关度分数：
            # - 标题完全匹配：3分
            # - 标题包含：2分
            # - 摘要包含：1分
            # - 加上评分和购买数的权重
            title_exact = case(
                (func.lower(Memory.title) == q_lower, 3),
                else_=0
            )
            title_contains = case(
                (func.lower(Memory.title).contains(q_lower), 2),
                else_=0
            )
            summary_contains = case(
                (func.lower(Memory.summary).contains(q_lower), 1),
                else_=0
            )
            score_normalized = (Memory.avg_score / 5.0) * 1.5
            purchase_normalized = func.log10(Memory.purchase_count + 1) / func.log10(100)
            
            relevance_score = (
                title_exact + 
                title_contains + 
                summary_contains + 
                score_normalized + 
                purchase_normalized
            )
            stmt = stmt.order_by(desc(relevance_score))
        else:
            # 无查询时，使用综合评分排序
            stmt = stmt.order_by(desc(Memory.avg_score), desc(Memory.purchase_count))

    # 获取总数
    count_stmt = select(func.count(Memory.memory_id)).select_from(Memory).where(
        Memory.is_active == True
    )
    if query:
        count_stmt = count_stmt.where(search_filter)
    total = (await db.execute(count_stmt)).scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    # 单次 JOIN 查询获取记忆 + 卖家信息
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        mem = row[0]   # Memory 对象
        seller_name = row[1] if len(row) > 1 else "unknown"
        seller_rep = row[2] if len(row) > 2 else 5.0

        items.append({
            "memory_id": mem.memory_id,
            "seller_agent_id": mem.seller_agent_id,
            "seller_name": seller_name or "unknown",
            "seller_reputation": seller_rep or 5.0,
            "title": mem.title,
            "category": mem.category,
            "tags": mem.tags or [],
            "summary": mem.summary,
            "content_preview": str(mem.content)[:200] if mem.content else "",
            "format_type": mem.format_type,
            "price": mem.price,
            "purchase_count": mem.purchase_count,
            "favorite_count": mem.favorite_count,
            "avg_score": mem.avg_score,
            "verification_score": mem.verification_score,
            "executability_score": getattr(mem, 'executability_score', 0) or 0,
            "created_at": mem.created_at.isoformat() if mem.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "search_type": "keyword_fallback",
    }


async def search_memories(
    db: AsyncSession,
    query: str = "",
    category: str = "",
    platform: str = "",
    format_type: str = "",
    min_score: float = 0,
    max_price: int = 999999,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "relevance",  # relevance, created_at, purchase_count, price
    search_type: Literal["vector", "keyword", "hybrid"] = "hybrid"
) -> MemoryList:
    """搜索记忆（使用 Qdrant 向量搜索）

    Args:
        db: 数据库会话
        query: 搜索关键词
        category: 分类筛选
        platform: 平台筛选
        format_type: 格式筛选
        min_score: 最低评分
        max_price: 最高价格
        page: 页码
        page_size: 每页数量
        sort_by: 排序方式 (relevance=综合评分, created_at=创建时间, purchase_count=购买次数, price=价格)
        search_type: 搜索类型 (vector=向量搜索, keyword=关键词, hybrid=混合，默认hybrid)

    Returns:
        记忆列表
    """
    # 验证 search_type 参数
    if search_type not in ["vector", "keyword", "hybrid"]:
        search_type = "hybrid"

    # 基础查询（不含关键词过滤）
    base_stmt = select(Memory, Agent.name, Agent.reputation_score).join(
        Agent, Memory.seller_agent_id == Agent.agent_id
    ).where(Memory.is_active == True)

    # 应用筛选条件（非文本搜索）
    if category:
        base_stmt = base_stmt.where(func.lower(Memory.category).contains(category.lower()))
    if platform:
        base_stmt = base_stmt.where(Memory.category.startswith(platform))
    if format_type:
        base_stmt = base_stmt.where(Memory.format_type == format_type)
    if min_score > 0:
        base_stmt = base_stmt.where(Memory.avg_score >= min_score)
    if max_price < 999999:
        base_stmt = base_stmt.where(Memory.price <= max_price)

    # 使用混合搜索引擎（Qdrant 可用时）或回退到关键词搜索
    if _has_qdrant:
        hybrid_engine = get_hybrid_engine()
        return await hybrid_engine.search(
            db=db,
            query=query,
            base_stmt=base_stmt,
            search_type=search_type,
            top_k=page_size * page,
            min_score=0.1,
            semantic_weight=0.6,
            keyword_weight=0.4,
            enable_rerank=True,
            page=page,
            page_size=page_size,
            sort_by=sort_by
        )
    else:
        # 回退：纯 SQL 关键词搜索
        return await _fallback_search(
            db=db,
            base_stmt=base_stmt,
            query=query,
            page=page,
            page_size=page_size,
            sort_by=sort_by
        )


async def get_memory_detail(db: AsyncSession, memory_id: str, buyer_id: str = None) -> MemoryDetail:
    """获取记忆详情

    Agent视角：
    - 免费知识：直接展示完整内容（Agent需要立即评估是否有用）
    - 付费知识：需先汲取（购买）才能查看完整内容
    """
    result = await db.execute(
        select(Memory, Agent.name, Agent.reputation_score).join(
            Agent, Memory.seller_agent_id == Agent.agent_id
        ).where(Memory.memory_id == memory_id)
    )
    row = result.first()
    if not row:
        return None

    memory, seller_name, seller_reputation = row

    # 免费知识：任何人可直接查看完整内容
    # 付费知识：需要已购买（或自己上传的）
    if buyer_id and memory.price > 0:
        # 检查是否已购买
        purchase = await db.execute(
            select(Purchase).where(
                and_(Purchase.buyer_agent_id == buyer_id, Purchase.memory_id == memory_id)
            )
        )
        if not purchase.scalar_one_or_none():
            # 检查是否是自己上传的
            if memory.seller_agent_id != buyer_id:
                raise PermissionError("未购买此记忆")

    # 处理 content 字段：如果是字符串则解析为 dict
    import json
    from json import JSONDecodeError
    content = memory.content
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except JSONDecodeError:
            content = {"raw": content}  # 解析失败时保留原始内容

    # 处理 verification_data 字段：如果是字符串则解析为 dict
    verification_data = memory.verification_data
    if verification_data and isinstance(verification_data, str):
        try:
            verification_data = json.loads(verification_data)
        except JSONDecodeError:
            verification_data = {"raw": verification_data}  # 解析失败时保留原始内容

    return MemoryDetail(
        **memory_to_response(memory, seller_name, seller_reputation).model_dump(),
        content=content,
        verification_data=verification_data
    )


async def purchase_memory(db: AsyncSession, buyer_id: str, memory_id: str) -> PurchaseResponse:
    """购买记忆"""
    # Use a transaction to prevent race conditions
    async with db.begin():
        # 获取记忆 (with FOR UPDATE lock to prevent race conditions)
        result = await db.execute(select(Memory).where(Memory.memory_id == memory_id).with_for_update())
        memory = result.scalar_one_or_none()
        if not memory:
            return PurchaseResponse(success=False, message="记忆不存在", memory_id=memory_id, credits_spent=0, remaining_credits=0)

        # 检查是否已购买
        existing = await db.execute(
            select(Purchase).where(
                and_(Purchase.buyer_agent_id == buyer_id, Purchase.memory_id == memory_id)
            )
        )
        if existing.scalar_one_or_none():
            return PurchaseResponse(success=False, message="已购买此记忆", memory_id=memory_id, credits_spent=0, remaining_credits=0)

        # 检查是否是自己的记忆
        if memory.seller_agent_id == buyer_id:
            return PurchaseResponse(success=False, message="不能购买自己的记忆", memory_id=memory_id, credits_spent=0, remaining_credits=0)

        # 获取买家 (with FOR UPDATE lock)
        buyer = await db.execute(select(Agent).where(Agent.agent_id == buyer_id).with_for_update())
        buyer = buyer.scalar_one_or_none()
        if not buyer:
            return PurchaseResponse(success=False, message="买家不存在", memory_id=memory_id, credits_spent=0, remaining_credits=0)

        # 随缘模式：所有记忆免费汲取
        price = 0

        # 更新记忆统计
        memory.purchase_count += 1

        # 创建汲取记录
        purchase = Purchase(
            purchase_id=gen_id("pur"),
            buyer_agent_id=buyer_id,
            seller_agent_id=memory.seller_agent_id,
            memory_id=memory_id,
            amount=0,
            seller_income=0,
            platform_fee=0
        )
        db.add(purchase)

        # 更新买家统计
        buyer.total_purchases += 1

    await db.commit()

    # 处理 content 字段：如果是字符串则解析为 dict
    import json
    from json import JSONDecodeError
    memory_content = memory.content
    if isinstance(memory_content, str):
        try:
            memory_content = json.loads(memory_content)
        except JSONDecodeError:
            memory_content = {"raw": memory_content}  # 解析失败时保留原始内容

    return PurchaseResponse(
        success=True,
        message="汲取成功，知识已汇入",
        memory_id=memory_id,
        credits_spent=0,
        remaining_credits=buyer.credits,
        memory_content=memory_content
    )


async def rate_memory(db: AsyncSession, buyer_id: str, req: RateRequest) -> RateResponse:
    """评价记忆（支持更新已有评价）

    Agent深入使用知识后可以更新评价，这比一次性评价更准确。
    """
    # 检查是否购买过（免费记忆也需先汲取）
    purchase = await db.execute(
        select(Purchase).where(
            and_(Purchase.buyer_agent_id == buyer_id, Purchase.memory_id == req.memory_id)
        )
    )
    if not purchase.scalar_one_or_none():
        raise PermissionError("未购买此记忆")

    # 检查是否已评价 — 支持更新
    existing = await db.execute(
        select(Rating).where(
            and_(Rating.buyer_agent_id == buyer_id, Rating.memory_id == req.memory_id)
        )
    )
    existing_rating = existing.scalar_one_or_none()

    if existing_rating:
        # 更新已有评价
        old_score = existing_rating.score
        existing_rating.score = req.score
        existing_rating.comment = req.comment
        existing_rating.effectiveness = req.effectiveness
        existing_rating.created_at = datetime.now()

        # 更新记忆评分统计
        memory = await db.execute(select(Memory).where(Memory.memory_id == req.memory_id))
        memory = memory.scalar_one_or_none()
        memory.total_score = memory.total_score - old_score + req.score
        memory.avg_score = memory.total_score / memory.score_count if memory.score_count > 0 else req.score

        await db.commit()

        return RateResponse(
            success=True,
            message="评价已更新",
            new_avg_score=memory.avg_score
        )

    # 创建新评价
    rating = Rating(
        rating_id=gen_id("rat"),
        memory_id=req.memory_id,
        buyer_agent_id=buyer_id,
        score=req.score,
        effectiveness=req.effectiveness,
        comment=req.comment
    )
    db.add(rating)

    # 更新记忆评分
    memory = await db.execute(select(Memory).where(Memory.memory_id == req.memory_id))
    memory = memory.scalar_one_or_none()
    memory.total_score += req.score
    memory.score_count += 1
    memory.avg_score = memory.total_score / memory.score_count

    await db.commit()

    return RateResponse(
        success=True,
        message="评价成功",
        new_avg_score=memory.avg_score
    )


def _calc_verification_score(data: dict) -> float:
    """计算验证分数（0-1）"""
    score = 0.0
    if data.get("sample_size"):
        score += min(data["sample_size"] / 1000, 0.3)
    if data.get("success_rate"):
        score += data["success_rate"] * 0.3
    if data.get("data_source"):
        score += 0.2
    if data.get("test_period_days"):
        score += min(data["test_period_days"] / 30, 0.2)
    return round(min(score, 1.0), 2)


async def update_memory(db: AsyncSession, memory_id: str, seller_id: str, updates: MemoryUpdate) -> Optional[MemoryResponse]:
    """更新记忆

    Args:
        db: 数据库会话
        memory_id: 记忆ID
        seller_id: 卖家ID（用于权限验证）
        updates: 要更新的字段（Pydantic模型）

    Returns:
        更新后的记忆响应，如果记忆不存在或无权限则返回None
    """
    # 获取记忆
    result = await db.execute(
        select(Memory).where(Memory.memory_id == memory_id)
    )
    memory = result.scalar_one_or_none()

    if not memory:
        return None

    # 验证权限：只有卖家才能更新
    if memory.seller_agent_id != seller_id:
        raise PermissionError("无权修改此记忆")

    # 提取 changelog（如果有）
    changelog = updates.changelog

    # 更新允许的字段
    if updates.summary is not None:
        memory.summary = updates.summary
    if updates.content is not None:
        memory.content = updates.content
    if updates.tags is not None:
        memory.tags = updates.tags

    # 更新时间戳
    from datetime import datetime
    memory.updated_at = datetime.now()

    await db.commit()
    await db.refresh(memory)

    # 创建新版本快照
    await create_memory_version(db, memory, changelog=changelog)
    await db.commit()

    # 增量向量化更新
    _vectorize_memory_async(memory)

    # 获取卖家信息
    seller = await db.execute(select(Agent).where(Agent.agent_id == seller_id))
    seller = seller.scalar_one_or_none()

    return memory_to_response(memory, seller.name if seller else "", seller.reputation_score if seller else 5.0)


async def get_my_memories(
    db: AsyncSession,
    seller_id: str,
    page: int = 1,
    page_size: int = 20
) -> dict:
    """获取当前Agent上传的所有记忆列表

    Args:
        db: 数据库会话
        seller_id: 卖家ID
        page: 页码
        page_size: 每页数量

    Returns:
        包含记忆列表和销售统计的字典
    """
    # 计算总数
    count_stmt = select(func.count()).select_from(Memory).where(
        and_(Memory.seller_agent_id == seller_id, Memory.is_active == True)
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 获取记忆列表
    stmt = select(Memory).where(
        and_(Memory.seller_agent_id == seller_id, Memory.is_active == True)
    ).order_by(desc(Memory.created_at)).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    memories = result.scalars().all()

    # 转换为响应格式
    items = []
    total_sales = 0
    total_earned = 0

    for memory in memories:
        items.append(memory_to_response(memory, "", 5.0))
        total_sales += memory.purchase_count
        total_earned += memory.purchase_count * memory.price

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "stats": {
            "total_memories": total,
            "total_sales": total_sales,
            "total_earned": total_earned
        }
    }


async def appreciate_memory(db: AsyncSession, buyer_id: str, memory_id: str, stardust: int, message: str = ""):
    """随缘打赏 — 使用者根据体验价值自愿给星尘"""
    from app.models.schemas import AppreciateResponse

    # 获取记忆
    result = await db.execute(select(Memory).where(Memory.memory_id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        return AppreciateResponse(success=False, message="记忆不存在", stardust_given=0, remaining_balance=0)

    # 不能打赏自己
    if memory.seller_agent_id == buyer_id:
        return AppreciateResponse(success=False, message="不能打赏自己的记忆", stardust_given=0, remaining_balance=0)

    # 获取买家
    buyer_result = await db.execute(select(Agent).where(Agent.agent_id == buyer_id))
    buyer = buyer_result.scalar_one_or_none()
    if not buyer:
        return AppreciateResponse(success=False, message="用户不存在", stardust_given=0, remaining_balance=0)

    if buyer.credits < stardust:
        return AppreciateResponse(success=False, message=f"星尘不足（当前 {buyer.credits}，需要 {stardust}）", stardust_given=0, remaining_balance=buyer.credits)

    # 计算分配（5%平台费，95%给作者）
    COMMISSION_RATE = 0.05
    platform_fee = int(stardust * COMMISSION_RATE)
    seller_income = stardust - platform_fee

    # 扣买家星尘
    buyer.credits -= stardust
    buyer.total_spent += stardust

    # 加卖家星尘
    seller_result = await db.execute(select(Agent).where(Agent.agent_id == memory.seller_agent_id))
    seller = seller_result.scalar_one_or_none()
    if seller:
        seller.credits += seller_income
        seller.total_earned += seller_income

    # 创建打赏记录
    purchase = Purchase(
        purchase_id=gen_id("pur"),
        buyer_agent_id=buyer_id,
        seller_agent_id=memory.seller_agent_id,
        memory_id=memory_id,
        amount=stardust,
        seller_income=seller_income,
        platform_fee=platform_fee
    )
    db.add(purchase)

    # 创建交易流水
    tx = Transaction(
        agent_id=buyer_id,
        tx_type="appreciate",
        amount=-stardust,
        balance_after=buyer.credits,
        related_id=memory_id,
        description=f"随缘星尘: {memory.title}" + (f" — {message}" if message else ""),
        commission=platform_fee
    )
    db.add(tx)

    await db.commit()

    return AppreciateResponse(
        success=True,
        message=f"已送出 {stardust} 星尘，感谢你的随缘 🙏",
        stardust_given=stardust,
        remaining_balance=buyer.credits
    )


async def verify_memory(
    db: AsyncSession,
    memory_id: str,
    verifier_id: str,
    req: VerificationRequest
) -> VerificationResponse:
    """验证记忆质量

    验证者可以是任何 Agent（不能验证自己的记忆）
    验证分数范围：1-5
    验证结果会更新记忆的 verification_score 字段
    验证者获得积分奖励

    Args:
        db: 数据库会话
        memory_id: 记忆ID
        verifier_id: 验证者ID
        req: 验证请求

    Returns:
        验证结果

    Raises:
        ValueError: 记忆不存在、已验证过或验证自己的记忆
    """
    # 检查记忆是否存在
    memory_result = await db.execute(
        select(Memory).where(Memory.memory_id == memory_id)
    )
    memory = memory_result.scalar_one_or_none()
    if not memory:
        raise ValueError("记忆不存在")

    # 检查是否是自己的记忆
    if memory.seller_agent_id == verifier_id:
        raise ValueError("不能验证自己的记忆")

    # 检查是否已经验证过
    existing_verification = await db.execute(
        select(Verification).where(
            and_(
                Verification.memory_id == memory_id,
                Verification.verifier_agent_id == verifier_id
            )
        )
    )
    if existing_verification.scalar_one_or_none():
        raise ValueError("已经验证过此记忆")

    # 创建验证记录
    verification = Verification(
        verification_id=gen_id("ver"),
        memory_id=memory_id,
        verifier_agent_id=verifier_id,
        score=req.score,
        comment=req.comment
    )
    db.add(verification)

    # 获取所有验证记录并计算平均分
    all_verifications = await db.execute(
        select(Verification).where(Verification.memory_id == memory_id)
    )
    verifications = all_verifications.scalars().all()

    # 计算新的验证分数（1-5转换为0-1）
    total_score = sum(v.score for v in verifications) + req.score
    avg_score = total_score / (len(verifications) + 1)
    memory.verification_score = round(avg_score / 5.0, 2)

    # 给验证者奖励积分
    verifier = await db.execute(
        select(Agent).where(Agent.agent_id == verifier_id)
    )
    verifier = verifier.scalar_one_or_none()
    if not verifier:
        raise ValueError("验证者不存在")

    REWARD_CREDITS = 5
    verifier.credits += REWARD_CREDITS
    verifier.total_earned += REWARD_CREDITS

    # 创建交易流水
    tx = Transaction(
        agent_id=verifier_id,
        tx_type="bonus",
        amount=REWARD_CREDITS,
        balance_after=verifier.credits,
        related_id=memory_id,
        description=f"验证记忆奖励: {memory.title}"
    )
    db.add(tx)

    await db.commit()

    return VerificationResponse(
        success=True,
        message="验证成功",
        memory_id=memory_id,
        verification_score=memory.verification_score,
        verification_count=len(verifications) + 1,
        reward_credits=REWARD_CREDITS
    )


async def _update_platform_stats(db: AsyncSession, total_amount: int, commission: int):
    """更新平台统计信息

    Args:
        db: 数据库会话
        total_amount: 总交易额
        commission: 平台佣金
    """
    from datetime import datetime, timedelta

    # 获取或创建今日统计
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # 查找今日统计记录
    stats_result = await db.execute(
        select(PlatformStats).where(PlatformStats.date == today)
    )
    stats = stats_result.scalar_one_or_none()

    if stats:
        # 更新现有统计
        stats.total_transactions += 1
        stats.total_revenue += commission
        stats.total_volume += total_amount
        stats.daily_transactions += 1
        stats.daily_revenue += commission
        stats.daily_volume += total_amount
    else:
        # 创建新的统计记录
        stats = PlatformStats(
            total_transactions=1,
            total_revenue=commission,
            total_volume=total_amount,
            daily_transactions=1,
            daily_revenue=commission,
            daily_volume=total_amount,
            date=today
        )
        db.add(stats)


async def create_memory_version(
    db: AsyncSession,
    memory: Memory,
    changelog: Optional[str] = None
) -> MemoryVersion:
    """创建记忆版本快照

    Args:
        db: 数据库会话
        memory: 记忆对象
        changelog: 更新说明（可选）

    Returns:
        创建的版本对象
    """
    # 获取当前最大版本号
    from sqlalchemy import select, func
    stmt = select(func.max(MemoryVersion.version_number)).where(
        MemoryVersion.memory_id == memory.memory_id
    )
    result = await db.execute(stmt)
    max_version = result.scalar() or 0
    next_version = max_version + 1

    # 创建版本快照
    version = MemoryVersion(
        version_id=gen_id("ver"),
        memory_id=memory.memory_id,
        version_number=next_version,
        title=memory.title,
        category=memory.category,
        tags=memory.tags or [],
        summary=memory.summary,
        content=memory.content,
        format_type=memory.format_type,
        price=memory.price,
        changelog=changelog
    )
    db.add(version)
    await db.flush()

    return version


async def get_memory_versions(
    db: AsyncSession,
    memory_id: str,
    page: int = 1,
    page_size: int = 20
) -> dict:
    """获取记忆的所有版本历史

    Args:
        db: 数据库会话
        memory_id: 记忆ID
        page: 页码
        page_size: 每页数量

    Returns:
        版本列表
    """
    # 计算总数
    count_stmt = select(func.count()).select_from(MemoryVersion).where(
        MemoryVersion.memory_id == memory_id
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 获取版本列表（按版本号降序）
    stmt = select(MemoryVersion).where(
        MemoryVersion.memory_id == memory_id
    ).order_by(desc(MemoryVersion.version_number)).offset(
        (page - 1) * page_size
    ).limit(page_size)

    result = await db.execute(stmt)
    versions = result.scalars().all()

    from app.models.schemas import MemoryVersionResponse
    import json
    from json import JSONDecodeError
    items = []
    for v in versions:
        # 处理 content 字段：如果是字符串则解析为 dict
        content = v.content
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except JSONDecodeError:
                content = {"raw": content}  # 解析失败时保留原始内容

        items.append(MemoryVersionResponse(
            version_id=v.version_id,
            memory_id=v.memory_id,
            version_number=v.version_number,
            title=v.title,
            category=v.category,
            tags=v.tags or [],
            summary=v.summary,
            content=content,
            format_type=v.format_type,
            price=v.price,
            changelog=v.changelog,
            created_at=v.created_at
        ))

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


async def get_memory_version(
    db: AsyncSession,
    memory_id: str,
    version_id: str
) -> Optional[dict]:
    """获取特定版本的详细信息

    Args:
        db: 数据库会话
        memory_id: 记忆ID
        version_id: 版本ID

    Returns:
        版本详细信息，如果不存在则返回None
    """
    result = await db.execute(
        select(MemoryVersion).where(
            and_(
                MemoryVersion.memory_id == memory_id,
                MemoryVersion.version_id == version_id
            )
        )
    )
    version = result.scalar_one_or_none()

    if not version:
        return None

    from app.models.schemas import MemoryVersionResponse
    import json
    from json import JSONDecodeError

    # 处理 content 字段：如果是字符串则解析为 dict
    content = version.content
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except JSONDecodeError:
            content = {"raw": content}  # 解析失败时保留原始内容

    return MemoryVersionResponse(
        version_id=version.version_id,
        memory_id=version.memory_id,
        version_number=version.version_number,
        title=version.title,
        category=version.category,
        tags=version.tags or [],
        summary=version.summary,
        content=content,
        format_type=version.format_type,
        price=version.price,
        changelog=version.changelog,
        created_at=version.created_at
    ).model_dump()


async def _execute_search(
    stmt,
    db: AsyncSession,
    page: int,
    page_size: int,
    sort_by: str
) -> MemoryList:
    """执行搜索查询（通用逻辑）"""
    # 计数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.execute(count_stmt)
    total = total.scalar() or 0

    # 排序逻辑
    if sort_by == "created_at":
        stmt = stmt.order_by(desc(Memory.created_at))
    elif sort_by == "purchase_count":
        stmt = stmt.order_by(desc(Memory.purchase_count))
    elif sort_by == "price":
        stmt = stmt.order_by(Memory.price)
    elif sort_by == "rating":
        stmt = stmt.order_by(desc(Memory.avg_score))
    else:
        # 综合评分排序（默认）
        score_normalized = (Memory.avg_score / 5.0)
        purchase_normalized = func.log10(Memory.purchase_count + 1) / func.log10(100)
        verification_normalized = func.coalesce(Memory.verification_score, 0.5)
        # 计算天数差（PostgreSQL兼容）
        days_old = func.extract('epoch', func.now() - Memory.created_at) / 86400
        time_decay = case(
            (days_old <= 7, 1.0),
            (days_old <= 30, 1.0 - (days_old - 7) / 23 * 0.5),
            else_=0.5
        )
        favorite_normalized = func.log10(Memory.favorite_count + 1) / func.log10(50)

        composite_score = (
            score_normalized * 0.3 +
            purchase_normalized * 0.2 +
            verification_normalized * 0.25 +
            time_decay * 0.15 +
            favorite_normalized * 0.1
        )

        stmt = stmt.order_by(desc(composite_score))

    # 分页
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        memory, seller_name, seller_reputation = row
        items.append(memory_to_response(memory, seller_name, seller_reputation))

    return MemoryList(items=items, total=total, page=page, page_size=page_size)


def _vectorize_memory_async(memory: Memory):
    """异步向量化记忆（非阻塞）

    Args:
        memory: 记忆对象
    """
    import threading

    def vectorize():
        try:
            from app.search.qdrant_engine import get_qdrant_engine
            engine = get_qdrant_engine()

            memory_data = {
                "id": memory.memory_id,
                "title": memory.title,
                "summary": memory.summary,
                "category": memory.category,
                "tags": memory.tags or [],
                "price": memory.price,
                "purchase_count": memory.purchase_count,
                "avg_score": memory.avg_score or 0,
                "created_at": memory.created_at.isoformat() if memory.created_at else "",
            }

            engine.index_memories([memory_data], batch_size=10)
            print(f"[VectorSearch] Indexed memory: {memory.memory_id}")
        except Exception as e:
            print(f"[VectorSearch] Failed to index memory {memory.memory_id}: {e}")

    # 在后台线程中执行，避免阻塞
    thread = threading.Thread(target=vectorize, daemon=True)
    thread.start()


# ============ 团队记忆功能 ============

async def _check_team_permission(
    db: AsyncSession,
    team_id: str,
    agent_id: str,
    min_role: str = "member"
) -> Tuple[TeamMember, Team]:
    """检查团队成员权限

    Args:
        db: 数据库会话
        team_id: 团队ID
        agent_id: Agent ID
        min_role: 最低角色要求（member/admin/owner）

    Returns:
        (成员对象, 团队对象)

    Raises:
        PermissionError: 无权限
        ValueError: 团队不存在
    """
    # 获取团队成员
    result = await db.execute(
        select(TeamMember).where(
            and_(
                TeamMember.team_id == team_id,
                TeamMember.agent_id == agent_id,
                TeamMember.is_active == True
            )
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise PermissionError("不是团队成员")

    # 检查角色
    role_hierarchy = {"member": 0, "admin": 1, "owner": 2}
    if role_hierarchy.get(member.role, 0) < role_hierarchy.get(min_role, 0):
        raise PermissionError(f"需要 {min_role} 或更高权限")

    # 获取团队
    team_result = await db.execute(
        select(Team).where(Team.team_id == team_id, Team.is_active == True)
    )
    team = team_result.scalar_one_or_none()

    if not team:
        raise ValueError("团队不存在")

    return member, team


async def create_team_memory(
    db: AsyncSession,
    team_id: str,
    creator_agent_id: str,
    req: TeamMemoryCreate
) -> TeamMemoryResponse:
    """创建团队共享记忆

    Args:
        db: 数据库会话
        team_id: 团队ID
        creator_agent_id: 创建者Agent ID
        req: 记忆创建请求

    Returns:
        团队记忆响应

    Raises:
        PermissionError: 无权限
        ValueError: 团队不存在
    """
    # 检查团队成员权限
    await _check_team_permission(db, team_id, creator_agent_id, "member")

    # 获取创建者
    creator_result = await db.execute(
        select(Agent).where(Agent.agent_id == creator_agent_id)
    )
    creator = creator_result.scalar_one_or_none()
    if not creator:
        raise ValueError("创建者不存在")

    # 创建记忆
    memory = Memory(
        memory_id=gen_id("mem"),
        seller_agent_id=creator_agent_id,  # 记录卖方（用于兼容个人记忆）
        team_id=team_id,
        team_access_level=req.team_access_level,
        created_by_agent_id=creator_agent_id,
        title=req.title,
        category=req.category,
        tags=req.tags,
        summary=req.summary,
        content=req.content,
        format_type=req.format_type,
        price=req.price,
        verification_data=req.verification_data
    )

    # 计算验证分数
    if req.verification_data:
        memory.verification_score = _calc_verification_score(req.verification_data)

    # 设置过期时间
    if req.expires_days:
        from datetime import datetime, timedelta
        memory.expires_at = datetime.now() + timedelta(days=req.expires_days)

    db.add(memory)

    # 更新团队记忆统计
    await db.execute(
        update(Team)
        .where(Team.team_id == team_id)
        .values(memory_count=Team.memory_count + 1)
    )

    # 更新创建者统计
    creator.memories_uploaded += 1

    await db.commit()
    await db.refresh(memory)

    # 创建初始版本快照
    await create_memory_version(db, memory, changelog="初始版本")
    await db.commit()

    # 增量向量化（异步）
    _vectorize_memory_async(memory)

    # 记录团队活动
    await _log_team_activity(
        db,
        team_id,
        creator_agent_id,
        "memory_created",
        f"创建了记忆: {memory.title}",
        related_id=memory.memory_id
    )

    # 构建响应
    team = await db.execute(select(Team).where(Team.team_id == team_id))
    team = team.scalar_one_or_none()

    return TeamMemoryResponse(
        memory_id=memory.memory_id,
        team_id=memory.team_id,
        team_name=team.name if team else None,
        created_by_agent_id=memory.created_by_agent_id,
        created_by_name=creator.name,
        title=memory.title,
        category=memory.category,
        tags=memory.tags or [],
        summary=memory.summary,
        format_type=memory.format_type,
        price=memory.price,
        purchase_count=memory.purchase_count,
        favorite_count=memory.favorite_count,
        avg_score=memory.avg_score,
        verification_score=memory.verification_score,
        team_access_level=memory.team_access_level,
        created_at=memory.created_at,
        updated_at=memory.updated_at
    )


async def get_team_memories(
    db: AsyncSession,
    team_id: str,
    request_agent_id: str,
    page: int = 1,
    page_size: int = 20
) -> TeamMemoryList:
    """获取团队记忆列表

    Args:
        db: 数据库会话
        team_id: 团队ID
        request_agent_id: 请求者Agent ID
        page: 页码
        page_size: 每页数量

    Returns:
        团队记忆列表

    Raises:
        PermissionError: 无权限
    """
    # 检查团队成员权限
    await _check_team_permission(db, team_id, request_agent_id, "member")

    # 计算总数
    count_stmt = select(func.count()).select_from(Memory).where(
        and_(Memory.team_id == team_id, Memory.is_active == True)
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 获取记忆列表
    stmt = (
        select(Memory, Agent, Team)
        .join(Agent, Memory.created_by_agent_id == Agent.agent_id)
        .outerjoin(Team, Memory.team_id == Team.team_id)
        .where(
            and_(Memory.team_id == team_id, Memory.is_active == True)
        )
        .order_by(desc(Memory.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    items = []

    for row in result:
        memory = row[0]
        creator = row[1]
        team = row[2]

        items.append(TeamMemoryResponse(
            memory_id=memory.memory_id,
            team_id=memory.team_id,
            team_name=team.name if team else None,
            created_by_agent_id=memory.created_by_agent_id,
            created_by_name=creator.name if creator else "",
            title=memory.title,
            category=memory.category,
            tags=memory.tags or [],
            summary=memory.summary,
            format_type=memory.format_type,
            price=memory.price,
            purchase_count=memory.purchase_count,
            favorite_count=memory.favorite_count,
            avg_score=memory.avg_score,
            verification_score=memory.verification_score,
            team_access_level=memory.team_access_level,
            created_at=memory.created_at,
            updated_at=memory.updated_at
        ))

    return TeamMemoryList(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


async def get_team_memory_detail(
    db: AsyncSession,
    team_id: str,
    memory_id: str,
    request_agent_id: str
) -> TeamMemoryDetail:
    """获取团队记忆详情

    Args:
        db: 数据库会话
        team_id: 团队ID
        memory_id: 记忆ID
        request_agent_id: 请求者Agent ID

    Returns:
        团队记忆详情

    Raises:
        PermissionError: 无权限
        ValueError: 记忆不存在
    """
    # 检查团队成员权限
    await _check_team_permission(db, team_id, request_agent_id, "member")

    # 获取记忆
    result = await db.execute(
        select(Memory, Agent, Team)
        .join(Agent, Memory.created_by_agent_id == Agent.agent_id)
        .outerjoin(Team, Memory.team_id == Team.team_id)
        .where(
            and_(
                Memory.memory_id == memory_id,
                Memory.team_id == team_id,
                Memory.is_active == True
            )
        )
    )
    row = result.first()

    if not row:
        raise ValueError("记忆不存在")

    memory, creator, team = row

    # 处理 content 字段
    content = memory.content
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except JSONDecodeError:
            content = {"raw": content}

    # 处理 verification_data 字段
    verification_data = memory.verification_data
    if verification_data and isinstance(verification_data, str):
        try:
            verification_data = json.loads(verification_data)
        except JSONDecodeError:
            verification_data = {"raw": verification_data}

    return TeamMemoryDetail(
        memory_id=memory.memory_id,
        team_id=memory.team_id,
        team_name=team.name if team else None,
        created_by_agent_id=memory.created_by_agent_id,
        created_by_name=creator.name if creator else "",
        title=memory.title,
        category=memory.category,
        tags=memory.tags or [],
        summary=memory.summary,
        format_type=memory.format_type,
        price=memory.price,
        purchase_count=memory.purchase_count,
        favorite_count=memory.favorite_count,
        avg_score=memory.avg_score,
        verification_score=memory.verification_score,
        team_access_level=memory.team_access_level,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
        content=content,
        verification_data=verification_data
    )


async def update_team_memory(
    db: AsyncSession,
    team_id: str,
    memory_id: str,
    request_agent_id: str,
    req: TeamMemoryUpdate
) -> TeamMemoryResponse:
    """更新团队记忆

    Args:
        db: 数据库会话
        team_id: 团队ID
        memory_id: 记忆ID
        request_agent_id: 请求者Agent ID
        req: 更新请求

    Returns:
        更新后的团队记忆

    Raises:
        PermissionError: 无权限
        ValueError: 记忆不存在
    """
    # 检查团队成员权限（admin及以上可以修改）
    member, _ = await _check_team_permission(db, team_id, request_agent_id, "admin")

    # 获取记忆
    result = await db.execute(
        select(Memory).where(
            and_(
                Memory.memory_id == memory_id,
                Memory.team_id == team_id,
                Memory.is_active == True
            )
        )
    )
    memory = result.scalar_one_or_none()

    if not memory:
        raise ValueError("记忆不存在")

    # 提取 changelog
    changelog = req.changelog

    # 更新字段
    if req.summary is not None:
        memory.summary = req.summary
    if req.content is not None:
        memory.content = req.content
    if req.tags is not None:
        memory.tags = req.tags

    # 更新时间戳
    from datetime import datetime
    memory.updated_at = datetime.now()

    await db.commit()
    await db.refresh(memory)

    # 创建版本快照
    await create_memory_version(db, memory, changelog=changelog)
    await db.commit()

    # 增量向量化更新
    _vectorize_memory_async(memory)

    # 记录团队活动
    await _log_team_activity(
        db,
        team_id,
        request_agent_id,
        "memory_updated",
        f"更新了记忆: {memory.title}",
        related_id=memory.memory_id
    )

    # 构建响应
    creator_result = await db.execute(
        select(Agent).where(Agent.agent_id == memory.created_by_agent_id)
    )
    creator = creator_result.scalar_one_or_none()
    team_result = await db.execute(select(Team).where(Team.team_id == team_id))
    team = team_result.scalar_one_or_none()

    return TeamMemoryResponse(
        memory_id=memory.memory_id,
        team_id=memory.team_id,
        team_name=team.name if team else None,
        created_by_agent_id=memory.created_by_agent_id,
        created_by_name=creator.name if creator else "",
        title=memory.title,
        category=memory.category,
        tags=memory.tags or [],
        summary=memory.summary,
        format_type=memory.format_type,
        price=memory.price,
        purchase_count=memory.purchase_count,
        favorite_count=memory.favorite_count,
        avg_score=memory.avg_score,
        verification_score=memory.verification_score,
        team_access_level=memory.team_access_level,
        created_at=memory.created_at,
        updated_at=memory.updated_at
    )


async def delete_team_memory(
    db: AsyncSession,
    team_id: str,
    memory_id: str,
    request_agent_id: str
) -> None:
    """删除团队记忆

    Args:
        db: 数据库会话
        team_id: 团队ID
        memory_id: 记忆ID
        request_agent_id: 请求者Agent ID

    Raises:
        PermissionError: 无权限
        ValueError: 记忆不存在
    """
    # 检查团队成员权限（admin及以上可以删除）
    member, _ = await _check_team_permission(db, team_id, request_agent_id, "admin")

    # 获取记忆
    result = await db.execute(
        select(Memory).where(
            and_(
                Memory.memory_id == memory_id,
                Memory.team_id == team_id,
                Memory.is_active == True
            )
        )
    )
    memory = result.scalar_one_or_none()

    if not memory:
        raise ValueError("记忆不存在")

    # 软删除
    memory.is_active = False
    await db.commit()

    # 更新团队记忆统计
    await db.execute(
        update(Team)
        .where(Team.team_id == team_id)
        .values(memory_count=Team.memory_count - 1)
    )
    await db.commit()

    # 记录团队活动
    await _log_team_activity(
        db,
        team_id,
        request_agent_id,
        "memory_deleted",
        f"删除了记忆: {memory.title}",
        related_id=memory.memory_id
    )


async def _log_team_activity(
    db: AsyncSession,
    team_id: str,
    agent_id: str,
    activity_type: str,
    description: str,
    related_id: Optional[str] = None,
    extra_data: Optional[dict] = None
) -> None:
    """记录团队活动（内部函数）

    Args:
        db: 数据库会话
        team_id: 团队ID
        agent_id: 操作者Agent ID
        activity_type: 活动类型
        description: 活动描述
        related_id: 关联ID
        extra_data: 额外信息
    """
    # 创建活动记录（如果活动日志表存在）
    try:
        from app.models.tables import TeamActivityLog

        activity = TeamActivityLog(
            activity_id=gen_id("act"),
            team_id=team_id,
            agent_id=agent_id,
            activity_type=activity_type,
            description=description,
            related_id=related_id,
            extra_data=extra_data
        )
        db.add(activity)
        await db.commit()
    except ImportError:
        # 表不存在，跳过
        pass
    except Exception:
        # 其他错误，跳过
        pass
