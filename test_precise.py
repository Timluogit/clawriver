#!/usr/bin/env python
"""精准测试：定位 Boolean value of this clause is not defined 错误"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.tables import Memory, Agent
from app.db.database import Base

async def test_precise():
    """精准定位问题"""
    print("=" * 60)
    print("精准定位 Boolean value of this clause is not defined 错误")
    print("=" * 60)
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        # 插入测试数据
        print("\n1. 插入测试数据...")
        agent = Agent(
            agent_id="test_agent_001",
            name="Test Agent",
            api_key="test_api_key_001"
        )
        db.add(agent)
        
        for i in range(3):
            memory = Memory(
                memory_id=f"test_mem_{i:03d}",
                seller_agent_id="test_agent_001",
                title=f"Test Memory {i}",
                category="Programming/Python",
                summary=f"This is test memory {i} about Python",
                content={"tip": f"Test tip {i}"},
                price=10 * (i + 1),
                is_active=True
            )
            db.add(memory)
        
        await db.commit()
        print("   ✓ 测试数据插入成功")
        
        # 基础查询
        print("\n2. 创建基础查询...")
        base_stmt = select(Memory, Agent.name, Agent.reputation_score).join(
            Agent, Memory.seller_agent_id == Agent.agent_id
        ).where(Memory.is_active == True)
        
        print("   ✓ 基础查询创建成功")
        
        # 测试 1: 执行查询并查看 row 的结构
        print("\n3. 测试查询结果结构...")
        result = await db.execute(base_stmt)
        all_memories = result.all()
        print(f"   ✓ 查询返回 {len(all_memories)} 条结果")
        
        first_row = all_memories[0]
        print(f"   第一行类型: {type(first_row)}")
        print(f"   第一行内容: {first_row}")
        print(f"   第一行长度: {len(first_row)}")
        
        # 检查如何访问元素
        print("\n4. 测试访问 row 元素的不同方式...")
        
        # 方式 1: 索引访问
        try:
            memory_by_index = first_row[0]
            print(f"   ✓ 通过索引 [0] 访问: {memory_by_index.title}")
        except Exception as e:
            print(f"   ✗ 索引访问失败: {e}")
        
        # 方式 2: 属性访问 (row.Memory)
        try:
            if hasattr(first_row, 'Memory'):
                memory_by_attr = first_row.Memory
                print(f"   ✓ 通过属性 .Memory 访问: {memory_by_attr.title}")
            else:
                print(f"   ✗ row 没有 .Memory 属性")
        except Exception as e:
            print(f"   ✗ 属性访问失败: {e}")
        
        # 测试 2: 模拟 hybrid_search.py 中的 _filter_expired_memories 函数
        print("\n5. 模拟 _filter_expired_memories 函数...")
        
        from datetime import datetime
        now = datetime.now()
        filtered = []
        
        try:
            for row in all_memories:
                print(f"\n   处理 row: {row}")
                
                # 这里是关键！让我们看看哪种方式会导致问题
                print(f"   检查 row 是否有 .Memory 属性: {hasattr(row, 'Memory')}")
                
                # 尝试访问
                if hasattr(row, 'Memory'):
                    memory = row.Memory
                    print(f"   ✓ 使用 row.Memory")
                else:
                    memory = row[0]
                    print(f"   ✓ 使用 row[0]")
                
                print(f"   memory.is_active: {memory.is_active}")
                print(f"   type(memory.is_active): {type(memory.is_active)}")
                
                # 这里是可能出错的地方！
                print(f"   尝试在 if 语句中使用 memory.is_active...")
                if memory.is_active:
                    print(f"   ✓ if memory.is_active 工作正常")
                    filtered.append(row)
                else:
                    print(f"   memory.is_active 是 False")
            
            print(f"\n   ✓ _filter_expired_memories 模拟完成，过滤后 {len(filtered)} 条")
            
        except TypeError as e:
            print(f"\n   ✗ 发现错误: {e}")
            if "Boolean value of this clause is not defined" in str(e):
                print("   ✓ 找到目标错误！！！")
            import traceback
            traceback.print_exc()
        
        # 测试 3: 让我们尝试找出问题的真正根源
        print("\n6. 检查是否存在某些奇怪的布尔值问题...")
        
        # 让我们看看 Memory.is_active 列的定义
        print(f"\n   Memory.is_active 列定义:")
        print(f"      type: {type(Memory.is_active)}")
        print(f"      repr: {repr(Memory.is_active)}")
        
        # 等等！让我们尝试一个更直接的测试
        print("\n7. 关键测试：让我们检查 hybrid_search.py 的 search 方法中的关键部分...")
        
        # 让我们模拟当 query 为空时的情况
        print("\n   模拟 query 为空的情况（调用 _execute_base_search）...")
        
        try:
            # 让我们看看 _execute_base_search 做了什么
            from sqlalchemy import case
            
            print("\n   尝试构建综合评分查询（这可能是问题所在！）...")
            
            # 这是 _execute_search 中的综合评分逻辑
            score_normalized = (Memory.avg_score / 5.0)
            purchase_normalized = func.log10(Memory.purchase_count + 1) / func.log10(100)
            verification_normalized = func.coalesce(Memory.verification_score, 0.5)
            
            # 计算天数差
            days_old = func.extract('epoch', func.now() - Memory.created_at) / 86400
            
            print(f"   days_old 表达式类型: {type(days_old)}")
            
            time_decay = case(
                (days_old <= 7, 1.0),
                (days_old <= 30, 1.0 - (days_old - 7) / 23 * 0.5),
                else_=0.5
            )
            
            print(f"   time_decay 表达式类型: {type(time_decay)}")
            
            favorite_normalized = func.log10(Memory.favorite_count + 1) / func.log10(50)
            
            composite_score = (
                score_normalized * 0.3 +
                purchase_normalized * 0.2 +
                verification_normalized * 0.25 +
                time_decay * 0.15 +
                favorite_normalized * 0.1
            )
            
            print(f"   composite_score 表达式类型: {type(composite_score)}")
            
            # 尝试使用这个表达式
            stmt = base_stmt.order_by(desc(composite_score))
            print(f"   ✓ 成功构建带综合评分的查询")
            
            # 尝试执行这个查询
            print("   尝试执行查询...")
            result = await db.execute(stmt)
            rows = result.all()
            print(f"   ✓ 查询成功执行，返回 {len(rows)} 条结果")
            
        except TypeError as e:
            print(f"\n   ✗ 综合评分查询错误: {e}")
            if "Boolean value of this clause is not defined" in str(e):
                print("   ✓ 找到目标错误！问题在综合评分计算！")
            import traceback
            traceback.print_exc()
        
        # 测试 4: 让我们检查 case 语句
        print("\n8. 单独测试 case 语句...")
        
        try:
            print("   测试简单的 case 语句...")
            
            # 简单的 case
            simple_case = case(
                (Memory.price <= 10, "cheap"),
                (Memory.price <= 20, "medium"),
                else_="expensive"
            )
            
            stmt = select(Memory, simple_case).where(Memory.memory_id == "test_mem_001")
            result = await db.execute(stmt)
            row = result.first()
            print(f"   ✓ 简单 case 工作正常: {row}")
            
            # 现在测试带计算的 case
            print("\n   测试带计算的 case 语句（这可能是问题！）...")
            
            test_days_old = func.extract('epoch', func.now() - Memory.created_at) / 86400
            
            print(f"   test_days_old 类型: {type(test_days_old)}")
            print(f"   test_days_old <= 7 类型: {type(test_days_old <= 7)}")
            
            # 这里是关键！让我们看看这个比较表达式
            comparison_expr = (test_days_old <= 7)
            print(f"   比较表达式: {comparison_expr}")
            print(f"   比较表达式类型: {type(comparison_expr)}")
            
            # 现在尝试在布尔上下文中使用它 - 这会导致错误！
            print("\n   尝试在布尔上下文中使用比较表达式...")
            try:
                # 这会导致 "Boolean value of this clause is not defined" 错误！
                if comparison_expr:
                    print("   这不应该被打印")
            except TypeError as e:
                print(f"   ✓ 找到错误了！: {e}")
                print("   错误原因: 不能在 if 语句中直接使用 SQLAlchemy 比较表达式！")
                
                import traceback
                traceback.print_exc()
            
            # 现在测试包含这种比较的 case 语句
            print("\n   测试包含这种比较的 case 语句...")
            try:
                complex_case = case(
                    (test_days_old <= 7, 1.0),
                    (test_days_old <= 30, 0.75),
                    else_=0.5
                )
                
                stmt = select(Memory, complex_case).where(Memory.memory_id == "test_mem_001")
                result = await db.execute(stmt)
                row = result.first()
                print(f"   ✓ 带比较的 case 在查询中工作正常: {row}")
                
            except Exception as e:
                print(f"   ✗ 带比较的 case 出错: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"   ✗ case 测试出错: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_precise())
