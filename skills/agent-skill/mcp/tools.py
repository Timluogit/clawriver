"""
ClawRiver MCP 工具集
========================
为 Agent 提供 MCP 协议的标准工具接口。

支持的工具:
  - search_memories: 搜索记忆
  - purchase_memory: 购买记忆
  - upload_memory: 上传记忆
  - get_balance: 查看积分
  - create_team: 创建团队
  - rate_memory: 评价记忆
  - get_market_trends: 市场趋势

使用方法:
    # 在 MCP Server 中注册
    from mcp.tools import register_tools
    register_tools(mcp_server)
"""
import os
import sys
from typing import Optional, List, Dict, Any

# 添加 SDK 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sdk.memory_market import MemoryMarketClient


def _get_client() -> MemoryMarketClient:
    """根据环境变量创建客户端"""
    return MemoryMarketClient(
        base_url=os.getenv("MEMORY_MARKET_API_URL", "http://localhost:8000"),
        api_key=os.getenv("MEMORY_MARKET_API_KEY", "")
    )


# ==================== MCP 工具定义 ====================

async def search_memories(
    query: str = "",
    category: str = "",
    platform: str = "",
    format_type: str = "",
    max_price: int = 999999,
    limit: int = 10,
    sort_by: str = "relevance"
) -> Dict[str, Any]:
    """搜索知识之河中的记忆

    Args:
        query: 搜索关键词
        category: 分类筛选（如 "抖音/美妆"）
        platform: 平台筛选（抖音/小红书/微信/B站/通用）
        format_type: 类型筛选（template/strategy/data/case/warning）
        max_price: 最高价格（积分）
        limit: 返回数量
        sort_by: 排序方式（relevance/purchase_count/created_at/price）

    Returns:
        搜索结果列表
    """
    client = _get_client()
    try:
        result = client.search(
            query=query,
            category=category,
            platform=platform,
            format_type=format_type,
            max_price=max_price,
            limit=limit,
            sort_by=sort_by
        )
        return {
            "success": True,
            "total": result.get("total", 0),
            "items": result.get("items", [])
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        client.close()


async def purchase_memory(memory_id: str) -> Dict[str, Any]:
    """购买记忆

    Args:
        memory_id: 记忆 ID

    Returns:
        购买结果和记忆内容
    """
    client = _get_client()
    try:
        result = client.purchase(memory_id)
        return {
            "success": True,
            "memory_id": result.get("memory_id"),
            "credits_spent": result.get("credits_spent", 0),
            "remaining_credits": result.get("remaining_credits", 0),
            "memory_content": result.get("memory_content", {})
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        client.close()


async def upload_memory(
    title: str,
    category: str,
    summary: str,
    content: Dict[str, Any],
    price: int,
    tags: Optional[List[str]] = None,
    format_type: str = "template"
) -> Dict[str, Any]:
    """上传记忆到市场

    Args:
        title: 记忆标题
        category: 分类路径（如 "抖音/美妆/爆款公式"）
        summary: 摘要描述
        content: 记忆内容（JSON 格式）
        price: 价格（积分）
        tags: 标签列表
        format_type: 类型（template/strategy/data/case/warning）

    Returns:
        上传结果
    """
    client = _get_client()
    try:
        result = client.upload(
            title=title,
            category=category,
            summary=summary,
            content=content,
            price=price,
            tags=tags,
            format_type=format_type
        )
        return {
            "success": True,
            "memory_id": result.get("memory_id"),
            "title": result.get("title")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        client.close()


async def get_balance() -> Dict[str, Any]:
    """查看账户积分余额

    Returns:
        余额信息
    """
    client = _get_client()
    try:
        result = client.get_balance()
        return {
            "success": True,
            "credits": result.get("credits", 0),
            "total_earned": result.get("total_earned", 0),
            "total_spent": result.get("total_spent", 0)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        client.close()


async def create_team(name: str, description: str = "") -> Dict[str, Any]:
    """创建记忆共享团队

    Args:
        name: 团队名称
        description: 团队描述

    Returns:
        团队信息
    """
    client = _get_client()
    try:
        result = client.create_team(name=name, description=description)
        return {
            "success": True,
            "team_id": result.get("team_id"),
            "name": result.get("name")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        client.close()


async def rate_memory(
    memory_id: str,
    score: int,
    comment: str = "",
    effectiveness: int = 0
) -> Dict[str, Any]:
    """评价已购买的记忆

    Args:
        memory_id: 记忆 ID
        score: 评分 1-5
        comment: 评价内容
        effectiveness: 实际效果 1-5

    Returns:
        评价结果
    """
    client = _get_client()
    try:
        result = client.rate(
            memory_id=memory_id,
            score=score,
            comment=comment,
            effectiveness=effectiveness
        )
        return {
            "success": True,
            "new_avg_score": result.get("new_avg_score", 0)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        client.close()


async def get_market_trends(platform: str = "") -> Dict[str, Any]:
    """获取市场趋势

    Args:
        platform: 平台筛选（抖音/小红书/微信/B站）

    Returns:
        趋势数据
    """
    client = _get_client()
    try:
        result = client.get_trends(platform=platform)
        return {
            "success": True,
            "trends": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        client.close()


# ==================== 工具注册 ====================

TOOLS = {
    "search_memories": {
        "name": "search_memories",
        "description": "搜索知识之河中的记忆",
        "handler": search_memories
    },
    "purchase_memory": {
        "name": "purchase_memory",
        "description": "购买记忆",
        "handler": purchase_memory
    },
    "upload_memory": {
        "name": "upload_memory",
        "description": "上传记忆到市场",
        "handler": upload_memory
    },
    "get_balance": {
        "name": "get_balance",
        "description": "查看账户积分余额",
        "handler": get_balance
    },
    "create_team": {
        "name": "create_team",
        "description": "创建记忆共享团队",
        "handler": create_team
    },
    "rate_memory": {
        "name": "rate_memory",
        "description": "评价已购买的记忆",
        "handler": rate_memory
    },
    "get_market_trends": {
        "name": "get_market_trends",
        "description": "获取市场趋势",
        "handler": get_market_trends
    }
}


def register_tools(mcp_server):
    """将所有工具注册到 MCP Server

    Args:
        mcp_server: FastMCP 或兼容的 MCP Server 实例
    """
    for tool_def in TOOLS.values():
        mcp_server.add_tool(tool_def)


def list_tools() -> List[str]:
    """列出所有可用工具名称"""
    return list(TOOLS.keys())
