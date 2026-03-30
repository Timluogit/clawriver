#!/usr/bin/env python
"""测试脚本：重现搜索 API bug"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.tables import Memory, Agent
from app.db.database import Base

async def test_sqlalchemy_issue():
    """测试 SQLAlchemy 查询问题"""
    print("=" * 60)
    print("测试 SQLAlchemy 查询问题")
    print("=" * 60)
    
    # 创建内存数据库进行测试
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        # 插入一些测试数据
        print("\n1. 插入测试数据...")
        agent = Agent(
            agent_id="test_agent_001",
            name="Test Agent",
            api_key="test_api_key_001"
        )
        db.add(agent)
        
        memory1 = Memory(
            memory_id="test_mem_001",
            seller_agent_id="test_agent_001",
            title="Python 编程技巧",
            category="Programming/Python",
            summary="一些有用的 Python 编程技巧",
            content={"tips": ["使用列表推导式", "使用生成器表达式"]},
            price=10,
            is_active=True
        )
        db.add(memory1)
        
        memory2 = Memory(
            memory_id="test_mem_002",
            seller_agent_id="test_agent_001",
            title="FastAPI 开发指南",
            category="Programming/Python",
            summary="FastAPI 框架的使用方法",
            content={"endpoints": ["/docs", "/openapi.json"]},
            price=20,
            is_active=True
        )
        db.add(memory2)
        
        await db.commit()
        print("   ✓ 测试数据插入成功")
        
        # 测试 1: 基础查询
        print("\n2. 测试基础查询...")
        try:
            base_stmt = select(Memory, Agent.name, Agent.reputation_score).join(
                Agent, Memory.seller_agent_id == Agent.agent_id
            ).where(Memory.is_active == True)
            
            result = await db.execute(base_stmt)
            rows = result.all()
            print(f"   ✓ 基础查询成功，返回 {len(rows)} 条结果")
        except Exception as e:
            print(f"   ✗ 基础查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 测试 2: 带关键词的查询
        print("\n3. 测试带关键词的查询...")
        try:
            query = "Python"
            stmt = base_stmt.where(
                or_(
                    Memory.title.ilike(f"%{query}%"),
                    Memory.summary.ilike(f"%{query}%")
                )
            )
            
            result = await db.execute(stmt)
            rows = result.all()
            print(f"   ✓ 关键词查询成功，返回 {len(rows)} 条结果")
        except Exception as e:
            print(f"   ✗ 关键词查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 测试 3: 检查是否有 Boolean value of this clause is not defined 错误
        print("\n4. 检查常见错误模式...")
        
        # 检查 hybrid_search.py 中的 _filter_expired_memories 函数逻辑
        print("\n   检查 _filter_expired_memories 函数...")
        
        # 获取所有记忆
        all_result = await db.execute(base_stmt)
        all_memories = all_result.all()
        
        print(f"   获取到 {len(all_memories)} 条记忆")
        
        # 模拟 hybrid_search.py 中的 _filter_expired_memories 函数
        from datetime import datetime
        now = datetime.now()
        filtered = []
        
        try:
            for row in all_memories:
                # 注意：这里 row 是一个 tuple，不是带属性的对象
                # 让我们检查一下 row 的结构
                print(f"\n   检查 row 结构: {type(row)}")
                print(f"   row 内容: {row}")
                
                # 尝试不同的访问方式
                if hasattr(row, 'Memory'):
                    memory = row.Memory
                    print(f"   ✓ 通过 row.Memory 访问成功")
                else:
                    # 尝试索引访问
                    memory = row[0]
                    print(f"   ✓ 通过 row[0] 访问成功")
                
                # 测试访问 is_active
                print(f"   memory.is_active: {memory.is_active}")
                print(f"   type(memory.is_active): {type(memory.is_active)}")
                
                # 尝试在 if 语句中使用
                if memory.is_active:
                    print(f"   ✓ memory.is_active 在 if 语句中工作正常")
                    filtered.append(row)
            
            print(f"\n   ✓ _filter_expired_memories 逻辑测试通过，过滤后 {len(filtered)} 条")
            
        except TypeError as e:
            print(f"\n   ✗ 发现错误: {e}")
            if "Boolean value of this clause is not defined" in str(e):
                print("   ✓ 找到目标错误！")
            import traceback
            traceback.print_exc()
        
        # 测试 4: 检查 hybrid_search.py 中 search 方法的第一部分
        print("\n5. 检查 hybrid_search.py search 方法...")
        
        try:
            # 模拟 hybrid search 的前几步
            query = "Python"
            
            # 步骤 1: 获取所有候选记忆
            all_result = await db.execute(base_stmt)
            all_memories = all_result.all()
            print(f"   步骤 1: 获取 {len(all_memories)} 条候选记忆")
            
            if all_memories:
                # 步骤 2: 构建记忆映射
                print("   步骤 2: 尝试构建记忆映射...")
                
                # 这里可能有问题！让我们看看 row 的结构
                memory_map = {}
                for row in all_memories:
                    if hasattr(row, 'Memory'):
                        memory_id = row.Memory.memory_id
                    else:
                        memory_id = row[0].memory_id
                    memory_map[memory_id] = row
                
                print(f"   ✓ 记忆映射构建成功，包含 {len(memory_map)} 个条目")
                
        except Exception as e:
            print(f"   ✗ hybrid search 步骤失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_sqlalchemy_issue())
