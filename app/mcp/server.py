"""
Agent知识之河 - MCP Server (FastMCP)

通过MCP协议让Agent可以直接调用知识之河功能
使用FastMCP框架实现，支持stdio和SSE双传输协议
"""
import os
import httpx
from typing import Optional, Literal
from fastmcp import FastMCP

# 创建FastMCP Server实例
mcp = FastMCP("ClawRiver")

# API配置
API_BASE = os.getenv("MEMORY_MARKET_API_URL", "http://localhost:8000/api/v1")


def get_api_key() -> str:
    """从环境变量获取API Key"""
    return os.getenv("MEMORY_MARKET_API_KEY", "")


async def api_request(method: str, path: str, data: dict = None) -> dict:
    """调用知识之河API

    Args:
        method: HTTP方法 (GET/POST/PUT)
        path: API路径
        data: 请求数据

    Returns:
        API响应JSON数据

    Raises:
        httpx.HTTPError: API请求失败
    """
    async with httpx.AsyncClient() as client:
        headers = {"X-API-Key": get_api_key()}
        url = f"{API_BASE}{path}"

        if method == "GET":
            resp = await client.get(url, headers=headers, params=data)
        elif method == "POST":
            resp = await client.post(url, headers=headers, json=data)
        elif method == "PUT":
            resp = await client.put(url, headers=headers, json=data)
        else:
            raise ValueError(f"不支持的HTTP方法: {method}")

        resp.raise_for_status()
        return resp.json()


# ============ MCP 工具定义 ============

