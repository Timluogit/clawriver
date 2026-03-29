"""团队记忆协作 MCP 工具

提供 MCP 协议的工具接口，用于团队记忆的查询、创建、购买等操作
"""
from typing import Optional, List, Dict, Any
import json
from datetime import datetime


class TeamMemoryTools:
    """团队记忆工具集"""

    def __init__(self, db_session_factory):
        """初始化工具

        Args:
            db_session_factory: 数据库会话工厂函数
        """
        self.get_db = db_session_factory

    async def search_team_memories(
        self,
        team_id: str,
        query: str = "",
        category: str = "",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """搜索团队记忆

        Args:
            team_id: 团队ID
            query: 搜索关键词
            category: 分类筛选
            page: 页码
            page_size: 每页数量

        Returns:
            记忆列表
        """
        from app.services.memory_service import get_team_memories

        db = self.get_db()
        try:
            result = await get_team_memories(
                db=db,
                team_id=team_id,
                request_agent_id="system",  # MCP 工具使用 system 权限
                page=page,
                page_size=page_size
            )

            # 应用筛选
            items = result.items
            if query:
                items = [m for m in items if query.lower() in m.title.lower() or query.lower() in m.summary.lower()]
            if category:
                items = [m for m in items if category in m.category]

            return {
                "items": [m.model_dump() for m in items],
                "total": len(items),
                "page": page,
                "page_size": page_size
            }
        finally:
            await db.close()

    async def create_team_memory(
        self,
        team_id: str,
        creator_agent_id: str,
        title: str,
        category: str,
        summary: str,
        content: Dict[str, Any],
        tags: List[str] = [],
        format_type: str = "template",
        price: int = 0,
        team_access_level: str = "team_only",
        verification_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建团队记忆

        Args:
            team_id: 团队ID
            creator_agent_id: 创建者Agent ID
            title: 标题
            category: 分类
            summary: 摘要
            content: 内容（JSON）
            tags: 标签列表
            format_type: 格式类型
            price: 价格
            team_access_level: 可见性
            verification_data: 验证数据

        Returns:
            创建的记忆信息
        """
        from app.models.schemas import TeamMemoryCreate
        from app.services.memory_service import create_team_memory

        db = self.get_db()
        try:
            req = TeamMemoryCreate(
                title=title,
                category=category,
                tags=tags,
                content=content,
                summary=summary,
                format_type=format_type,
                price=price,
                team_access_level=team_access_level,
                verification_data=verification_data
            )

            memory = await create_team_memory(db, team_id, creator_agent_id, req)
            return memory.model_dump()
        except Exception as e:
            return {"error": str(e)}
        finally:
            await db.close()

    async def purchase_memory_with_team_credits(
        self,
        team_id: str,
        request_agent_id: str,
        memory_id: str
    ) -> Dict[str, Any]:
        """使用团队积分购买记忆

        Args:
            team_id: 团队ID
            request_agent_id: 请求者Agent ID
            memory_id: 记忆ID

        Returns:
            购买结果
        """
        from app.services.purchase_service_v2 import purchase_with_team_credits

        db = self.get_db()
        try:
            result = await purchase_with_team_credits(
                db=db,
                team_id=team_id,
                request_agent_id=request_agent_id,
                memory_id=memory_id
            )
            return result.model_dump()
        except Exception as e:
            return {"error": str(e)}
        finally:
            await db.close()

    async def get_team_credits(
        self,
        team_id: str
    ) -> Dict[str, Any]:
        """查询团队积分

        Args:
            team_id: 团队ID

        Returns:
            团队积分信息
        """
        from app.services.team_service import CreditService

        db = self.get_db()
        try:
            info = await CreditService.get_credits_info(db, team_id)
            return info
        except Exception as e:
            return {"error": str(e)}
        finally:
            await db.close()

    async def get_team_stats(
        self,
        team_id: str
    ) -> Dict[str, Any]:
        """获取团队统计信息

        Args:
            team_id: 团队ID

        Returns:
            团队统计信息
        """
        from app.api.team_stats import get_team_stats as api_get_team_stats
        from app.models.tables import Agent

        db = self.get_db()
        try:
            # 创建一个临时的 system agent
            system_agent = Agent(
                agent_id="system",
                name="System",
                description="System Agent",
                api_key="system",
                credits=0,
                reputation_score=5.0,
                total_sales=0,
                total_purchases=0,
                memories_uploaded=0,
                is_active=True
            )

            stats = await api_get_team_stats(
                team_id=team_id,
                current_agent=system_agent,
                db=db
            )
            return stats.model_dump()
        except Exception as e:
            return {"error": str(e)}
        finally:
            await db.close()

    async def get_team_activity_logs(
        self,
        team_id: str,
        activity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取团队活动日志

        Args:
            team_id: 团队ID
            activity_type: 活动类型过滤
            page: 页码
            page_size: 每页数量

        Returns:
            活动日志列表
        """
        from app.api.team_activity import get_team_activity_logs
        from app.models.tables import Agent

        db = self.get_db()
        try:
            # 创建一个临时的 system agent
            system_agent = Agent(
                agent_id="system",
                name="System",
                description="System Agent",
                api_key="system",
                credits=0,
                reputation_score=5.0,
                total_sales=0,
                total_purchases=0,
                memories_uploaded=0,
                is_active=True
            )

            logs = await get_team_activity_logs(
                team_id=team_id,
                activity_type=activity_type,
                page=page,
                page_size=page_size,
                current_agent=system_agent,
                db=db
            )
            return logs.model_dump()
        except Exception as e:
            return {"error": str(e)}
        finally:
            await db.close()


# 工具注册函数
def register_team_tools(mcp_server, db_session_factory):
    """注册团队记忆工具到 MCP 服务器

    Args:
        mcp_server: MCP 服务器实例
        db_session_factory: 数据库会话工厂函数
    """
    tools = TeamMemoryTools(db_session_factory)

    # 注册工具
    mcp_server.add_tool({
        "name": "search_team_memories",
        "description": "搜索团队记忆",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "团队ID"},
                "query": {"type": "string", "description": "搜索关键词"},
                "category": {"type": "string", "description": "分类筛选"},
                "page": {"type": "integer", "description": "页码", "default": 1},
                "page_size": {"type": "integer", "description": "每页数量", "default": 20}
            },
            "required": ["team_id"]
        },
        "handler": tools.search_team_memories
    })

    mcp_server.add_tool({
        "name": "create_team_memory",
        "description": "创建团队记忆",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "团队ID"},
                "creator_agent_id": {"type": "string", "description": "创建者Agent ID"},
                "title": {"type": "string", "description": "标题"},
                "category": {"type": "string", "description": "分类"},
                "summary": {"type": "string", "description": "摘要"},
                "content": {"type": "object", "description": "内容（JSON）"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "标签列表"},
                "format_type": {"type": "string", "description": "格式类型", "default": "template"},
                "price": {"type": "integer", "description": "价格", "default": 0},
                "team_access_level": {"type": "string", "description": "可见性", "default": "team_only"},
                "verification_data": {"type": "object", "description": "验证数据"}
            },
            "required": ["team_id", "creator_agent_id", "title", "category", "summary", "content"]
        },
        "handler": tools.create_team_memory
    })

    mcp_server.add_tool({
        "name": "purchase_memory_with_team_credits",
        "description": "使用团队积分购买记忆",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "团队ID"},
                "request_agent_id": {"type": "string", "description": "请求者Agent ID"},
                "memory_id": {"type": "string", "description": "记忆ID"}
            },
            "required": ["team_id", "request_agent_id", "memory_id"]
        },
        "handler": tools.purchase_memory_with_team_credits
    })

    mcp_server.add_tool({
        "name": "get_team_credits",
        "description": "查询团队积分",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "团队ID"}
            },
            "required": ["team_id"]
        },
        "handler": tools.get_team_credits
    })

    mcp_server.add_tool({
        "name": "get_team_stats",
        "description": "获取团队统计信息",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "团队ID"}
            },
            "required": ["team_id"]
        },
        "handler": tools.get_team_stats
    })

    mcp_server.add_tool({
        "name": "get_team_activity_logs",
        "description": "获取团队活动日志",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "团队ID"},
                "activity_type": {"type": "string", "description": "活动类型过滤"},
                "page": {"type": "integer", "description": "页码", "default": 1},
                "page_size": {"type": "integer", "description": "每页数量", "default": 20}
            },
            "required": ["team_id"]
        },
        "handler": tools.get_team_activity_logs
    })
