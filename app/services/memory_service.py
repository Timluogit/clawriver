"""记忆服务"""
import json
import re
from typing import Optional, List, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_, or_, desc, case, literal_column
from app.models.tables import Agent, Memory, Purchase, Rating, Transaction, Verification, PlatformStats, MemoryVersion
from app.models.schemas import (
    MemoryCreate, MemoryUpdate, MemoryResponse, MemoryDetail,
    MemoryList, PurchaseResponse, RateRequest, RateResponse,
    VerificationRequest, VerificationResponse
)
from app.core.config import settings
from app.search.vector_search import get_search_engine
import uuid
from datetime import datetime
from math import log10

def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def calc_executability_score(content: dict, summary: str = "") -> dict:
    """计算知识的Agent可执行度（0-100）"""
    score = 0
    reasons = []
    full_text = json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else str(content)
    full_text += " " + (summary or "")

    # 1. 变量模板检测
    variables = re.findall(r'\{[a-zA-Z_\u4e00-\u9fff][a-zA-Z0-9_\u4e00-\u9fff]{0,29}\}', full_text)
    if variables:
        score += min(len(variables) * 15, 45)
        reasons.append(f"包含{len(variables)}个可填充变量")
    else:
        reasons.append("无可填充变量模板")

    # 2. 条件逻辑
    logic = re.findall(r'(if|when|否则|如果|条件|判断|case|switch|elif|else)', full_text, re.IGNORECASE)
    if logic:
        score += min(len(logic) * 8, 20)
        reasons.append(f"包含{len(logic)}处条件逻辑")

    # 3. 结构化程度
    if isinstance(content, dict):
        field_count = len(content)
        max_depth = 0
        def get_depth(d, depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            if isinstance(d, dict):
                for v in d.values(): get_depth(v, depth + 1)
            elif isinstance(d, list):
                for item in d: get_depth(item, depth + 1)
        get_depth(content)
        if field_count >= 3:
            score += 10
            reasons.append(f"结构化内容({field_count}个字段)")
        if max_depth >= 2:
            score += 5
            reasons.append(f"多层嵌套({max_depth}层)")

    # 4. 可执行代码/API
    exec_p = re.findall(r'(curl|POST|GET|PUT|DELETE|api|endpoint|sdk|pip install|npm install|import|from|def |function|class )', full_text, re.IGNORECASE)
    if exec_p:
        score += min(len(exec_p) * 5, 15)
        reasons.append(f"包含可执行代码/API({len(exec_p)}处)")

    # 5. 步骤/流程
    steps = re.findall(r'(步骤|step|第[一二三四五六七八九十\d]步|阶段|流程|→|=>|->|then)', full_text, re.IGNORECASE)
    if steps:
        score += min(len(steps) * 3, 10)
        reasons.append(f"包含操作步骤({len(steps)}步)")

    # 6. 内容长度
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
    level = "excellent" if score >= 70 else "usable" if score >= 40 else "partial" if score >= 20 else "useless"
    return {"score": score, "reasons": reasons, "level": level}

def get_agent_level(total_transactions: int, avg_score: float = 0) -> str:
    """计算Agent等级
    - 新手(newbie): <10次交易
    - 铜牌(bronze): 10-50次交易
    - 银牌(silver): 50-100次交易
    - 金牌(gold): >100次交易
    """
    if total_transactions >= 100:
        return "gold"
    elif total_transactions >= 50:
        return "silver"
    elif total_transactions >= 10:
        return "bronze"
    return "newbie"

def memory_to_response(memory: Memory, seller_name: str = "", seller_reputation: float = 5.0, seller_total_sales: int = 0) -> MemoryResponse:
    """转换为响应格式（Agent视角：展示结构而非文字）"""
    # 生成内容预览：展示结构和变量
    content_preview = None
    if memory.content:
        try:
            content = memory.content if isinstance(memory.content, dict) else json.loads(memory.content)
            if isinstance(content, dict):
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
    if exec_result["score"] < 15:
        raise ValueError(
            f"知识可执行度过低({exec_result['score']}/100)。"
            f"Agent视角：{'; '.join(exec_result['reasons'])}。"
            f"请添加可填充的变量模板{{变量名}}、结构化JSON内容或可执行的步骤。"
        )

    memory = Memory(
        memory_id=gen_id("mem"),
        seller_agent_id=seller_id,
        title=req.title,
        category=req.category,
        tags=req.tags,
        summary=req.summary,
        content=req.content,
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

    return memory_to_response(memory, seller.name, seller.reputation_score)

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
    search_type: Literal["keyword", "semantic", "hybrid"] = "hybrid"
) -> MemoryList:
    """搜索记忆

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
        search_type: 搜索类型 (keyword=关键词, semantic=语义, hybrid=混合，默认hybrid)

    Returns:
        记忆列表
    """
    # 基础查询（不含关键词过滤）
    base_stmt = select(Memory, Agent.name, Agent.reputation_score).join(
        Agent, Memory.seller_agent_id == Agent.agent_id
    ).where(Memory.is_active == True)

    # 应用筛选条件（非文本搜索）
    if category:
        base_stmt = base_stmt.where(Memory.category.contains(category))
    if platform:
        base_stmt = base_stmt.where(Memory.category.startswith(platform))
    if format_type:
        base_stmt = base_stmt.where(Memory.format_type == format_type)
    if min_score > 0:
        base_stmt = base_stmt.where(Memory.avg_score >= min_score)
    if max_price < 999999:
        base_stmt = base_stmt.where(Memory.price <= max_price)

    # 根据搜索类型选择策略
    if search_type == "semantic":
        # 纯语义搜索
        return await _semantic_search(
            db, query, base_stmt, page, page_size, sort_by
        )
    elif search_type == "keyword":
        # 纯关键词搜索（原有逻辑）
        return await _keyword_search(
            db, query, base_stmt, page, page_size, sort_by
        )
    else:
        # 混合搜索（默认）
        return await _hybrid_search(
            db, query, base_stmt, page, page_size, sort_by
        )


async def _keyword_search(
    db: AsyncSession,
    query: str,
    base_stmt,
    page: int,
    page_size: int,
    sort_by: str
) -> MemoryList:
    """关键词搜索"""
    stmt = base_stmt

    # 关键词过滤
    if query:
        stmt = stmt.where(
            or_(
                Memory.title.ilike(f"%{query}%"),
                Memory.summary.ilike(f"%{query}%")
            )
        )

    # 使用通用搜索执行逻辑
    return await _execute_search(stmt, db, page, page_size, sort_by)


async def get_memory_detail(db: AsyncSession, memory_id: str, buyer_id: str = None) -> MemoryDetail:
    """获取记忆详情"""
    result = await db.execute(
        select(Memory, Agent.name, Agent.reputation_score).join(
            Agent, Memory.seller_agent_id == Agent.agent_id
        ).where(Memory.memory_id == memory_id)
    )
    row = result.first()
    if not row:
        return None

    memory, seller_name, seller_reputation = row

    # 检查是否已购买（免费记忆除外）
    if buyer_id and memory.price > 0:
        purchase = await db.execute(
            select(Purchase).where(
                and_(Purchase.buyer_agent_id == buyer_id, Purchase.memory_id == memory_id)
            )
        )
        if not purchase.scalar_one_or_none():
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
    # 获取记忆
    result = await db.execute(select(Memory).where(Memory.memory_id == memory_id))
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
    
    # 获取买家
    buyer = await db.execute(select(Agent).where(Agent.agent_id == buyer_id))
    buyer = buyer.scalar_one_or_none()
    if not buyer:
        return PurchaseResponse(success=False, message="买家不存在", memory_id=memory_id, credits_spent=0, remaining_credits=0)
    
    # MVP免费模式：跳过余额检查
    price = memory.price
    if settings.MVP_FREE_MODE:
        price = 0  # 免费！
    elif buyer.credits < price:
        return PurchaseResponse(success=False, message="积分不足", memory_id=memory_id, credits_spent=price, remaining_credits=buyer.credits)

    # 计算分配（5%平台佣金，95%给卖家）
    COMMISSION_RATE = 0.05
    platform_fee = int(price * COMMISSION_RATE) if price > 0 else 0
    seller_income = price - platform_fee

    # 扣买家积分
    buyer.credits -= price
    buyer.total_spent += price
    buyer.total_purchases += 1

    # 加卖家积分（扣除佣金后）
    seller = await db.execute(select(Agent).where(Agent.agent_id == memory.seller_agent_id))
    seller = seller.scalar_one_or_none()
    seller.credits += seller_income
    seller.total_earned += seller_income
    seller.total_sales += 1

    # 更新记忆统计
    memory.purchase_count += 1

    # 创建购买记录（含平台佣金）
    purchase = Purchase(
        purchase_id=gen_id("pur"),
        buyer_agent_id=buyer_id,
        seller_agent_id=memory.seller_agent_id,
        memory_id=memory_id,
        amount=price,
        seller_income=seller_income,
        platform_fee=platform_fee
    )
    db.add(purchase)

    # 创建交易流水
    tx_buyer = Transaction(
        agent_id=buyer_id,
        tx_type="purchase",
        amount=-price,
        balance_after=buyer.credits,
        related_id=memory_id,
        description=f"购买记忆: {memory.title}",
        commission=0
    )
    tx_seller = Transaction(
        agent_id=memory.seller_agent_id,
        tx_type="sale",
        amount=seller_income,
        balance_after=seller.credits,
        related_id=memory_id,
        description=f"销售记忆: {memory.title}",
        commission=platform_fee
    )
    db.add(tx_buyer)
    db.add(tx_seller)

    # 更新平台统计
    await _update_platform_stats(db, price, platform_fee)

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
        message="购买成功",
        memory_id=memory_id,
        credits_spent=price,
        remaining_credits=buyer.credits,
        memory_content=memory_content
    )

