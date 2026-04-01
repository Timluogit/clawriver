"""
MCP HTTP 端点 - 不依赖 fastmcp http_app
直接用 FastAPI 实现 MCP streamable-http 协议
"""
import json
import traceback
from typing import Any
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

router = APIRouter(prefix="/mcp", tags=["mcp"])

# 工具注册表
_tools: list[dict] = []
_tool_handlers: dict[str, Any] = {}


def register_tool(name: str, description: str, input_schema: dict, handler):
    """注册 MCP 工具"""
    _tools.append({
        "name": name,
        "description": description,
        "inputSchema": input_schema,
    })
    _tool_handlers[name] = handler


async def _call_tool(name: str, arguments: dict) -> Any:
    """调用工具"""
    if name not in _tool_handlers:
        return {"error": f"Tool '{name}' not found"}
    try:
        result = await _tool_handlers[name](**arguments)
        return result
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()[:500]}


@router.post("")
@router.post("/")
async def mcp_endpoint(request: Request):
    """MCP streamable-http 端点"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
            status_code=400,
        )

    method = body.get("method", "")
    req_id = body.get("id")
    params = body.get("params", {})

    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "ClawRiver", "version": "0.1.0"},
            },
        })

    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": _tools},
        })

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = await _call_tool(tool_name, arguments)

        if isinstance(result, dict) and "error" in result:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(result["error"])},
            })

        # 格式化为 MCP 工具结果
        content = []
        if isinstance(result, str):
            content.append({"type": "text", "text": result})
        elif isinstance(result, dict):
            content.append({"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)})
        else:
            content.append({"type": "text", "text": str(result)})

        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": content},
        })

    elif method == "notifications/initialized":
        return JSONResponse({"jsonrpc": "2.0", "id": None, "result": {}}, status_code=200)

    else:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        })


@router.get("/health")
async def mcp_health():
    """MCP 健康检查"""
    return {
        "mcp_available": True,
        "tools_count": len(_tools),
        "tools": [t["name"] for t in _tools],
    }
