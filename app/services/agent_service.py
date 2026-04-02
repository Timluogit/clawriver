"""Agent服务"""
import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.models.core import Agent, Transaction, Memory, Rating
from app.models.schemas import AgentCreate, AgentResponse, AgentBalance, CreditTransaction, CreditHistoryList
from app.core.config import settings


async def calc_agent_reputation(db: AsyncSession, agent_id: str) -> float:
    """计算Agent的真实信用分（0.0-5.0）

    评估维度（Agent视角）：
    1. 知识质量：上传知识的平均可执行度
    2. 用户评价：知识被评价的平均分数
    3. 实际使用：知识被汲取的次数
    4. 活跃度：作为消费者汲取了多少知识（学习意愿）
    5. 贡献量：上传了多少条知识

    Returns:
        float: 0.0-5.0 的信用分
    """
    score = 2.5  # 基础分

    # 1. 知识质量（可执行度）- 占比最大
    mem_result = await db.execute(
        select(
            func.coalesce(func.avg(Memory.executability_score), 0),
            func.count(Memory.memory_id)
        ).where(
            Memory.seller_agent_id == agent_id,
            Memory.is_active == True
        )
    )
    avg_exec, mem_count = mem_result.fetchone()
    if mem_count > 0:
        # 可执行度 0-100 映射到 -1.0 ~ +1.5
        score += (avg_exec / 100.0) * 1.5 - 0.5

    # 2. 用户评价
    rating_result = await db.execute(
        select(func.coalesce(func.avg(Rating.score), 0)).join(
            Memory, Memory.memory_id == Rating.memory_id
        ).where(Memory.seller_agent_id == agent_id)
    )
    avg_rating = rating_result.scalar()
    if avg_rating > 0:
        # 评分 1-5 映射到 -0.5 ~ +1.0
        score += (avg_rating / 5.0) * 1.0 - 0.5

    # 3. 实际使用（被汲取次数）
    purchase_result = await db.execute(
        select(func.coalesce(func.sum(Memory.purchase_count), 0)).where(
            Memory.seller_agent_id == agent_id,
            Memory.is_active == True
        )
    )
    total_purchases = purchase_result.scalar()
    if total_purchases > 0:
        # 被汲取次数加分（上限+0.5）
        score += min(total_purchases * 0.1, 0.5)

    # 4. 活跃度（作为消费者汲取了多少）
    agent_result = await db.execute(select(Agent.total_purchases).where(Agent.agent_id == agent_id))
    purchases = agent_result.scalar() or 0
    if purchases > 0:
        score += min(purchases * 0.05, 0.3)

    # 5. 贡献量
    if mem_count >= 5:
        score += 0.2
    elif mem_count >= 2:
        score += 0.1

    return round(min(max(score, 0.0), 5.0), 2)


async def update_agent_reputation(db: AsyncSession, agent_id: str):
    """更新Agent的信用分"""
    new_score = await calc_agent_reputation(db, agent_id)
    await db.execute(
        update(Agent).where(Agent.agent_id == agent_id).values(reputation_score=new_score)
    )
    await db.commit()


def get_agent_level(total_transactions: int, avg_score: float = 0) -> str:
    """计算Agent等级（基于交易量和质量）"""
    if total_transactions >= 50 and avg_score >= 4.0:
        return "gold"
    elif total_transactions >= 20 and avg_score >= 3.5:
        return "silver"
    elif total_transactions >= 5:
        return "bronze"
    return "newbie"


async def create_agent(db: AsyncSession, req: AgentCreate) -> AgentResponse:
    """注册新Agent"""
    # 生成API Key
    api_key = f"mk_{secrets.token_hex(24)}"
    
    agent = Agent(
        name=req.name,
        description=req.description,
        api_key=api_key,
        credits=settings.INITIAL_CREDITS
    )
    db.add(agent)
    await db.flush()  # 先flush获取agent_id
    
    # 记录初始积分
    tx = Transaction(
        agent_id=agent.agent_id,
        tx_type="bonus",
        amount=settings.INITIAL_CREDITS,
        balance_after=settings.INITIAL_CREDITS,
        description="注册赠送"
    )
    db.add(tx)
    
    await db.commit()
    await db.refresh(agent)
    
    return AgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        description=agent.description,
        api_key=agent.api_key,  # 注册时返回API Key
        credits=agent.credits,
        reputation_score=agent.reputation_score,
        total_sales=agent.total_sales,
        total_purchases=agent.total_purchases,
        created_at=agent.created_at
    )

async def get_agent(db: AsyncSession, agent_id: str) -> AgentResponse:
    """获取Agent信息"""
    result = await db.execute(select(Agent).where(Agent.agent_id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return None
    
    return AgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        description=agent.description,
        credits=agent.credits,
        reputation_score=agent.reputation_score,
        total_sales=agent.total_sales,
        total_purchases=agent.total_purchases,
        created_at=agent.created_at
    )

async def get_agent_by_api_key(db: AsyncSession, api_key: str) -> Agent:
    """通过API Key获取Agent"""
    result = await db.execute(select(Agent).where(Agent.api_key == api_key))
    return result.scalar_one_or_none()

async def get_balance(db: AsyncSession, agent_id: str) -> AgentBalance:
    """获取账户余额"""
    result = await db.execute(select(Agent).where(Agent.agent_id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return None
    
    return AgentBalance(
        agent_id=agent.agent_id,
        credits=agent.credits,
        total_earned=agent.total_earned,
        total_spent=agent.total_spent
    )

async def update_credits(db: AsyncSession, agent_id: str, amount: int, tx_type: str, 
                         related_id: str = None, description: str = None) -> bool:
    """更新积分（通用方法）"""
    result = await db.execute(select(Agent).where(Agent.agent_id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return False
    
    # 检查余额（扣款时）
    if amount < 0 and agent.credits + amount < 0:
        return False
    
    # 更新余额
    new_balance = agent.credits + amount
    agent.credits = new_balance
    
    if amount > 0:
        agent.total_earned += amount
    else:
        agent.total_spent += abs(amount)
    
    # 记录流水
    tx = Transaction(
        agent_id=agent_id,
        tx_type=tx_type,
        amount=amount,
        balance_after=new_balance,
        related_id=related_id,
        description=description
    )
    db.add(tx)
    
    await db.commit()
    return True

async def get_credit_history(
    db: AsyncSession,
    agent_id: str,
    page: int = 1,
    page_size: int = 20
) -> CreditHistoryList:
    """获取积分流水记录"""
    # 计算总数
    count_stmt = select(func.count()).select_from(Transaction).where(
        Transaction.agent_id == agent_id
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 获取流水记录
    stmt = select(Transaction).where(
        Transaction.agent_id == agent_id
    ).order_by(Transaction.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    transactions = result.scalars().all()

    items = [
        CreditTransaction(
            tx_id=tx.tx_id,
            tx_type=tx.tx_type,
            amount=tx.amount,
            balance_after=tx.balance_after,
            related_id=tx.related_id,
            description=tx.description,
            commission=tx.commission,
            created_at=tx.created_at
        )
        for tx in transactions
    ]

    return CreditHistoryList(items=items, total=total, page=page, page_size=page_size)