async def rate_memory(db: AsyncSession, buyer_id: str, req: RateRequest) -> RateResponse:
    """评价记忆（支持更新已有评价）"""
    # 检查是否购买过
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

        memory = await db.execute(select(Memory).where(Memory.memory_id == req.memory_id))
        memory = memory.scalar_one_or_none()
        memory.total_score = memory.total_score - old_score + req.score
        memory.avg_score = memory.total_score / memory.score_count if memory.score_count > 0 else req.score

        seller_id = memory.seller_agent_id
        await db.commit()

        # 更新卖家信用分
        try:
            from app.services.agent_service import update_agent_reputation
            await update_agent_reputation(db, seller_id)
        except Exception:
            pass

        return RateResponse(success=True, message="评价已更新", new_avg_score=memory.avg_score)

    # 创建评价
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

    # 更新卖家的信用分
    seller_id = memory.seller_agent_id
    await db.commit()

    # 异步更新卖家信用分
    try:
        from app.services.agent_service import update_agent_reputation
        await update_agent_reputation(db, seller_id)
    except Exception:
        pass  # 信用分更新失败不影响评价

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


async def _semantic_search(
    db: AsyncSession,
    query: str,
    base_stmt,
    page: int,
    page_size: int,
    sort_by: str
) -> MemoryList:
    """语义搜索"""
    if not query:
        # 无查询时返回所有结果
        return await _execute_search(base_stmt, db, page, page_size, sort_by)

    # 获取所有候选记忆
    result = await db.execute(base_stmt)
    all_memories = result.all()

    if not all_memories:
        return MemoryList(items=[], total=0, page=page, page_size=page_size)

    # 准备语义搜索数据
    memories_data = [
        {
            'id': row.Memory.memory_id,
            'title': row.Memory.title,
            'summary': row.Memory.summary
        }
        for row in all_memories
    ]

    # 索引记忆
    engine = get_search_engine()
    engine.batch_index_with_cache(memories_data)

    # 语义搜索
    search_results = engine.search(query, top_k=page_size * page)

    # 按 ID 映射回记忆对象
    memory_map = {row.Memory.memory_id: row for row in all_memories}
    sorted_memories = []
    for memory_id, score in search_results:
        if memory_id in memory_map:
            sorted_memories.append((memory_id, score, memory_map[memory_id]))

    # 分页
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_memories = sorted_memories[start_idx:end_idx]

    # 转换为响应格式
    items = []
    for memory_id, score, row in paged_memories:
        memory, seller_name, seller_reputation = row
        items.append(memory_to_response(memory, seller_name, seller_reputation))

    return MemoryList(
        items=items,
        total=len(sorted_memories),
        page=page,
        page_size=page_size
    )


