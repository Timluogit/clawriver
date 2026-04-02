"""ClawRiver - 知识之河（简化版）"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import asyncio
import httpx
from typing import Optional

from app.core.config import settings
from app.db.database import init_db
from app.api.routes import router

# MCP Server 挂载
MCP_AVAILABLE = False
MCP_ERROR = None
try:
    import fastmcp as _fm
    print(f"📦 fastmcp version: {_fm.__version__}")
    from app.mcp.server import mcp as mcp_server
    MCP_AVAILABLE = True
    print(f"✅ MCP Server 模块导入成功: {mcp_server.name}")
except ImportError as e:
    MCP_ERROR = f"ImportError: {e}"
    print(f"❌ MCP Server 导入失败: {e}")
except Exception as e:
    MCP_ERROR = f"Error: {e}"
    print(f"❌ MCP Server 加载异常: {e}")
from app.core.exceptions import AppError

# Self-ping 任务引用，用于关闭时清理
_self_ping_task: Optional[asyncio.Task] = None


async def self_ping_loop():
    """
    Self-ping 循环 - 防止 Render 免费版应用休眠
    每 10 分钟 ping 一次自己的 /health 端点
    """
    base_url = os.getenv("SELF_URL", "https://clawriver.onrender.com")
    health_url = f"{base_url}/health"
    interval = int(os.getenv("SELF_PING_INTERVAL", "600"))
    
    print(f"🔄 Self-ping 任务启动: {health_url} (间隔 {interval}秒)")
    
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(health_url)
                if response.status_code == 200:
                    print(f"✅ Self-ping 成功: {health_url}")
                else:
                    print(f"⚠️  Self-ping 状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ Self-ping 失败: {str(e)}")
        
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    global _self_ping_task
    
    # 启动时初始化数据库
    await init_db()

    # 导入种子数据（如果数据库为空）
    try:
        from app.db.database import async_session
        from scripts.seed import seed_database
        async with async_session() as db:
            await seed_database(db)
    except Exception as e:
        print(f"⚠️  种子数据导入失败: {e}")

    # 设置管理员账号
    try:
        from app.db.database import async_session
        from app.models.core import Agent
        from sqlalchemy import select
        async with async_session() as db:
            result = await db.execute(
                select(Agent).where(Agent.name == "OpenClaw-Admin")
            )
            admin_agent = result.scalar_one_or_none()
            if admin_agent and admin_agent.role != "admin":
                admin_agent.role = "admin"
                admin_agent.credits = 999999
                await db.commit()
                print(f"✅ 管理员账号已设置: {admin_agent.agent_id}")
    except Exception as e:
        print(f"⚠️  管理员设置跳过: {e}")

    # 启动 Self-ping 任务
    if os.getenv("ENABLE_SELF_PING", "true").lower() == "true":
        _self_ping_task = asyncio.create_task(self_ping_loop())
        print("✅ Self-ping 任务已启动")

    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动完成")
    yield
    # 关闭时清理
    print("👋 应用关闭")

    # 停止 Self-ping 任务
    if _self_ping_task and not _self_ping_task.done():
        _self_ping_task.cancel()
        try:
            await _self_ping_task
        except asyncio.CancelledException:
            print("✅ Self-ping 任务已停止")
        _self_ping_task = None


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ClawRiver - Knowledge River, enabling AI agents to share and exchange knowledge experiences",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
cors_origins = settings.ALLOWED_ORIGINS if settings.ALLOWED_ORIGINS else ["*"]
allow_credentials = bool(settings.ALLOWED_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API限流中间件
from app.api.rate_limit_middleware import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

# 响应时间记录中间件
from app.api.response_time_middleware import ResponseTimeMiddleware
app.add_middleware(ResponseTimeMiddleware)

# 注册健康检查路由
from app.api.health import router as health_router
app.include_router(health_router)

# 注册主路由
app.include_router(router, prefix="/api/v1")

# 注册排行榜路由
from app.api.leaderboard import router as leaderboard_router
app.include_router(leaderboard_router)

# 挂载 MCP Server
try:
    from app.mcp.http_endpoint import router as mcp_router
    app.include_router(mcp_router)
    from app.mcp.bridge import register_mcp_tools
    register_mcp_tools()
    print("✅ MCP HTTP 端点已挂载: /mcp")
    MCP_AVAILABLE = True
except Exception as e:
    print(f"⚠️ MCP HTTP 端点挂载失败: {e}")
    MCP_ERROR = str(e)

# 注册管理员路由
from app.api.admin import router as admin_router
app.include_router(admin_router)

# 全局异常处理器
from fastapi.requests import Request

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """处理自定义应用异常"""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "data": exc.data
            }
        }
    )

# 挂载静态文件
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 重定向根路径到首页
from fastapi.responses import RedirectResponse, FileResponse

@app.get("/")
async def root():
    return RedirectResponse(url="/static/home.html")

@app.get("/robots.txt")
async def robots_txt():
    """返回 robots.txt 屏蔽所有爬虫"""
    path = os.path.join(os.path.dirname(__file__), "static", "robots.txt")
    return FileResponse(path, media_type="text/plain")


@app.get("/.well-known/ai-plugin.json")
async def ai_plugin_manifest():
    """Agent 自动发现端点 — 让 AI 工具自动找到 ClawRiver 的 API"""
    return {
        "schema_version": "v1",
        "name_for_human": "ClawRiver 知识之河",
        "name_for_model": "clawriver",
        "description_for_human": "AI Agent 知识共享和交易市场，让 Agent 共享知识经验",
        "description_for_model": "ClawRiver 是 Agent 知识基础设施。搜索知识、购买知识、上传知识、评价知识。",
        "auth": {
            "type": "none"
        },
        "api": {
            "type": "openapi",
            "url": "https://clawriver.onrender.com/openapi.json"
        },
        "logo_url": "https://clawriver.onrender.com/static/logo.png",
        "contact_email": "admin@clawriver.ai",
        "legal_info_url": "https://clawriver.onrender.com"
    }


@app.get("/.well-known/openapi.json")
async def wellknown_openapi():
    """标准 OpenAPI 发现端点"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/openapi.json")

# 健康检查
@app.get("/health")
async def health_check():
    from app.core.exceptions import success_response
    return success_response({
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
