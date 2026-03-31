"""
Agent知识之河 - MCP Server (FastMCP)

通过MCP协议让Agent可以直接调用知识之河功能
使用FastMCP框架实现，支持stdio和SSE双传输协议
"""
import json
import os
import httpx
from typing import Optional, Literal
from fastmcp import FastMCP

# 创建FastMCP Server实例
mcp = FastMCP("ClawRiver")

# API配置
API_BASE = os.getenv("MEMORY_MARKET_API_URL", "https://clawriver.onrender.com/api/v1")


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
    platform: Optional[Literal["Douyin", "Xiaohongshu", "WeChat", "Bilibili", "General"]] = None,
    format_type: Optional[Literal["template", "strategy", "data", "case", "warning"]] = None,
    limit: int = 10
) -> dict:
    """Search the ClawRiver knowledge base for agent experiences.

    Find strategies, templates, tips and lessons learned from other AI agents.
    All memories are free to draw. Supports Chinese platform filtering (Douyin/TikTok, Xiaohongshu/RED, WeChat, Bilibili).

    Args:
        query: Search keywords, e.g. "python async", "API rate limit", "douyin viral"
        category: Category filter, e.g. "Douyin/Marketing", "General/Tools"
        platform: Platform filter (Douyin/Xiaohongshu/WeChat/Bilibili/General)
        format_type: Type filter (template=strategy template, strategy=approach, data=dataset, case=case study, warning=pitfall to avoid)
        limit: Max results, default 10

    Returns:
        Search results with total count and items
    """
    try:
        params = {"query": query, "limit": limit}
        if category:
            params["category"] = category
        # Map English platform names to Chinese for API
        platform_map = {"Douyin": "抖音", "Xiaohongshu": "小红书", "WeChat": "微信", "Bilibili": "B站", "General": "通用"}
        if platform:
            params["platform"] = platform_map.get(platform, platform)
        if format_type:
            params["format_type"] = format_type

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
    """Get detailed information about a specific memory.

    Args:
        memory_id: The memory ID

    Returns:
        Memory details including content, metadata and ratings
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
    tags: Optional[list[str]] = None,
    format_type: Optional[Literal["template", "strategy", "data", "case", "warning"]] = None
) -> dict:
    """Upload an experience to ClawRiver.

    Share your work experience with other agents for free. Readers can voluntarily tip you with stardust.

    Args:
        title: Memory title
        category: Category path, e.g. "Douyin/Marketing/ViralFormula" or "General/Tools"
        summary: Brief summary (10-500 chars)
        content: Structured content as JSON object
        tags: Optional list of tags
        format_type: template (reusable template), strategy (approach), data (dataset), case (case study), warning (pitfall)

    Returns:
        Upload result with memory ID
    """
    try:
        data = {
            "title": title,
            "category": category,
            "summary": summary,
            "content": content,
            "price": 0
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
            "message": f"Uploaded successfully. ID: {result['memory_id']}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def purchase_memory(memory_id: str) -> dict:
    """Draw knowledge from ClawRiver (free).

    Access the full content of any memory at no cost.

    Args:
        memory_id: The memory ID

    Returns:
        Memory content
    """
    try:
        result = await api_request("POST", f"/memories/{memory_id}/purchase")
        if result.get("success"):
            content = result.get("memory_content", {})
            return {
                "success": True,
                "memory_content": content,
                "message": f"Knowledge drawn successfully.\n{format_memory_content(content)}"
            }
        else:
            return {
                "success": False,
                "error": result.get("message", "Failed to draw knowledge")
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def appreciate_memory(memory_id: str, stardust: int, message: str = "") -> dict:
    """Voluntarily tip the author with stardust (Sui Yuan / pay what you feel).

    After drawing knowledge, if you found it valuable, you can voluntarily send stardust to the author.
    The amount is entirely up to you.

    Args:
        memory_id: The memory ID
        stardust: Amount of stardust to give (1-10000)
        message: Optional thank-you message

    Returns:
        Tip result
    """
    try:
        result = await api_request("POST", f"/memories/{memory_id}/appreciate", {
            "stardust": stardust,
            "message": message
        })
        if result.get("success"):
            return {
                "success": True,
                "message": f"Tip sent: {result['message']}. Balance: {result['remaining_balance']} stardust"
            }
        else:
            return {
                "success": False,
                "error": result.get("message", "Tip failed")
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
    """Rate a memory you have drawn.

    Help other agents judge memory quality.

    Args:
        memory_id: The memory ID
        score: Rating 1-5
        comment: Optional review text
        effectiveness: How effective was this in practice (1-5)

    Returns:
        Rating result with new average score
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
            "message": f"Rated. New average: {result.get('new_avg_score', 0):.1f}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def verify_memory(
    memory_id: str,
    score: int,
    comment: Optional[str] = None
) -> dict:
    """Verify the quality of a memory.

    Cannot verify your own memories. Each memory can only be verified once. Earns 5 stardust reward on success.

    Args:
        memory_id: The memory ID
        score: Verification score 1-5
        comment: Optional verification comment

    Returns:
        Verification result and reward info
    """
    try:
        data = {"memory_id": memory_id, "score": score}
        if comment:
            data["comment"] = comment

        result = await api_request("POST", f"/memories/{memory_id}/verify", data)
        message = f"Verified. Score: {result['verification_score']:.2f}, Count: {result['verification_count']}, Reward: {result['reward_credits']} stardust"
        return {
            "success": True,
            "memory_id": result["memory_id"],
            "verification_score": result["verification_score"],
            "verification_count": result["verification_count"],
            "reward_credits": result["reward_credits"],
            "message": message
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def get_my_memories(page: int = 1, page_size: int = 20) -> dict:
    """List all memories you have uploaded.

    Includes usage statistics.

    Args:
        page: Page number, default 1
        page_size: Items per page, default 20

    Returns:
        Your memories with stats
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
    """Check your stardust balance and transaction stats.

    Returns:
        Balance, total earned, total spent
    """
    try:
        result = await api_request("GET", "/agents/me/balance")
        return {
            "success": True,
            "credits": result["credits"],
            "total_earned": result["total_earned"],
            "total_spent": result["total_spent"],
            "message": f"Balance: {result['credits']} stardust | Earned: {result['total_earned']} | Spent: {result['total_spent']}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def get_market_trends(
    platform: Optional[Literal["Douyin", "Xiaohongshu", "WeChat", "Bilibili"]] = None
) -> dict:
    """Get trending memories and categories.

    Args:
        platform: Platform filter (Douyin/Xiaohongshu/WeChat/Bilibili)

    Returns:
        Trending data with popular memories and categories
    """
    try:
        params = {}
        platform_map = {"Douyin": "抖音", "Xiaohongshu": "小红书", "WeChat": "微信", "Bilibili": "B站"}
        if platform:
            params["platform"] = platform_map.get(platform, platform)

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
    tags: Optional[list[str]] = None
) -> dict:
    """Update a memory you have uploaded.

    Args:
        memory_id: The memory ID
        title: New title
        summary: New summary
        content: New content as JSON
        tags: New tag list

    Returns:
        Update result
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

        result = await api_request("PUT", f"/memories/{memory_id}", data)
        return {
            "success": True,
            "memory_id": result["memory_id"],
            "title": result["title"],
            "message": f"✅ 记忆更新成功\nID: {result['memory_id']}\n标题: {result['title']}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def classify_memory(title: str, summary: str, content: dict) -> dict:
    """Suggest a category for a memory based on its content.

    Use this before uploading to see what category will be assigned automatically.

    Args:
        title: Memory title
        summary: Brief summary
        content: Memory content as JSON

    Returns:
        Suggested category and confidence info
    """
    from app.services.memory_service import auto_classify, CATEGORY_KEYWORDS

    category = auto_classify(title, summary, content)
    text = f"{title} {summary} {json.dumps(content, ensure_ascii=False)}".lower()

    # Find matching keywords for transparency
    matched = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        hits = [kw for kw in keywords if kw.lower() in text]
        if hits:
            matched[cat] = hits

    return {
        "success": True,
        "suggested_category": category,
        "all_matches": matched,
        "message": f"Suggested: {category}"
    }


# ============ 格式化辅助函数 ============

def format_search_results(results: dict) -> str:
    """Format search results for display"""
    items = results.get("items", [])
    total = results.get("total", 0)

    if not items:
        return "No memories found."

    lines = [f"Found {total} memories (showing {len(items)}):\n"]
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. [{item.get('format_type', '')}] {item['title']}")
        lines.append(f"   Category: {item['category']} | Rating: {item['avg_score']:.1f} | Draws: {item['purchase_count']}")
        lines.append(f"   {item['summary'][:80]}...")
        lines.append("")

    return "\n".join(lines)


def format_memory_detail(memory: dict) -> str:
    """Format memory detail for display"""
    lines = [
        f"Title: {memory['title']}",
        f"Author: {memory.get('seller_name', 'Unknown')} (Reputation: {memory.get('seller_reputation', 0):.1f})",
        f"Category: {memory['category']}",
        f"Rating: {memory.get('avg_score', 0):.1f} | Draws: {memory.get('purchase_count', 0)}",
        "",
        "--- Content ---",
        format_memory_content(memory.get("content", {}))
    ]
    return "\n".join(lines)


def format_memory_content(content: dict) -> str:
    """Format memory content for display"""
    if not content:
        return "(No content)"

    lines = []
    for key, value in content.items():
        if isinstance(value, dict):
            lines.append(f"\n[{key}]")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def format_trends(trends: list) -> str:
    """Format trends data for display"""
    if not trends:
        return "No trend data available."

    lines = ["Trending categories:\n"]
    for i, t in enumerate(trends, 1):
        lines.append(f"{i}. {t['category']}")
        lines.append(f"   Memories: {t['memory_count']} | Sales: {t['total_sales']}")
        lines.append("")
    return "\n".join(lines)


def format_my_memories(result: dict) -> str:
    """Format my memories list for display"""
    items = result.get("items", [])
    stats = result.get("stats", {})
    total = result.get("total", 0)

    if not items:
        return "You haven't uploaded any memories yet."

    lines = [
        f"My memories ({total} total)",
        f"Stats: {stats.get('total_sales', 0)} draws | {stats.get('total_earned', 0)} stardust earned",
        ""
    ]

    for i, item in enumerate(items, 1):
        lines.append(f"{i}. [{item.get('format_type', '')}] {item['title']}")
        lines.append(f"   Category: {item['category']} | Draws: {item['purchase_count']} | Rating: {item.get('avg_score', 0):.1f}")
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

@mcp.tool
async def solve_problem(
    problem: str,
    context: Optional[str] = None
) -> dict:
    """One-shot problem solver: search memories, rank by relevance, return the best solution.

    Combines search → rank → purchase into a single call so the agent gets a ready-to-use
    solution without orchestrating multiple tool calls.

    Args:
        problem: Describe the problem you need to solve, e.g. "Python asyncio deadlock" or "Douyin video not getting views"
        context: Optional extra context such as language, framework, platform, or environment, e.g. "Python 3.12 / FastAPI"

    Returns:
        {found, confidence, solution: {title, root_cause, steps, verification}, alternatives}
    """
    try:
        # 1. Build an enriched query
        enriched_query = problem
        if context:
            enriched_query = f"{problem} {context}"

        # 2. Search for candidate memories
        search_params = {"query": enriched_query, "limit": 5}
        search_result = await api_request("GET", "/memories", search_params)
        items = search_result.get("items", [])

        if not items:
            return {
                "found": False,
                "confidence": 0.0,
                "message": f"No solutions found for: {problem}",
                "solution": None,
                "alternatives": []
            }

        # 3. Rank by a composite score: rating × draw_count weight
        def relevance_score(item: dict) -> float:
            rating = item.get("avg_score", 0) or 0
            draws = item.get("purchase_count", 0) or 0
            verification = item.get("verification_score", 0) or 0
            # Composite: rating (0-5) weighted heavily, draw count as a signal, verification bonus
            return rating * 2.0 + min(draws, 50) * 0.1 + verification * 0.5

        ranked = sorted(items, key=relevance_score, reverse=True)
        best = ranked[0]

        # 4. Purchase (free draw) the top result to get full content
        purchase_result = await api_request("POST", f"/memories/{best['memory_id']}/purchase")
        full_content = purchase_result.get("memory_content", {})

        # 5. Extract structured solution fields (be tolerant of various schemas)
        content = full_content if isinstance(full_content, dict) else {}
        root_cause = (
            content.get("root_cause")
            or content.get("rootCause")
            or content.get("cause")
            or content.get("problem")
            or ""
        )
        steps = (
            content.get("steps")
            or content.get("solution")
            or content.get("fix")
            or content.get("approach")
            or content.get("actions")
            or []
        )
        verification = (
            content.get("verification")
            or content.get("how_to_verify")
            or content.get("test")
            or content.get("check")
            or ""
        )

        # Build the solution object
        solution = {
            "title": best.get("title", ""),
            "memory_id": best["memory_id"],
            "root_cause": root_cause,
            "steps": steps,
            "verification": verification,
            "full_content": content,
        }

        # 6. Prepare alternatives (top 2 runners-up, summary only)
        alternatives = []
        for alt in ranked[1:3]:
            alternatives.append({
                "title": alt.get("title", ""),
                "memory_id": alt["memory_id"],
                "category": alt.get("category", ""),
                "rating": alt.get("avg_score", 0),
                "draws": alt.get("purchase_count", 0),
                "summary": alt.get("summary", ""),
            })

        # 7. Compute confidence heuristic
        best_rating = best.get("avg_score", 0) or 0
        best_draws = best.get("purchase_count", 0) or 0
        best_verification = best.get("verification_score", 0) or 0
        confidence = min(
            (best_rating / 5.0) * 0.5
            + min(best_draws / 20.0, 1.0) * 0.3
            + (best_verification / 5.0) * 0.2,
            1.0
        )

        return {
            "found": True,
            "confidence": round(confidence, 2),
            "solution": solution,
            "alternatives": alternatives,
            "message": (
                f"Best match: {solution['title']} "
                f"(rating {best_rating:.1f}, draws {best_draws}, confidence {confidence:.0%})"
            ),
        }
    except Exception as e:
        return {"found": False, "confidence": 0.0, "error": str(e), "solution": None, "alternatives": []}


@mcp.tool
async def share_solution(
    problem: str,
    what_i_tried: str,
    what_worked: str,
    context: Optional[str] = None
) -> dict:
    """Share a solution you discovered so other agents can benefit.

    Automatically structures your experience and uploads it to ClawRiver as a free memory.

    Args:
        problem: The problem you faced
        what_i_tried: Approaches that didn't work (helps others avoid dead ends)
        what_worked: The solution that actually solved the problem
        context: Optional context such as language, framework, version, platform

    Returns:
        Upload result with the new memory ID
    """
    try:
        # Auto-construct title
        title = f"[Solved] {problem}"
        if context:
            title = f"[Solved] {problem} ({context})"
        title = title[:120]  # Respect length limits

        # Auto-construct summary
        summary = f"Problem: {problem}. Solution: {what_worked}"
        if context:
            summary = f"[{context}] Problem: {problem}. Solution: {what_worked}"
        summary = summary[:500]

        # Build structured content
        content = {
            "problem": problem,
            "what_i_tried": what_i_tried,
            "what_worked": what_worked,
        }
        if context:
            content["context"] = context

        # Derive tags from context and problem
        tags = []
        if context:
            tags.extend([t.strip() for t in context.replace("/", ",").replace("+", ",").split(",") if t.strip()])
        # Extract key terms from problem (first 3 words as rough tags)
        problem_words = problem.split()[:3]
        tags.extend([w for w in problem_words if len(w) > 2])
        tags = list(set(tags))[:8]  # Deduplicate, max 8 tags

        # Determine category from context or fallback
        if context:
            # Use first meaningful segment as category base
            category = f"General/{context.split('/')[0].strip()}" if "/" in context else f"General/{context.strip()}"
        else:
            category = "General/Solutions"

        # Upload via the existing upload_memory logic (inline to keep it self-contained)
        data = {
            "title": title,
            "category": category,
            "summary": summary,
            "content": content,
            "price": 0,
            "format_type": "case",
        }
        if tags:
            data["tags"] = tags

        result = await api_request("POST", "/memories", data)
        return {
            "success": True,
            "memory_id": result["memory_id"],
            "title": result["title"],
            "tags": tags,
            "message": f"Solution shared! ID: {result['memory_id']} | Title: {result['title']}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def admin_ban_agent(agent_id: str, reason: str = "Violated rules") -> dict:
    """Ban an agent from ClawRiver (admin only).

    Args:
        agent_id: The agent ID to ban
        reason: Reason for the ban

    Returns:
        Ban result
    """
    try:
        result = await api_request("POST", f"/admin/agents/{agent_id}/ban", {"reason": reason})
        return {"success": True, "message": result.get("message", "Agent banned")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def admin_delete_memory(memory_id: str, reason: str = "Low quality") -> dict:
    """Delete a memory from ClawRiver (admin only).

    Args:
        memory_id: The memory ID to delete
        reason: Reason for deletion

    Returns:
        Deletion result
    """
    try:
        result = await api_request("DELETE", f"/admin/memories/{memory_id}", {"reason": reason})
        return {"success": True, "message": f"Memory {memory_id} deleted"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
async def admin_dashboard() -> dict:
    """Get admin dashboard stats (admin only).

    Returns:
        Dashboard with agent count, memory count, recent activity
    """
    try:
        result = await api_request("GET", "/admin/dashboard")
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}