async def _hybrid_search(
    db: AsyncSession,
    query: str,
    base_stmt,
    page: int,
    page_size: int,
    sort_by: str
) -> MemoryList:
    """混合搜索：语义 + 关键词"""
    if not query:
        # 无查询时返回所有结果
        return await _execute_search(base_stmt, db, page, page_size, sort_by)

    # 1. 获取关键词匹配结果
    keyword_stmt = base_stmt
    if query:
        keyword_stmt = keyword_stmt.where(
            or_(
                Memory.title.ilike(f"%{query}%"),
                Memory.summary.ilike(f"%{query}%")
            )
        )

    keyword_result = await db.execute(keyword_stmt)
    keyword_memories = keyword_result.all()
    keyword_ids = {row.Memory.memory_id for row in keyword_memories}

    # 2. 获取所有候选记忆用于语义搜索
    all_result = await db.execute(base_stmt)
    all_memories = all_result.all()

    if not all_memories:
        return MemoryList(items=[], total=0, page=page, page_size=page_size)

    # 3. 准备语义搜索数据
    memories_data = [
        {
            'id': row.Memory.memory_id,
            'title': row.Memory.title,
            'summary': row.Memory.summary
        }
        for row in all_memories
    ]

    # 4. 索引记忆
    engine = get_search_engine()
    engine.batch_index_with_cache(memories_data)

    # 5. 混合搜索
    search_results = engine.search_with_keywords(
        query,
        keyword_ids,
        top_k=page_size * page,
        semantic_weight=0.6  # 语义权重 60%，关键词 40%
    )

    # 6. 按 ID 映射回记忆对象
    memory_map = {row.Memory.memory_id: row for row in all_memories}
    sorted_memories = []
    for memory_id, score in search_results:
        if memory_id in memory_map:
            sorted_memories.append((memory_id, score, memory_map[memory_id]))

    # 7. 分页
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_memories = sorted_memories[start_idx:end_idx]

    # 8. 转换为响应格式
    items = []
    for memory_id, score, row in paged_memories:
        memory, seller_name, seller_reputation = row
        items.append(memory_to_response(memory, seller_name, seller_reputation))

    return MemoryList(
        items=items,
        total=len(sorted_memories),
        page=page,
        page_size=page_size
    )


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

