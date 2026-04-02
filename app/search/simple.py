"""极简搜索引擎 - FTS5 + 评分加权"""
from sqlalchemy import text, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from app.models.core import Memory


class SimpleSearchEngine:
    """极简搜索引擎 — FTS5 + 评分加权"""
    
    def __init__(self):
        self.fts_initialized = False
    
    async def ensure_fts_table(self, db: AsyncSession):
        """确保 FTS5 虚拟表存在"""
        if self.fts_initialized:
            return
        
        # 检查 FTS 表是否存在
        result = await db.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories_fts'"
        ))
        table_exists = result.scalar_one_or_none()
        
        if not table_exists:
            # 创建 FTS5 虚拟表
            await db.execute(text("""
                CREATE VIRTUAL TABLE memories_fts USING fts5(
                    memory_id,
                    title,
                    summary,
                    tags,
                    category,
                    content=memories,
                    content_rowid=memory_id
                )
            """))
            
            # 填充初始数据
            await db.execute(text("""
                INSERT INTO memories_fts (rowid, memory_id, title, summary, tags, category)
                SELECT oid, memory_id, title, summary, 
                       COALESCE(json_extract(tags, '$[*]'), ''), category
                FROM memories
            """))
            
            # 创建触发器自动更新 FTS 表
            await db.execute(text("""
                CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, memory_id, title, summary, tags, category)
                    VALUES (new.oid, new.memory_id, new.title, new.summary,
                           COALESCE(json_extract(new.tags, '$[*]'), ''), new.category);
                END;
            """))
            
            await db.execute(text("""
                CREATE TRIGGER memories_ad AFTER DELETE ON memories BEGIN
                    DELETE FROM memories_fts WHERE rowid = old.oid;
                END;
            """))
            
            await db.execute(text("""
                CREATE TRIGGER memories_au AFTER UPDATE ON memories BEGIN
                    UPDATE memories_fts
                    SET memory_id = new.memory_id,
                        title = new.title,
                        summary = new.summary,
                        tags = COALESCE(json_extract(new.tags, '$[*]'), ''),
                        category = new.category
                    WHERE rowid = new.oid;
                END;
            """))
            
            await db.commit()
        
        self.fts_initialized = True
    
    async def search(
        self, 
        db: AsyncSession, 
        query: str, 
        limit: int = 10,
        category: Optional[str] = None,
        min_score: Optional[float] = None
    ) -> List[Memory]:
        """搜索记忆
        
        Args:
            db: 数据库会话
            query: 搜索关键词
            limit: 返回结果数量
            category: 分类过滤
            min_score: 最低评分过滤
            
        Returns:
            记忆列表，按综合评分排序
        """
        await self.ensure_fts_table(db)
        
        if not query or query.strip() == "":
            # 无关键词时返回最新记忆
            stmt = select(Memory).where(Memory.is_active == True)
            if category:
                stmt = stmt.where(Memory.category == category)
            if min_score:
                stmt = stmt.where(Memory.avg_score >= min_score)
            stmt = stmt.order_by(Memory.created_at.desc()).limit(limit)
            
            result = await db.execute(stmt)
            return list(result.scalars().all())
        
        # 1. FTS5 全文搜索
        fts_query = self._prepare_fts_query(query)
        fts_results = await self._fts_search(db, fts_query, limit * 3)
        
        if not fts_results:
            # FTS 无结果，回退到简单关键词匹配
            return await self._keyword_fallback_search(db, query, limit, category, min_score)
        
        # 2. 获取完整记忆数据
        memory_ids = [r[0] for r in fts_results]
        stmt = select(Memory).where(Memory.memory_id.in_(memory_ids))
        if category:
            stmt = stmt.where(Memory.category == category)
        if min_score:
            stmt = stmt.where(Memory.avg_score >= min_score)
        
        result = await db.execute(stmt)
        memories = {m.memory_id: m for m in result.scalars().all()}
        
        # 3. 评分加权排序
        scored = []
        now = datetime.utcnow()
        
        for memory_id, fts_rank in fts_results:
            if memory_id not in memories:
                continue
            
            memory = memories[memory_id]
            
            # 计算综合评分
            score = self._calculate_score(
                fts_rank=fts_rank,
                avg_rating=memory.avg_score,
                purchase_count=memory.purchase_count,
                recency_days=(now - memory.created_at).days if memory.created_at else 365,
                is_low_quality=memory.low_quality
            )
            
            scored.append((score, memory))
        
        # 4. 返回 Top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]
    
    def _prepare_fts_query(self, query: str) -> str:
        """准备 FTS 查询"""
        # 简单处理：转义特殊字符，添加 OR 连接
        terms = query.strip().split()
        if not terms:
            return ""
        
        # 对于多词查询，使用 OR 连接
        if len(terms) > 1:
            return " OR ".join([f'"{term}"' for term in terms])
        return f'"{terms[0]}"'
    
    async def _fts_search(
        self, 
        db: AsyncSession, 
        query: str, 
        limit: int
    ) -> List[Tuple[str, float]]:
        """执行 FTS 搜索"""
        try:
            result = await db.execute(text("""
                SELECT memory_id, rank
                FROM memories_fts
                WHERE memories_fts MATCH :query
                ORDER BY rank
                LIMIT :limit
            """), {"query": query, "limit": limit})
            
            rows = result.fetchall()
            # 将 rank 转换为 relevance score（越低越好 → 越高越好）
            max_rank = max((r[1] for r in rows), default=1.0) if rows else 1.0
            return [(r[0], max(1.0 - (r[1] / max_rank), 0.1)) for r in rows]
        except Exception as e:
            print(f"FTS search failed: {e}")
            return []
    
    async def _keyword_fallback_search(
        self,
        db: AsyncSession,
        query: str,
        limit: int,
        category: Optional[str],
        min_score: Optional[float]
    ) -> List[Memory]:
        """简单关键词回退搜索"""
        terms = [f"%{term}%" for term in query.strip().split()]
        
        stmt = select(Memory).where(Memory.is_active == True)
        
        if category:
            stmt = stmt.where(Memory.category == category)
        if min_score:
            stmt = stmt.where(Memory.avg_score >= min_score)
        
        # 关键词匹配
        or_conditions = []
        for term in terms:
            or_conditions.extend([
                Memory.title.ilike(term),
                Memory.summary.ilike(term),
                Memory.category.ilike(term)
            ])
        
        stmt = stmt.where(or_(*or_conditions))
        stmt = stmt.order_by(Memory.created_at.desc()).limit(limit)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    def _calculate_score(
        self,
        fts_rank: float,
        avg_rating: float,
        purchase_count: int,
        recency_days: int,
        is_low_quality: bool = False
    ) -> float:
        """综合评分：搜索相关性 * 质量 * 时效
        
        Args:
            fts_rank: FTS 相关性得分 (0-1)
            avg_rating: 平均评分 (0-5)
            purchase_count: 汲取次数
            recency_days: 发布天数
            is_low_quality: 是否低质量
            
        Returns:
            综合评分
        """
        if is_low_quality:
            # 低质量内容降权
            fts_rank = fts_rank * 0.1
        
        relevance = max(fts_rank, 0.01)
        quality = (avg_rating / 5.0) if avg_rating > 0 else 0.5
        popularity = min(purchase_count / 50.0, 1.0)
        freshness = 1.0 / (1.0 + recency_days / 30.0)  # 30 天半衰期
        
        return (
            relevance * 0.40 +  # 搜索相关性最重要
            quality * 0.25 +    # 质量次之
            popularity * 0.20 +  # 热度
            freshness * 0.15     # 时效
        )


# 全局搜索引擎实例
search_engine = SimpleSearchEngine()
