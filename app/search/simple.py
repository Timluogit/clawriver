"""智能搜索引擎 - 多维度评分 + 搜索重排"""
from sqlalchemy import text, select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
import time

from app.models.core import Memory, SearchLog, Agent


class SearchResult:
    """搜索结果容器，包含记忆和评分细节"""
    def __init__(
        self, 
        memory: Memory, 
        total_score: float, 
        relevance_score: float,
        quality_score: float,
        recency_score: float,
        popularity_score: float
    ):
        self.memory = memory
        self.total_score = total_score
        self.relevance_score = relevance_score
        self.quality_score = quality_score
        self.recency_score = recency_score
        self.popularity_score = popularity_score


class SearchSuggestion:
    """搜索建议"""
    def __init__(self, suggestion_type: str, text: str, query: Optional[str] = None):
        self.suggestion_type = suggestion_type  # "expand", "related", "alternative"
        self.text = text
        self.query = query or text


class SmartSearchEngine:
    """智能搜索引擎 — 多维度评分 + 搜索重排"""
    
    def __init__(self):
        self.fts_initialized = False
        # 评分权重配置
        self.weights = {
            'relevance': 0.40,  # 文本相关性 40%
            'quality': 0.30,    # 质量评分 30%
            'recency': 0.15,    # 时效性 15%
            'popularity': 0.15   # 使用热度 15%
        }
        # 动态调整参数
        self.min_results_target = 5
        self.max_results_target = 20
    
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
            
            # 创建搜索日志表（如果不存在）
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    log_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    agent_id TEXT,
                    result_count INTEGER DEFAULT 0,
                    has_results BOOLEAN DEFAULT 0,
                    category TEXT,
                    execution_time_ms REAL DEFAULT 0.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            await db.commit()
        
        self.fts_initialized = True
    
    async def search(
        self, 
        db: AsyncSession, 
        query: str, 
        limit: int = 10,
        category: Optional[str] = None,
        min_score: Optional[float] = None,
        agent: Optional[Agent] = None
    ) -> Tuple[List[Memory], List[SearchSuggestion]]:
        """搜索记忆，返回结果和搜索建议
        
        Args:
            db: 数据库会话
            query: 搜索关键词
            limit: 返回结果数量
            category: 分类过滤
            min_score: 最低评分过滤
            agent: 可选的 Agent 信息
            
        Returns:
            (记忆列表, 搜索建议列表)
        """
        start_time = time.time()
        await self.ensure_fts_table(db)
        
        if not query or query.strip() == "":
            # 无关键词时返回最新记忆
            memories = await self._get_latest_memories(db, limit, category, min_score)
            suggestions = []
            await self._log_search(db, query, len(memories), category, start_time, agent)
            return memories, suggestions
        
        # 1. FTS5 全文搜索
        fts_query = self._prepare_fts_query(query)
        fts_results = await self._fts_search(db, fts_query, limit * 3)
        
        if not fts_results:
            # FTS 无结果，回退到简单关键词匹配
            memories = await self._keyword_fallback_search(db, query, limit, category, min_score)
            suggestions = self._generate_suggestions(query, [], category)
            await self._log_search(db, query, len(memories), category, start_time, agent)
            return memories, suggestions
        
        # 2. 获取完整记忆数据
        memory_ids = [r[0] for r in fts_results]
        stmt = select(Memory).where(Memory.memory_id.in_(memory_ids))
        if category:
            stmt = stmt.where(Memory.category == category)
        if min_score:
            stmt = stmt.where(Memory.avg_score >= min_score)
        
        result = await db.execute(stmt)
        memories = {m.memory_id: m for m in result.scalars().all()}
        
        # 3. 多维度评分
        search_results = self._score_results(fts_results, memories)
        
        # 4. 动态权重调整
        adjusted_results = self._adjust_weights_dynamically(search_results, category)
        
        # 5. 排序并返回 Top N
        adjusted_results.sort(key=lambda x: x.total_score, reverse=True)
        final_memories = [r.memory for r in adjusted_results[:limit]]
        
        # 6. 生成搜索建议
        suggestions = self._generate_suggestions(query, final_memories, category)
        
        # 7. 记录搜索日志
        await self._log_search(db, query, len(final_memories), category, start_time, agent)
        
        return final_memories, suggestions
    
    def _score_results(
        self, 
        fts_results: List[Tuple[str, float]], 
        memories: Dict[str, Memory]
    ) -> List[SearchResult]:
        """多维度评分"""
        now = datetime.utcnow()
        scored = []
        
        for memory_id, fts_rank in fts_results:
            if memory_id not in memories:
                continue
            
            memory = memories[memory_id]
            
            # 计算各维度得分
            relevance_score = self._calculate_relevance_score(fts_rank)
            quality_score = self._calculate_quality_score(memory)
            recency_score = self._calculate_recency_score(memory, now)
            popularity_score = self._calculate_popularity_score(memory)
            
            # 综合评分
            total_score = (
                relevance_score * self.weights['relevance'] +
                quality_score * self.weights['quality'] +
                recency_score * self.weights['recency'] +
                popularity_score * self.weights['popularity']
            )
            
            scored.append(SearchResult(
                memory=memory,
                total_score=total_score,
                relevance_score=relevance_score,
                quality_score=quality_score,
                recency_score=recency_score,
                popularity_score=popularity_score
            ))
        
        return scored
    
    def _calculate_relevance_score(self, fts_rank: float) -> float:
        """计算文本相关性得分 (0-1)"""
        return max(fts_rank, 0.01)
    
    def _calculate_quality_score(self, memory: Memory) -> float:
        """计算质量评分 (0-1)"""
        if memory.low_quality:
            return 0.1  # 低质量内容大幅降权
        
        if memory.avg_score <= 0:
            return 0.5  # 无评分时给中等分
        
        return min(memory.avg_score / 5.0, 1.0)
    
    def _calculate_recency_score(self, memory: Memory, now: datetime) -> float:
        """计算时效性得分 (0-1) — 30天半衰期"""
        if not memory.created_at:
            return 0.5
        
        recency_days = (now - memory.created_at).days
        return 1.0 / (1.0 + recency_days / 30.0)
    
    def _calculate_popularity_score(self, memory: Memory) -> float:
        """计算使用热度得分 (0-1)"""
        return min(memory.purchase_count / 50.0, 1.0)
    
    def _adjust_weights_dynamically(
        self, 
        results: List[SearchResult], 
        category: Optional[str]
    ) -> List[SearchResult]:
        """动态调整权重"""
        result_count = len(results)
        
        # 复制权重以避免修改原始配置
        adjusted_weights = self.weights.copy()
        
        if result_count < self.min_results_target:
            # 结果太少：降低质量阈值，增加相关性权重
            adjusted_weights['quality'] *= 0.7
            adjusted_weights['relevance'] *= 1.2
        elif result_count > self.max_results_target:
            # 结果太多：提高质量阈值
            adjusted_weights['quality'] *= 1.3
            adjusted_weights['relevance'] *= 0.9
        
        # 重新计算评分
        adjusted_results = []
        for result in results:
            new_total = (
                result.relevance_score * adjusted_weights['relevance'] +
                result.quality_score * adjusted_weights['quality'] +
                result.recency_score * adjusted_weights['recency'] +
                result.popularity_score * adjusted_weights['popularity']
            )
            
            adjusted_results.append(SearchResult(
                memory=result.memory,
                total_score=new_total,
                relevance_score=result.relevance_score,
                quality_score=result.quality_score,
                recency_score=result.recency_score,
                popularity_score=result.popularity_score
            ))
        
        return adjusted_results
    
    def _generate_suggestions(
        self, 
        query: str, 
        results: List[Memory], 
        category: Optional[str]
    ) -> List[SearchSuggestion]:
        """生成搜索建议"""
        suggestions = []
        
        if not results:
            # 无结果时提供扩展搜索建议
            suggestions.append(SearchSuggestion(
                "expand",
                "试试更宽泛的关键词",
                query.split()[0] if len(query.split()) > 1 else query
            ))
            
            # 如果有多个词，建议去掉最后一个词
            terms = query.split()
            if len(terms) > 1:
                suggestions.append(SearchSuggestion(
                    "alternative",
                    f"试试只搜索: {' '.join(terms[:-1])}",
                    ' '.join(terms[:-1])
                ))
        elif len(results) < 3:
            # 结果较少时提供相关分类建议
            if category:
                suggestions.append(SearchSuggestion(
                    "related",
                    f"查看 {category} 分类的更多内容",
                    ""
                ))
        
        return suggestions
    
    async def _log_search(
        self, 
        db: AsyncSession, 
        query: str, 
        result_count: int, 
        category: Optional[str],
        start_time: float,
        agent: Optional[Agent]
    ):
        """记录搜索日志"""
        execution_time_ms = (time.time() - start_time) * 1000
        
        import uuid
        log_id = f"slog_{uuid.uuid4().hex[:12]}"
        
        agent_id = agent.agent_id if agent else None
        
        log = SearchLog(
            log_id=log_id,
            query=query,
            agent_id=agent_id,
            result_count=result_count,
            has_results=result_count > 0,
            category=category,
            execution_time_ms=execution_time_ms
        )
        
        db.add(log)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
    
    async def get_search_analytics(
        self, 
        db: AsyncSession, 
        days: int = 7
    ) -> Dict[str, Any]:
        """获取搜索分析数据"""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # 零结果率
        stmt = select(
            func.count(SearchLog.log_id).label('total'),
            func.sum(func.cast(SearchLog.has_results, Integer)).label('has_results')
        ).where(SearchLog.created_at >= since_date)
        
        result = await db.execute(stmt)
        row = result.first()
        total_searches = row.total or 0
        successful_searches = row.has_results or 0
        zero_result_rate = 1.0 - (successful_searches / total_searches) if total_searches > 0 else 0
        
        # 热门搜索词
        stmt = select(
            SearchLog.query,
            func.count(SearchLog.log_id).label('count')
        ).where(SearchLog.created_at >= since_date
        ).group_by(SearchLog.query
        ).order_by(desc(func.count(SearchLog.log_id))
        ).limit(10)
        
        result = await db.execute(stmt)
        top_queries = [{'query': r.query, 'count': r.count} for r in result]
        
        return {
            'period_days': days,
            'total_searches': total_searches,
            'successful_searches': successful_searches,
            'zero_result_rate': round(zero_result_rate * 100, 2),
            'top_queries': top_queries
        }
    
    def _prepare_fts_query(self, query: str) -> str:
        """准备 FTS 查询"""
        terms = query.strip().split()
        if not terms:
            return ""
        
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
            max_rank = max((r[1] for r in rows), default=1.0) if rows else 1.0
            return [(r[0], max(1.0 - (r[1] / max_rank), 0.1)) for r in rows]
        except Exception as e:
            print(f"FTS search failed: {e}")
            return []
    
    async def _get_latest_memories(
        self,
        db: AsyncSession,
        limit: int,
        category: Optional[str],
        min_score: Optional[float]
    ) -> List[Memory]:
        """获取最新记忆"""
        stmt = select(Memory).where(Memory.is_active == True)
        if category:
            stmt = stmt.where(Memory.category == category)
        if min_score:
            stmt = stmt.where(Memory.avg_score >= min_score)
        stmt = stmt.order_by(Memory.created_at.desc()).limit(limit)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
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


# 全局搜索引擎实例
search_engine = SmartSearchEngine()
