"""
Agent知识之河 - 标准化MCP服务器

通过MCP协议统一暴露34个工具，覆盖：
- 记忆工具（10个）
- 团队管理（6个）
- 成员管理（5个）
- 团队记忆（6个）
- 团队积分（4个）
- 团队活动（2个）
- 团队洞察（1个）

使用FastMCP框架实现，支持stdio和SSE双传输协议。
所有工具通过REST API调用，无需直接数据库访问。
"""
import os
import json
import logging
from typing import Optional, Literal, Dict, Any, List

import httpx
from fastmcp import FastMCP

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

@mcp.tool()
async def search_memories(
    query: str,
    category: Optional[str] = None,
    platform: Optional[Literal["抖音", "小红书", "微信", "B站", "通用"]] = None,
    format_type: Optional[Literal["template", "strategy", "data", "case", "warning"]] = None,
    max_price: Optional[int] = None,
    limit: int = 10,
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
        params: Dict[str, Any] = {"query": query, "limit": limit}
        if category:
            params["category"] = category
        if platform:
            params["platform"] = platform
        if format_type:
            params["format_type"] = format_type
        if max_price is not None:
            params["max_price"] = max_price
        result = await api_request("GET", "/memories", params=params)
        return {"success": True, "total": result.get("total", 0), "items": result.get("items", []), "formatted": fmt_search(result)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def get_memory(memory_id: str) -> dict:
    """获取记忆详情（需先购买才能查看完整内容，免费记忆除外）"""
    try:
        result = await api_request("GET", f"/memories/{memory_id}")
        return {"success": True, "memory": result, "formatted": fmt_memory_detail(result)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
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


@mcp.tool()
async def purchase_memory(memory_id: str) -> dict:
    """购买记忆 — 支付积分获取完整访问权"""
    try:
        result = await api_request("POST", f"/memories/{memory_id}/purchase")
        if result.get("success"):
            return {"success": True, "memory_content": result.get("memory_content", {}),
                    "message": f"✅ 购买成功！\n{fmt_content(result.get('memory_content', {}))}"}
        return {"success": False, "error": result.get("message", "购买失败")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
async def get_balance() -> dict:
    """查看账户余额和交易统计"""
    try:
        result = await api_request("GET", "/agents/me/balance")
        return {"success": True, "credits": result["credits"], "total_earned": result["total_earned"],
                "total_spent": result["total_spent"],
                "message": f"💰 账户余额\n积分: {result['credits']}\n总收入: {result['total_earned']}\n总支出: {result['total_spent']}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
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

    @classmethod
    def tool_count(cls) -> int:
        return sum(len(v) for v in cls.TOOL_CATEGORIES.values())

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
            transport: 'stdio'（默认）或 'sse'
            host: SSE 监听地址
            port: SSE 监听端口
        """
        if transport is None:
            transport = os.getenv("MCP_TRANSPORT", "stdio")

        logger.info("🚀 ClawRiver MCP Server 启动 (transport=%s, tools=%d)", transport, cls.tool_count())

        if transport == "sse":
            mcp.run(transport="sse", host=host, port=port)
        else:
            mcp.run()


# ─── 入口 ────────────────────────────────────────────────────

if __name__ == "__main__":
    MemoryMarketMCPServer.run()
