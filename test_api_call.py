#!/usr/bin/env python
"""直接测试搜索 API 调用"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.tables import Memory, Agent
from app.db.database import Base
from app.services.memory_service import search_memories

async def test_api_call():
    """直接测试 search_memories 函数"""
    print("=" * 60)
    print("直接测试 search_memories 函数")
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
        
        for i in range(5):
            memory = Memory(
                memory_id=f"test_mem_{i:03d}",
                seller_agent_id="test_agent_001",
                title=f"Test Memory {i} about Python",
                category="Programming/Python",
                summary=f"This is test memory {i} about Python programming",
                content={"tip": f"Test tip {i}", "code": f"print('Hello {i}')"},
                price=10 * (i + 1),
                is_active=True,
                avg_score=4.0 + i * 0.2,
                purchase_count=i * 3
            )
            db.add(memory)
        
        await db.commit()
        print("   ✓ 测试数据插入成功")
        
        # 测试 1: 不带关键词的搜索
        print("\n2. 测试不带关键词的搜索 (query='')...")
        try:
            result = await search_memories(
                db,
                query="",
                page=1,
                page_size=10,
                sort_by="relevance",
                search_type="hybrid"
            )
            print(f"   ✓ 成功！找到 {result.total} 条结果")
            for item in result.items[:3]:
                print(f"      - {item.title}")
        except Exception as e:
            print(f"   ✗ 失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 测试 2: 带关键词的搜索
        print("\n3. 测试带关键词的搜索 (query='Python')...")
        try:
            result = await search_memories(
                db,
                query="Python",
                page=1,
                page_size=10,
                sort_by="relevance",
                search_type="hybrid"
            )
            print(f"   ✓ 成功！找到 {result.total} 条结果")
            for item in result.items[:3]:
                print(f"      - {item.title}")
        except Exception as e:
            print(f"   ✗ 失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 测试 3: 关键词搜索类型
        print("\n4. 测试关键词搜索类型 (search_type='keyword')...")
        try:
            result = await search_memories(
                db,
                query="Python",
                page=1,
                page_size=10,
                sort_by="relevance",
                search_type="keyword"
            )
            print(f"   ✓ 成功！找到 {result.total} 条结果")
            for item in result.items[:3]:
                print(f"      - {item.title}")
        except Exception as e:
            print(f"   ✗ 失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 测试 4: 向量搜索类型
        print("\n5. 测试向量搜索类型 (search_type='vector')...")
        try:
            result = await search_memories(
                db,
                query="Python",
                page=1,
                page_size=10,
                sort_by="relevance",
                search_type="vector"
            )
            print(f"   ✓ 成功！找到 {result.total} 条结果")
            for item in result.items[:3]:
                print(f"      - {item.title}")
        except Exception as e:
            print(f"   ✗ 失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_api_call())
