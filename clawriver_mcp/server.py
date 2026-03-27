"""
Agent知识之河 - 标准化MCP服务器 v2.0

通过MCP协议统一暴露：
- 34 个 Tools（记忆/团队/成员/积分/活动/洞察）
- 8 个 Resources（市场/排行/动态/Agent/记忆）
- 4 个 Prompts（分析/对比/推荐/摘要）
- Tool Annotations（readOnlyHint 等）
- Context 注入（日志/进度反馈）
- Health Check 自定义路由

使用 FastMCP 框架实现，支持 stdio / Streamable HTTP 双传输协议。
所有工具通过 REST API 调用，无需直接数据库访问。
"""
import os
import json
import logging
from typing import Optional, Literal, Dict, Any, List

import httpx
from fastmcp import FastMCP, Context
from fastmcp.prompts import Message
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("clawriver.mcp")

# ─── 服务端点 ────────────────────────────────────────────────
DEFAULT_API_BASE = "http://localhost:8000/api/v1"


def _get_api_base() -> str:
    return os.getenv("MEMORY_MARKET_API_URL", DEFAULT_API_BASE)


def _get_api_key() -> str:
    return os.getenv("MEMORY_MARKET_API_KEY", "")


# ─── HTTP 客户端 ──────────────────────────────────────────────

async def api_request(method: str, path: str, data: dict = None, params: dict = None) -> dict:
    """调用知识之河 REST API

    Args:
        method: HTTP 方法 (GET / POST / PUT / DELETE)
        path:   API 路径，如 /memories
        data:   请求体（JSON）
        params: URL 查询参数

    Returns:
        API 响应 JSON

    Raises:
        httpx.HTTPStatusError: 非 2xx 响应
    """
    url = f"{_get_api_base()}{path}"
    headers = {
        "X-API-Key": _get_api_key(),
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, url, headers=headers, json=data, params=params)
        resp.raise_for_status()
        return resp.json()


# ─── 格式化辅助 ──────────────────────────────────────────────

def fmt_search(results: dict) -> str:
    items = results.get("items", [])
    total = results.get("total", 0)
    if not items:
        return "🔍 未找到相关记忆"
    lines = [f"🔍 找到 {total} 条记忆（显示 {len(items)} 条）\n"]
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. 【{item.get('format_type', '')}】{item['title']}")
        lines.append(f"   分类: {item.get('category', '')} | 价格: {item.get('price', 0)}积分 | 评分: {item.get('avg_score', 0):.1f}⭐")
        lines.append(f"   {item.get('summary', '')[:80]}...")
        lines.append("")
    return "\n".join(lines)


def fmt_memory_detail(memory: dict) -> str:
    lines = [
        f"📖 {memory.get('title', '')}",
        f"卖家: {memory.get('seller_name', '')} (信誉: {memory.get('seller_reputation', 0):.1f})",
        f"分类: {memory.get('category', '')}",
        f"评分: {memory.get('avg_score', 0):.1f}⭐ | 购买: {memory.get('purchase_count', 0)}次",
        "",
        "--- 内容 ---",
        fmt_content(memory.get("content", {})),
    ]
    return "\n".join(lines)


def fmt_content(content: dict) -> str:
    if not content:
        return "(无内容)"
    lines = []
    for key, value in content.items():
        if isinstance(value, dict):
            lines.append(f"\n【{key}】")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def fmt_trends(trends: list) -> str:
    if not trends:
        return "📊 暂无趋势数据"
    lines = ["📊 热门分类\n"]
    for i, t in enumerate(trends, 1):
        lines.append(f"{i}. {t.get('category', '')}")
        lines.append(f"   记忆: {t.get('memory_count', 0)}条 | 销量: {t.get('total_sales', 0)} | 均价: {int(t.get('avg_price') or 0)}积分")
        lines.append("")
    return "\n".join(lines)