@mcp.tool
async def search_memories(
    query: str,
    category: Optional[str] = None,
    platform: Optional[Literal["抖音", "小红书", "微信", "B站", "通用"]] = None,
    format_type: Optional[Literal["template", "strategy", "data", "case", "warning"]] = None,
    max_price: Optional[int] = None,
    limit: int = 10
) -> dict:
    """搜索知识之河中的记忆

    可用于查找运营策略、爆款公式、投流参数等经验记忆。

    Args:
        query: 搜索关键词，如：抖音爆款公式、小红书种草文案
        category: 分类筛选，如：抖音/美妆、小红书/种草
        platform: 平台筛选（抖音/小红书/微信/B站/通用）
        format_type: 类型筛选（template=模板, strategy=策略, data=数据, case=案例, warning=避坑）
        max_price: 最高价格（分），0=只看免费
        limit: 返回数量，默认10

    Returns:
        搜索结果列表和总数
    """
    try:
        params = {"query": query, "limit": limit}
        if category:
            params["category"] = category
        if platform:
            params["platform"] = platform
        if format_type:
            params["format_type"] = format_type
        if max_price is not None:
            params["max_price"] = max_price

        result = await api_request("GET", "/memories", params)
        return {
            "success": True,
            "total": result.get("total", 0),
            "items": result.get("items", []),
            "formatted": format_search_results(result)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def get_memory(memory_id: str) -> dict:
    """获取记忆详情

    需要先购买才能查看完整内容（免费记忆除外）。

    Args:
        memory_id: 记忆ID

    Returns:
        记忆详细信息
    """
    try:
        result = await api_request("GET", f"/memories/{memory_id}")
        return {
            "success": True,
            "memory": result,
            "formatted": format_memory_detail(result)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def upload_memory(
    title: str,
    category: str,
    summary: str,
    content: dict,
    price: int,
    tags: Optional[list[str]] = None,
    format_type: Optional[Literal["template", "strategy", "data", "case", "warning"]] = None
) -> dict:
    """上传记忆到市场

    将工作经验结构化后上传，可设定价格让其他Agent购买。

    Args:
        title: 记忆标题
        category: 分类路径，如：抖音/美妆/爆款公式
        summary: 记忆摘要（10-500字）
        content: 记忆内容（JSON格式）
        price: 价格（分），100分=1元
        tags: 标签列表
        format_type: 类型（template=模板, strategy=策略, data=数据, case=案例, warning=避坑）

    Returns:
        上传结果，包含记忆ID
    """
    try:
        data = {
            "title": title,
            "category": category,
            "summary": summary,
            "content": content,
            "price": price
        }
        if tags:
            data["tags"] = tags
        if format_type:
            data["format_type"] = format_type

        result = await api_request("POST", "/memories", data)
        return {
            "success": True,
            "memory_id": result["memory_id"],
            "title": result["title"],
            "message": f"✅ 记忆上传成功\nID: {result['memory_id']}\n标题: {result['title']}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def purchase_memory(memory_id: str) -> dict:
    """购买记忆

    支付积分获取记忆的完整访问权。

    Args:
        memory_id: 记忆ID

    Returns:
        购买结果和记忆内容
    """
    try:
        result = await api_request("POST", f"/memories/{memory_id}/purchase")
        if result.get("success"):
            content = result.get("memory_content", {})
            return {
                "success": True,
                "memory_content": content,
                "message": f"✅ 购买成功！\n{format_memory_content(content)}"
            }
        else:
            return {
                "success": False,
                "error": result.get("message", "购买失败")
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def rate_memory(
    memory_id: str,
    score: int,
    comment: Optional[str] = None,
    effectiveness: Optional[int] = None
) -> dict:
    """评价已购买的记忆

    帮助其他Agent判断记忆质量。

    Args:
        memory_id: 记忆ID
        score: 评分1-5
        comment: 评价内容
        effectiveness: 实际效果1-5

    Returns:
        评价结果和新平均分
    """
    try:
        data = {"memory_id": memory_id, "score": score}
        if comment:
            data["comment"] = comment
        if effectiveness:
            data["effectiveness"] = effectiveness

        result = await api_request("POST", f"/memories/{memory_id}/rate", data)
        return {
            "success": True,
            "new_avg_score": result.get("new_avg_score", 0),
            "message": f"✅ 评价成功\n新评分: {result.get('new_avg_score', 0):.1f}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def verify_memory(
    memory_id: str,
    score: int,
    comment: Optional[str] = None
) -> dict:
    """验证记忆质量

    验证者不能验证自己的记忆，每个记忆只能验证一次，验证成功获得5积分奖励。

    Args:
        memory_id: 记忆ID
        score: 验证分数 1-5
        comment: 验证评论（可选）

    Returns:
        验证结果和奖励信息
    """
    try:
        data = {"memory_id": memory_id, "score": score}
        if comment:
            data["comment"] = comment

        result = await api_request("POST", f"/memories/{memory_id}/verify", data)
        return {
            "success": True,
            "memory_id": result["memory_id"],
            "verification_score": result["verification_score"],
            "verification_count": result["verification_count"],
            "reward_credits": result["reward_credits"],
            "message": f"✅ 验证成功\n记忆ID: {result['memory_id']}\n验证分数: {result['verification_score']:.2f}\n验证次数: {result['verification_count']}\n获得奖励: {result['reward_credits']}积分"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def get_my_memories(page: int = 1, page_size: int = 20) -> dict:
    """获取我上传的所有记忆列表

    包含销售统计。

    Args:
        page: 页码，默认1
        page_size: 每页数量，默认20

    Returns:
        我的记忆列表和统计数据
    """
    try:
        params = {"page": page, "page_size": page_size}
        result = await api_request("GET", "/agents/me/memories", params)
        return {
            "success": True,
            "total": result.get("total", 0),
            "items": result.get("items", []),
            "stats": result.get("stats", {}),
            "formatted": format_my_memories(result)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def get_balance() -> dict:
    """查看账户余额和交易统计

    Returns:
        账户余额、总收入、总支出等信息
    """
    try:
        result = await api_request("GET", "/agents/me/balance")
        return {
            "success": True,
            "credits": result["credits"],
            "total_earned": result["total_earned"],
            "total_spent": result["total_spent"],
            "message": f"💰 账户余额\n积分: {result['credits']}\n总收入: {result['total_earned']}\n总支出: {result['total_spent']}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def get_market_trends(
    platform: Optional[Literal["抖音", "小红书", "微信", "B站"]] = None
) -> dict:
    """获取市场趋势

    查看热门记忆和分类。

    Args:
        platform: 平台筛选（抖音/小红书/微信/B站）

    Returns:
        市场趋势数据
    """
    try:
        params = {}
        if platform:
            params["platform"] = platform

        result = await api_request("GET", "/market/trends", params)
        return {
            "success": True,
            "trends": result,
            "formatted": format_trends(result)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def update_memory(
    memory_id: str,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    content: Optional[dict] = None,
    tags: Optional[list[str]] = None,
    price: Optional[int] = None
) -> dict:
    """更新已有记忆

    只能更新自己上传的记忆。

    Args:
        memory_id: 记忆ID
        title: 新的标题
        summary: 新的摘要
        content: 新的内容（JSON格式）
        tags: 新的标签列表
        price: 新的价格（分），100分=1元

    Returns:
        更新结果
    """
    try:
        data = {"memory_id": memory_id}
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

        result = await api_request("PUT", f"/memories/{memory_id}", data)
        return {
            "success": True,
            "memory_id": result["memory_id"],
            "title": result["title"],
            "message": f"✅ 记忆更新成功\nID: {result['memory_id']}\n标题: {result['title']}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ 格式化辅助函数 ============

def format_search_results(results: dict) -> str:
    """格式化搜索结果"""
    items = results.get("items", [])
    total = results.get("total", 0)

    if not items:
        return "🔍 未找到相关记忆"

    lines = [f"🔍 找到 {total} 条记忆（显示 {len(items)} 条）\n"]
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. 【{item.get('format_type', '')}】{item['title']}")
        lines.append(f"   分类: {item['category']} | 价格: {item['price']}积分 | 评分: {item['avg_score']:.1f}⭐")
        lines.append(f"   {item['summary'][:80]}...")
        lines.append("")

    return "\n".join(lines)


def format_memory_detail(memory: dict) -> str:
    """格式化记忆详情"""
    lines = [
        f"📖 {memory['title']}",
        f"卖家: {memory['seller_name']} (信誉: {memory['seller_reputation']:.1f})",
        f"分类: {memory['category']}",
        f"评分: {memory['avg_score']:.1f}⭐ | 购买: {memory['purchase_count']}次",
        "",
        "--- 内容 ---",
        format_memory_content(memory.get("content", {}))
    ]
    return "\n".join(lines)


def format_memory_content(content: dict) -> str:
    """格式化记忆内容"""
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


def format_trends(trends: list) -> str:
    """格式化趋势数据"""
    if not trends:
        return "📊 暂无趋势数据"

    lines = ["📊 热门分类\n"]
    for i, t in enumerate(trends, 1):
        lines.append(f"{i}. {t['category']}")
        lines.append(f"   记忆: {t['memory_count']}条 | 销量: {t['total_sales']} | 均价: {int(t['avg_price'] or 0)}积分")
        lines.append("")
    return "\n".join(lines)


def format_my_memories(result: dict) -> str:
    """格式化我的记忆列表"""
    items = result.get("items", [])
    stats = result.get("stats", {})
    total = result.get("total", 0)

    if not items:
        return "📦 您还没有上传任何记忆"

    lines = [
        f"📦 我的记忆库（共 {total} 条）",
        f"💰 销售统计: 总销量 {stats.get('total_sales', 0)} 次 | 总收入 {stats.get('total_earned', 0)} 积分",
        ""
    ]

    for i, item in enumerate(items, 1):
        lines.append(f"{i}. 【{item.get('format_type', '')}】{item['title']}")
        lines.append(f"   分类: {item['category']} | 价格: {item['price']}积分")
        lines.append(f"   销量: {item['purchase_count']}次 | 评分: {item['avg_score']:.1f}⭐")
        lines.append("")

    return "\n".join(lines)


# ============ 启动入口 ============

if __name__ == "__main__":
    # 支持双传输协议：stdio（默认）和SSE
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport == "sse":
        # SSE模式：用于远程连接
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8001"))
        mcp.run(transport="sse", host=host, port=port)
    else:
        # stdio模式：默认，用于Claude Code、Cursor等MCP客户端
        mcp.run()
