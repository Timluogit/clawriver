"""直接事实搜索Agent - 搜索直接相关事实

在知识之河中搜索与查询直接匹配的事实性记忆
对应Supermemory ASMR Agent 1：搜索直接事实
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_base import BaseAgent, AgentRole, AgentContext, AgentResult, AgentStatus
from app.models.tables import Memory, Agent

logger = logging.getLogger(__name__)


class DirectFactAgent(BaseAgent):
    """直接事实搜索Agent

    职责：在知识之河中搜索与查询直接匹配的事实性记忆
    策略：关键词精确匹配 + 标题匹配优先
    """

    def __init__(self, db: Optional[AsyncSession] = None, **kwargs):
        kwargs.setdefault("role", AgentRole.SEARCHER_DIRECT)
        super().__init__(**kwargs)
        self.db = db

    async def execute(self, context: AgentContext) -> AgentResult:
        """执行直接事实搜索"""
        query = context.query
        if not query.strip():
            return AgentResult(
                agent_id=self.agent_id,
                role=self.role,
                status=AgentStatus.COMPLETED,
                data={"results": [], "query": query, "strategy": "direct_fact"},
                confidence=0.0,
            )

        results = []

        if self.db:
            results = await self._search_db(query, context)
        else:
            # 无DB时基于已有observations搜索
            results = self._search_from_context(query, context)

        confidence = self._calc_confidence(results)

        return AgentResult(
            agent_id=self.agent_id,
            role=self.role,
            status=AgentStatus.COMPLETED,
            data={
                "results": results,
                "query": query,
                "strategy": "direct_fact",
                "result_count": len(results),
            },
            confidence=confidence,
        )

    async def _search_db(self, query: str, context: AgentContext) -> List[Dict[str, Any]]:
        """数据库直接事实搜索"""
        try:
            # 构建查询
            stmt = (
                select(Memory, Agent.name, Agent.reputation_score)
                .join(Agent, Memory.seller_agent_id == Agent.agent_id)
                .where(
                    Memory.is_active == True,
                    or_(
                        Memory.title.ilike(f"%{query}%"),
                        Memory.summary.ilike(f"%{query}%"),
                    ),
                )
                .order_by(
                    # 标题匹配优先
                    func.coalesce(Memory.verification_score, 0).desc(),
                    Memory.purchase_count.desc(),
                )
                .limit(20)
            )

            result = await self.db.execute(stmt)
            rows = result.all()

            memories = []
            for memory, seller_name, seller_rep in rows:
                # 计算相关性分数
                relevance = self._compute_relevance(query, memory)
                memories.append({
                    "memory_id": memory.memory_id,
                    "title": memory.title,
                    "summary": memory.summary,
                    "category": memory.category,
                    "tags": memory.tags or [],
                    "price": memory.price,
                    "relevance_score": relevance,
                    "seller_name": seller_name,
                    "seller_reputation": seller_rep,
                    "purchase_count": memory.purchase_count,
                    "avg_score": memory.avg_score,
                })

            # 按相关性排序
            memories.sort(key=lambda x: x["relevance_score"], reverse=True)
            return memories[:10]

        except Exception as e:
            logger.error(f"DirectFactAgent DB search error: {e}")
            return []

    def _search_from_context(self, query: str, context: AgentContext) -> List[Dict[str, Any]]:
        """从上下文中搜索（无DB回退）"""
        results = []
        query_lower = query.lower()

        # 搜索observations中的记忆数据
        for key, val in context.observations.items():
            if isinstance(val, dict):
                text = ""
                for field in ("title", "summary", "content", "description"):
                    v = val.get(field)
                    if isinstance(v, str):
                        text += " " + v
                    elif isinstance(v, dict):
                        text += " " + str(v)

                if query_lower in text.lower():
                    results.append({
                        "source": key,
                        "data": val,
                        "relevance_score": self._text_relevance(query_lower, text.lower()),
                    })

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:10]

    def _compute_relevance(self, query: str, memory) -> float:
        """计算记忆与查询的相关性"""
        query_lower = query.lower()
        score = 0.0

        # 标题匹配（高权重）
        title = (memory.title or "").lower()
        if query_lower == title:
            score += 1.0
        elif query_lower in title:
            score += 0.7

        # 摘要匹配
        summary = (memory.summary or "").lower()
        if query_lower in summary:
            score += 0.4

        # 标签匹配
        tags = memory.tags or []
        for tag in tags:
            if query_lower in tag.lower():
                score += 0.3
                break

        # 质量加成
        if memory.verification_score:
            score += memory.verification_score * 0.1
        if memory.avg_score:
            score += (memory.avg_score / 5.0) * 0.1

        return min(score, 2.0)

    def _text_relevance(self, query: str, text: str) -> float:
        """简单文本相关性"""
        score = 0.0
        if query == text.strip():
            score += 1.0
        elif query in text:
            score += 0.6
        # 部分匹配
        words = query.split()
        matched = sum(1 for w in words if w in text)
        if words:
            score += (matched / len(words)) * 0.4
        return score

    def _calc_confidence(self, results: List) -> float:
        """计算搜索置信度"""
        if not results:
            return 0.0
        count = len(results)
        if count >= 5:
            return 0.9
        elif count >= 3:
            return 0.7
        elif count >= 1:
            return 0.5
        return 0.1