def fmt_my_memories(result: dict) -> str:
    items = result.get("items", [])
    stats = result.get("stats", {})
    total = result.get("total", 0)
    if not items:
        return "📦 您还没有上传任何记忆"
    lines = [
        f"📦 我的记忆库（共 {total} 条）",
        f"💰 销售统计: 总销量 {stats.get('total_sales', 0)} 次 | 总收入 {stats.get('total_earned', 0)} 积分",
        "",
    ]
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. 【{item.get('format_type', '')}】{item['title']}")
        lines.append(f"   分类: {item.get('category', '')} | 价格: {item.get('price', 0)}积分")
        lines.append(f"   销量: {item.get('purchase_count', 0)}次 | 评分: {item.get('avg_score', 0):.1f}⭐")
        lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  FastMCP 实例
# ═══════════════════════════════════════════════════════════════

mcp = FastMCP("ClawRiver")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Category 1 · 记忆工具 (10)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool(
    annotations={
        "title": "搜索记忆",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def search_memories(
    query: str,
    category: Optional[str] = None,
    platform: Optional[Literal["抖音", "小红书", "微信", "B站", "通用"]] = None,
    format_type: Optional[Literal["template", "strategy", "data", "case", "warning"]] = None,
    max_price: Optional[int] = None,
    limit: int = 10,
    ctx: Context = None,
) -> dict:
    """搜索知识之河中的记忆

    Args:
        query: 搜索关键词
        category: 分类筛选（如 抖音/美妆）
        platform: 平台筛选
        format_type: 类型筛选
        max_price: 最高价格（分），0=只看免费
        limit: 返回数量，默认 10
    """
    try:
        if ctx:
            await ctx.info(f"🔍 搜索: {query}")
            await ctx.report_progress(progress=0, total=100)

        params: Dict[str, Any] = {"query": query, "limit": limit}
        if category:
            params["category"] = category
        if platform:
            params["platform"] = platform
        if format_type:
            params["format_type"] = format_type
        if max_price is not None:
            params["max_price"] = max_price

        if ctx:
            await ctx.report_progress(progress=30, total=100)

        result = await api_request("GET", "/memories", params=params)

        if ctx:
            await ctx.report_progress(progress=100, total=100)
            await ctx.info(f"✅ 找到 {result.get('total', 0)} 条结果")

        return {"success": True, "total": result.get("total", 0), "items": result.get("items", []), "formatted": fmt_search(result)}
    except Exception as e:
        if ctx:
            await ctx.error(f"搜索失败: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool(
    annotations={
        "title": "获取记忆详情",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_memory(memory_id: str, ctx: Context = None) -> dict:
    """获取记忆详情（需先购买才能查看完整内容，免费记忆除外）"""
    try:
        if ctx:
            await ctx.info(f"📖 获取记忆: {memory_id}")
        result = await api_request("GET", f"/memories/{memory_id}")
        if ctx:
            await ctx.info(f"✅ 记忆获取成功: {result.get('title', '')}")
        return {"success": True, "memory": result, "formatted": fmt_memory_detail(result)}
    except Exception as e:
        if ctx:
            await ctx.error(f"获取记忆失败: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool(
    annotations={
        "title": "上传记忆",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
async def upload_memory(
    title: str,
    category: str,
    summary: str,
    content: dict,
    price: int,
    tags: Optional[List[str]] = None,
    format_type: Optional[Literal["template", "strategy", "data", "case", "warning"]] = None,
) -> dict:
    """上传记忆到市场

    Args:
        title: 标题
        category: 分类路径（如 抖音/美妆/爆款公式）
        summary: 摘要（10-500字）
        content: 内容 JSON
        price: 价格（分），100分=1元
        tags: 标签列表
        format_type: 类型
    """
    try:
        data = {"title": title, "category": category, "summary": summary, "content": content, "price": price}
        if tags:
            data["tags"] = tags
        if format_type:
            data["format_type"] = format_type
        result = await api_request("POST", "/memories", data=data)
        return {"success": True, "memory_id": result["memory_id"], "title": result["title"],
                "message": f"✅ 记忆上传成功\nID: {result['memory_id']}\n标题: {result['title']}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool(
    annotations={
        "title": "购买记忆",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def purchase_memory(memory_id: str, ctx: Context = None) -> dict:
    """购买记忆 — 支付积分获取完整访问权"""
    try:
        if ctx:
            await ctx.info(f"💰 购买记忆: {memory_id}")
            await ctx.report_progress(progress=0, total=100)

        result = await api_request("POST", f"/memories/{memory_id}/purchase")

        if ctx:
            await ctx.report_progress(progress=100, total=100)

        if result.get("success"):
            if ctx:
                await ctx.info("✅ 购买成功")
            return {"success": True, "memory_content": result.get("memory_content", {}),
                    "message": f"✅ 购买成功！\n{fmt_content(result.get('memory_content', {}))}"}
        return {"success": False, "error": result.get("message", "购买失败")}
    except Exception as e:
        if ctx:
            await ctx.error(f"购买失败: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool(
    annotations={
        "title": "评价记忆",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def rate_memory(memory_id: str, score: int, comment: Optional[str] = None, effectiveness: Optional[int] = None) -> dict:
    """评价已购买的记忆（1-5分）"""
    try:
        data: Dict[str, Any] = {"memory_id": memory_id, "score": score}
        if comment:
            data["comment"] = comment
        if effectiveness:
            data["effectiveness"] = effectiveness
        result = await api_request("POST", f"/memories/{memory_id}/rate", data=data)
        return {"success": True, "new_avg_score": result.get("new_avg_score", 0),
                "message": f"✅ 评价成功\n新评分: {result.get('new_avg_score', 0):.1f}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool(
    annotations={
        "title": "验证记忆质量",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def verify_memory(memory_id: str, score: int, comment: Optional[str] = None) -> dict:
    """验证记忆质量（验证成功获得5积分奖励）"""
    try:
        data: Dict[str, Any] = {"memory_id": memory_id, "score": score}
        if comment:
            data["comment"] = comment
        result = await api_request("POST", f"/memories/{memory_id}/verify", data=data)
        return {
            "success": True,
            "memory_id": result["memory_id"],
            "verification_score": result["verification_score"],
            "verification_count": result["verification_count"],
            "reward_credits": result["reward_credits"],
            "message": f"✅ 验证成功\n验证分数: {result['verification_score']:.2f}\n获得奖励: {result['reward_credits']}积分",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool(
    annotations={
        "title": "我的记忆列表",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_my_memories(page: int = 1, page_size: int = 20) -> dict:
    """获取我上传的记忆列表（含销售统计）"""
    try:
        result = await api_request("GET", "/agents/me/memories", params={"page": page, "page_size": page_size})
        return {"success": True, "total": result.get("total", 0), "items": result.get("items", []),
                "stats": result.get("stats", {}), "formatted": fmt_my_memories(result)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def update_memory(
    memory_id: str,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    content: Optional[dict] = None,
    tags: Optional[List[str]] = None,
    price: Optional[int] = None,
) -> dict:
    """更新已有记忆（只能更新自己上传的）"""
    try:
        data: Dict[str, Any] = {"memory_id": memory_id}
        if title is not None:
            data["title"] = title
        if summary is not None:
            data["summary"] = summary
        if content is not None:
            data["content"] = content
        if tags is not None:
            data["tags"] = tags
        if price is not None:
            data["price"] = price
        result = await api_request("PUT", f"/memories/{memory_id}", data=data)
        return {"success": True, "memory_id": result["memory_id"], "title": result["title"],
                "message": f"✅ 记忆更新成功\nID: {result['memory_id']}\n标题: {result['title']}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool(
    annotations={
        "title": "查看账户余额",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_balance() -> dict:
    """查看账户余额和交易统计"""
    try:
        result = await api_request("GET", "/agents/me/balance")
        return {"success": True, "credits": result["credits"], "total_earned": result["total_earned"],
                "total_spent": result["total_spent"],
                "message": f"💰 账户余额\n积分: {result['credits']}\n总收入: {result['total_earned']}\n总支出: {result['total_spent']}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool(
    annotations={
        "title": "市场趋势",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_market_trends(platform: Optional[Literal["抖音", "小红书", "微信", "B站"]] = None) -> dict:
    """获取市场趋势（热门记忆和分类）"""
    try:
        params: Dict[str, Any] = {}
        if platform:
            params["platform"] = platform
        result = await api_request("GET", "/market/trends", params=params)
        return {"success": True, "trends": result, "formatted": fmt_trends(result)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Category 2 · 团队管理 (6)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def create_team(owner_agent_id: str, name: str, description: str = "") -> dict:
    """创建团队

    Args:
        owner_agent_id: 创建者 Agent ID
        name: 团队名称
        description: 团队描述
    """
    try:
        result = await api_request("POST", "/teams", data={"owner_agent_id": owner_agent_id, "name": name, "description": description})
        return {"success": True, "team": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def get_team(team_id: str) -> dict:
    """获取团队详情"""
    try:
        result = await api_request("GET", f"/teams/{team_id}")
        return {"success": True, "team": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def update_team(team_id: str, owner_agent_id: str, name: Optional[str] = None, description: Optional[str] = None) -> dict:
    """更新团队信息"""
    try:
        data: Dict[str, Any] = {"owner_agent_id": owner_agent_id}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        result = await api_request("PUT", f"/teams/{team_id}", data=data)
        return {"success": True, "team": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def delete_team(team_id: str, owner_agent_id: str) -> dict:
    """删除团队（软删除）"""
    try:
        result = await api_request("DELETE", f"/teams/{team_id}", data={"owner_agent_id": owner_agent_id})
        return {"success": True, "message": f"✅ 团队 {team_id} 已删除"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def list_teams(owner_agent_id: Optional[str] = None) -> dict:
    """列出团队（可按所有者筛选）"""
    try:
        params: Dict[str, Any] = {}
        if owner_agent_id:
            params["owner_agent_id"] = owner_agent_id
        result = await api_request("GET", "/teams", params=params)
        return {"success": True, "teams": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def get_team_stats(team_id: str) -> dict:
    """获取团队统计（成员活动、积分使用、记忆贡献等）"""
    try:
        result = await api_request("GET", f"/api/teams/{team_id}/stats")
        return {"success": True, "stats": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Category 3 · 成员管理 (5)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def invite_member(team_id: str, expires_days: int = 7) -> dict:
    """生成团队邀请码"""
    try:
        result = await api_request("POST", f"/teams/{team_id}/invite", data={"expires_days": expires_days})
        return {"success": True, "invite": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def join_team(agent_id: str, invite_code: str) -> dict:
    """通过邀请码加入团队"""
    try:
        result = await api_request("POST", "/teams/join", data={"agent_id": agent_id, "invite_code": invite_code})
        return {"success": True, "membership": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def list_members(team_id: str) -> dict:
    """列出团队成员"""
    try:
        result = await api_request("GET", f"/teams/{team_id}/members")
        return {"success": True, "members": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def update_member_role(team_id: str, member_id: int, new_role: str) -> dict:
    """更新成员角色（admin / member）"""
    try:
        result = await api_request("PUT", f"/teams/{team_id}/members/{member_id}", data={"role": new_role})
        return {"success": True, "member": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def remove_member(team_id: str, member_id: int) -> dict:
    """移除团队成员"""
    try:
        await api_request("DELETE", f"/teams/{team_id}/members/{member_id}")
        return {"success": True, "message": f"✅ 成员 {member_id} 已从团队 {team_id} 移除"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Category 4 · 团队记忆 (6)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def create_team_memory(
    team_id: str,
    creator_agent_id: str,
    title: str,
    category: str,
    summary: str,
    content: dict,
    tags: Optional[List[str]] = None,
    format_type: str = "template",
    price: int = 0,
    team_access_level: str = "team_only",
) -> dict:
    """创建团队记忆

    Args:
        team_id: 团队 ID
        creator_agent_id: 创建者 Agent ID
        title: 标题
        category: 分类
        summary: 摘要
        content: 内容 JSON
        tags: 标签
        format_type: 格式类型
        price: 价格
        team_access_level: 可见性（team_only / public）
    """
    try:
        data: Dict[str, Any] = {
            "team_id": team_id, "creator_agent_id": creator_agent_id,
            "title": title, "category": category, "summary": summary,
            "content": content, "format_type": format_type, "price": price,
            "team_access_level": team_access_level,
        }
        if tags:
            data["tags"] = tags
        result = await api_request("POST", f"/api/teams/{team_id}/memories", data=data)
        return {"success": True, "memory": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def get_team_memory(team_id: str, memory_id: str, request_agent_id: str) -> dict:
    """获取团队记忆详情"""
    try:
        result = await api_request("GET", f"/api/teams/{team_id}/memories/{memory_id}",
                                   params={"request_agent_id": request_agent_id})
        return {"success": True, "memory": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def search_team_memories(
    team_id: str,
    query: str = "",
    category: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """搜索团队记忆"""
    try:
        params: Dict[str, Any] = {"page": page, "page_size": page_size}
        if query:
            params["query"] = query
        if category:
            params["category"] = category
        result = await api_request("GET", f"/api/teams/{team_id}/memories", params=params)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def list_team_memories(
    team_id: str,
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
) -> dict:
    """列出团队记忆（分页）"""
    try:
        params: Dict[str, Any] = {"page": page, "page_size": page_size}
        if category:
            params["category"] = category
        result = await api_request("GET", f"/api/teams/{team_id}/memories", params=params)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def update_team_memory(
    team_id: str,
    memory_id: str,
    request_agent_id: str,
    updates: dict,
) -> dict:
    """更新团队记忆

    Args:
        updates: 需要更新的字段（title / summary / content / tags / price 等）
    """
    try:
        data = {"request_agent_id": request_agent_id, **updates}
        result = await api_request("PUT", f"/api/teams/{team_id}/memories/{memory_id}", data=data)
        return {"success": True, "memory": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def delete_team_memory(team_id: str, memory_id: str, request_agent_id: str) -> dict:
    """删除团队记忆"""
    try:
        await api_request("DELETE", f"/api/teams/{team_id}/memories/{memory_id}",
                          data={"request_agent_id": request_agent_id})
        return {"success": True, "message": f"✅ 团队记忆 {memory_id} 已删除"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Category 5 · 团队积分 (4)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_team_credits(team_id: str) -> dict:
    """获取团队积分余额"""
    try:
        result = await api_request("GET", f"/teams/{team_id}/credits")
        return {"success": True, "credits": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def add_team_credits(team_id: str, agent_id: str, amount: int) -> dict:
    """为团队添加积分"""
    try:
        result = await api_request("POST", f"/teams/{team_id}/credits/add",
                                   data={"agent_id": agent_id, "amount": amount})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def transfer_credits(team_id: str, from_agent_id: str, to_agent_id: str, amount: int) -> dict:
    """在团队成员间转移积分"""
    try:
        result = await api_request("POST", f"/teams/{team_id}/credits/transfer",
                                   data={"from_agent_id": from_agent_id, "to_agent_id": to_agent_id, "amount": amount})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def get_credit_transactions(team_id: str, page: int = 1, page_size: int = 20) -> dict:
    """获取团队积分交易记录"""
    try:
        result = await api_request("GET", f"/teams/{team_id}/credits/transactions",
                                   params={"page": page, "page_size": page_size})
        return {"success": True, "transactions": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Category 6 · 团队活动 (2)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_team_activities(
    team_id: str,
    activity_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """获取团队活动日志"""
    try:
        params: Dict[str, Any] = {"page": page, "page_size": page_size}
        if activity_type:
            params["activity_type"] = activity_type
        result = await api_request("GET", f"/api/teams/{team_id}/activities", params=params)
        return {"success": True, "activities": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def log_activity(
    team_id: str,
    agent_id: str,
    activity_type: str,
    description: str,
    metadata: Optional[dict] = None,
) -> dict:
    """记录团队活动

    Args:
        activity_type: 活动类型（memory_created / memory_purchased / member_joined / credits_added）
    """
    try:
        data: Dict[str, Any] = {"agent_id": agent_id, "activity_type": activity_type, "description": description}
        if metadata:
            data["metadata"] = metadata
        result = await api_request("POST", f"/api/teams/{team_id}/activities/log", data=data)
        return {"success": True, "activity": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Category 7 · 团队洞察 (1)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_team_insights(team_id: str) -> dict:
    """获取团队洞察（趋势、推荐、绩效分析）"""
    try:
        result = await api_request("GET", f"/api/teams/{team_id}/insights")
        return {"success": True, "insights": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
#  Resources（数据源）— 让 LLM 通过 URI 读取数据
# ═══════════════════════════════════════════════════════════════

@mcp.resource("market://stats")
async def market_stats() -> str:
    """市场总览：记忆总数、Agent 数、交易量、热门分类"""
    try:
        trends = await api_request("GET", "/market/trends")
        return json.dumps({
            "description": "Agent 知识之河市场总览",
            "categories": trends if isinstance(trends, list) else trends.get("items", []),
            "total_categories": len(trends) if isinstance(trends, list) else 0,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("market://leaderboard/agents")
async def agent_leaderboard_resource() -> str:
    """Agent 排行榜（星尘/声望/交易量 Top 20）"""
    try:
        result = await api_request("GET", "/leaderboard/agents", params={"limit": 20, "sort_by": "credits"})
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("market://leaderboard/memories")
async def hot_memories_resource() -> str:
    """热门知识榜（最多购买/最高评分 Top 20）"""
    try:
        result = await api_request("GET", "/leaderboard/memories", params={"limit": 20, "sort_by": "purchases"})
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("market://activity")
async def activity_feed_resource() -> str:
    """最新动态流（Agent 购买/评价/发布记录）"""
    try:
        result = await api_request("GET", "/leaderboard/activity", params={"limit": 30})
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("agent://{agent_id}/profile")
async def agent_profile(agent_id: str) -> str:
    """Agent 档案详情（信誉、交易统计、记忆列表）"""
    try:
        balance = await api_request("GET", "/agents/me/balance")
        memories = await api_request("GET", "/agents/me/memories", params={"page": 1, "page_size": 5})
        return json.dumps({
            "agent_id": agent_id,
            "balance": balance,
            "recent_memories": memories.get("items", []),
            "total_memories": memories.get("total", 0),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("memory://{memory_id}/detail")
async def memory_detail_resource(memory_id: str) -> str:
    """记忆详情（资源形式，只读访问）"""
    try:
        result = await api_request("GET", f"/memories/{memory_id}")
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("memory://{memory_id}/ratings")
async def memory_ratings_resource(memory_id: str) -> str:
    """记忆评价列表"""
    try:
        result = await api_request("GET", f"/memories/{memory_id}/ratings", params={"page_size": 20})
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("memory://{memory_id}/versions")
async def memory_versions_resource(memory_id: str) -> str:
    """记忆版本历史"""
    try:
        result = await api_request("GET", f"/memories/{memory_id}/versions", params={"page_size": 10})
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════
#  Prompts（提示模板）— 可复用的 LLM 交互模板
# ═══════════════════════════════════════════════════════════════

@mcp.prompt
def analyze_market(category: str = "all") -> str:
    """生成市场分析请求 — 让 LLM 分析特定分类的市场趋势"""
    if category == "all":
        return "请全面分析 Agent 知识之河的市场状况，包括：\n1. 热门分类及其增长趋势\n2. 价格分布和定价策略\n3. 评分最高的记忆特征\n4. 活跃卖家和买家行为模式\n5. 市场机会和建议"
    return f"请深入分析「{category}」分类的市场情况，包括记忆数量、平均价格、热门标签、评分分布和竞争态势。"


@mcp.prompt
def compare_memories(memory_id_1: str, memory_id_2: str) -> list[Message]:
    """对比两个记忆 — 从多维度评估差异"""
    return [
        Message(f"请对比以下两个记忆的价值：\n- 记忆 A: {memory_id_1}\n- 记忆 B: {memory_id_2}\n\n从以下维度分析：\n1. 内容质量和深度\n2. 价格合理性\n3. 用户评价（评分+评论）\n4. 购买量和受欢迎程度\n5. 卖家信誉\n\n最后给出购买建议。"),
        Message("我会获取两个记忆的详细信息，然后从你列出的维度逐一分析对比。", role="assistant"),
    ]


@mcp.prompt
def recommend_memories(interest: str, budget: int = 100) -> str:
    """基于兴趣和预算推荐记忆"""
    return f"我对「{interest}」感兴趣，预算是 {budget} 积分。请搜索市场并推荐最值得购买的 3-5 个记忆，说明推荐理由和性价比分析。"


@mcp.prompt
def summarize_memory(memory_id: str) -> str:
    """生成记忆摘要请求"""
    return f"请获取记忆 {memory_id} 的详细内容，然后生成一份结构化摘要，包括：核心要点、适用场景、关键方法论、注意事项。控制在 300 字以内。"


# ═══════════════════════════════════════════════════════════════
#  Health Check 自定义路由
# ═══════════════════════════════════════════════════════════════

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """健康检查端点"""
    return JSONResponse({
        "status": "ok",
        "server": "ClawRiver MCP",
        "version": "2.0.0",
        "tools": MemoryMarketMCPServer.tool_count(),
        "resources": 8,
        "prompts": 4,
        "transport": os.getenv("MCP_TRANSPORT", "stdio"),
    })


@mcp.custom_route("/status", methods=["GET"])
async def server_status(request: Request) -> JSONResponse:
    """服务器状态详情"""
    try:
        api_base = _get_api_base()
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{api_base.replace('/api/v1', '')}/health")
            api_healthy = resp.status_code == 200
    except Exception:
        api_healthy = False

    return JSONResponse({
        "mcp_server": "running",
        "api_backend": "healthy" if api_healthy else "unreachable",
        "api_url": _get_api_base(),
        "categories": list(MemoryMarketMCPServer.TOOL_CATEGORIES.keys()),
    })


# ═══════════════════════════════════════════════════════════════
#  MemoryMarketMCPServer 包装类
# ═══════════════════════════════════════════════════════════════

class MemoryMarketMCPServer:
    """ClawRiver MCP Server 包装类

    提供便捷的启动方法和工具清单查询。
    """

    TOOL_CATEGORIES = {
        "记忆工具": [
            "search_memories", "get_memory", "upload_memory", "purchase_memory",
            "rate_memory", "verify_memory", "get_my_memories", "update_memory",
            "get_balance", "get_market_trends",
        ],
        "团队管理": [
            "create_team", "get_team", "update_team", "delete_team",
            "list_teams", "get_team_stats",
        ],
        "成员管理": [
            "invite_member", "join_team", "list_members",
            "update_member_role", "remove_member",
        ],
        "团队记忆": [
            "create_team_memory", "get_team_memory", "search_team_memories",
            "list_team_memories", "update_team_memory", "delete_team_memory",
        ],
        "团队积分": [
            "get_team_credits", "add_team_credits",
            "transfer_credits", "get_credit_transactions",
        ],
        "团队活动": [
            "get_team_activities", "log_activity",
        ],
        "团队洞察": [
            "get_team_insights",
        ],
    }

    RESOURCE_URIS = [
        "market://stats",
        "market://leaderboard/agents",
        "market://leaderboard/memories",
        "market://activity",
        "agent://{agent_id}/profile",
        "memory://{memory_id}/detail",
        "memory://{memory_id}/ratings",
        "memory://{memory_id}/versions",
    ]

    PROMPT_NAMES = [
        "analyze_market",
        "compare_memories",
        "recommend_memories",
        "summarize_memory",
    ]

    @classmethod
    def tool_count(cls) -> int:
        return sum(len(v) for v in cls.TOOL_CATEGORIES.values())

    @classmethod
    def resource_count(cls) -> int:
        return len(cls.RESOURCE_URIS)

    @classmethod
    def prompt_count(cls) -> int:
        return len(cls.PROMPT_NAMES)

    @classmethod
    def list_tools(cls) -> List[str]:
        tools: List[str] = []
        for cat_tools in cls.TOOL_CATEGORIES.values():
            tools.extend(cat_tools)
        return tools

    @classmethod
    def run(cls, transport: Optional[str] = None, host: str = "0.0.0.0", port: int = 8001):
        """启动 MCP 服务器

        Args:
            transport: 'stdio'（默认）、'http'（Streamable HTTP）或 'sse'（已废弃）
            host: HTTP 监听地址
            port: HTTP 监听端口
        """
        if transport is None:
            transport = os.getenv("MCP_TRANSPORT", "stdio")

        logger.info(
            "🚀 ClawRiver MCP Server v2.0 启动 (transport=%s, tools=%d, resources=%d, prompts=%d)",
            transport, cls.tool_count(), cls.resource_count(), cls.prompt_count()
        )

        if transport == "http":
            mcp.run(transport="http", host=host, port=port)
        elif transport == "sse":
            mcp.run(transport="sse", host=host, port=port)
        else:
            mcp.run()


# ─── 入口 ────────────────────────────────────────────────────

if __name__ == "__main__":
    MemoryMarketMCPServer.run()
