"""
MCP Bridge - 将 FastMCP tools 注册到 HTTP 端点
在 fastmcp http_app 不可用时的降级方案
"""
import inspect
import json
from app.mcp.http_endpoint import register_tool


def _make_schema(func) -> dict:
    """从函数签名生成 JSON Schema"""
    sig = inspect.signature(func)
    properties = {}
    required = []

    for name, param in sig.parameters.items():
        if name in ('self', 'cls'):
            continue
        prop = {"type": "string"}
        annotation = param.annotation

        if annotation == int:
            prop = {"type": "integer"}
        elif annotation == float:
            prop = {"type": "number"}
        elif annotation == bool:
            prop = {"type": "boolean"}
        elif annotation == dict or str(annotation) == "dict":
            prop = {"type": "object"}
        elif annotation == list or str(annotation) == "list":
            prop = {"type": "array"}
        elif hasattr(annotation, "__origin__"):
            # typing.List, typing.Dict etc
            origin = annotation.__origin__
            if origin == dict:
                prop = {"type": "object"}
            elif origin == list:
                prop = {"type": "array"}

        if param.default == inspect.Parameter.empty:
            required.append(name)
        else:
            prop["default"] = param.default

        properties[name] = prop

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def register_mcp_tools():
    """从 MCP server 模块导入并注册所有工具"""
    try:
        from app.mcp.server import mcp
    except Exception as e:
        print(f"⚠️ 无法导入 MCP server: {e}")
        return 0

    registered = 0

    # 遍历 FastMCP 注册的工具
    try:
        # FastMCP 内部存储工具的方式
        tools_dict = mcp._tool_manager._tools if hasattr(mcp, '_tool_manager') else {}
        for name, tool in tools_dict.items():
            handler = tool.fn if hasattr(tool, 'fn') else None
            description = tool.description or ""
            schema = _make_schema(handler) if handler else {"type": "object", "properties": {}}

            if handler:
                register_tool(name, description, schema, handler)
                registered += 1
                print(f"  ✅ 注册工具: {name}")
    except Exception as e:
        print(f"⚠️ 遍历工具失败: {e}")
        # 降级方案：手动注册关键工具
        try:
            from app.mcp import server as mcp_mod
            tool_names = [
                'search_memories', 'get_memory', 'upload_memory',
                'purchase_memory', 'rate_memory', 'get_balance',
                'get_my_memories', 'get_market_trends', 'verify_memory',
                'solve_problem', 'share_solution', 'classify_memory',
                'update_memory', 'appreciate_memory',
                'admin_ban_agent', 'admin_delete_memory', 'admin_dashboard',
            ]
            for tname in tool_names:
                fn = getattr(mcp_mod, tname, None)
                if fn and callable(fn):
                    schema = _make_schema(fn)
                    doc = fn.__doc__ or ""
                    register_tool(tname, doc.strip(), schema, fn)
                    registered += 1
                    print(f"  ✅ 注册工具: {tname}")
        except Exception as e2:
            print(f"⚠️ 手动注册也失败: {e2}")

    print(f"📦 共注册 {registered} 个 MCP 工具")
    return registered
