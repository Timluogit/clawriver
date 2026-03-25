"""种子数据导入 - 启动时自动导入基础知识"""
import json
import os
from pathlib import Path

SEED_FILE = Path(__file__).parent / "seed_data.json"

async def seed_database(db):
    """如果数据库为空，自动导入种子数据"""
    from sqlalchemy import select, func
    from app.models.tables import Memory, Agent

    # 检查是否已有数据
    count = await db.execute(select(func.count()).select_from(Memory).where(Memory.is_active == True))
    if count.scalar() > 0:
        print(f"🌱 数据库已有 {count.scalar()} 条知识，跳过种子导入")
        return

    # 检查种子文件
    if not SEED_FILE.exists():
        print("⚠️  种子数据文件不存在，跳过导入")
        return

    with open(SEED_FILE, "r", encoding="utf-8") as f:
        seeds = json.load(f)

    # 创建种子 Agent
    import uuid
    agent_id = f"agent_seed_{uuid.uuid4().hex[:12]}"
    api_key = f"mk_seed_{uuid.uuid4().hex[:32]}"

    agent = Agent(
        agent_id=agent_id,
        name="ClawRiver Seeds",
        description="系统种子数据 - 精选Agent知识",
        api_key=api_key,
        credits=999999,
        is_active=True
    )
    db.add(agent)
    await db.flush()

    # 导入知识
    imported = 0
    for item in seeds:
        memory = Memory(
            memory_id=f"mem_seed_{uuid.uuid4().hex[:12]}",
            seller_agent_id=agent_id,
            title=item["title"],
            category=item["category"],
            summary=item["summary"],
            content=item["content"],
            format_type="template",
            price=item.get("price", 0),
            is_active=True
        )
        # 计算可执行度
        from app.services.memory_service import calc_executability_score
        exec_result = calc_executability_score(item["content"], item["summary"])
        memory.executability_score = exec_result["score"]

        db.add(memory)
        imported += 1

    await db.commit()
    print(f"🌱 种子数据导入完成: {imported} 条知识已上架")
