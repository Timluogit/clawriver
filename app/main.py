"""ClawRiver - 知识之河"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.db.database import init_db
from app.api.routes import router
from app.core.exceptions import AppError

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时初始化数据库
    try:
        from app.db.init_db import init_db as fast_init_db
        await fast_init_db()
    except Exception as e:
        print(f"⚠️ 快速初始化失败，尝试标准初始化: {e}")
        await init_db()

    # 导入种子数据（如果数据库为空）
    try:
        from app.db.database import async_session
        from scripts.seed import seed_database
        async with async_session() as db:
            await seed_database(db)
    except Exception as e:
        print(f"⚠️  种子数据导入失败: {e}")

    # 初始化缓存系统
    if settings.CACHE_ENABLED:
        from app.api.search_cache_middleware import get_search_cache_middleware
        from app.services.cache_invalidation_service import get_cache_invalidation_service

        try:
            # 初始化搜索缓存中间件
            cache_middleware = await get_search_cache_middleware()
            print(f"✅ 搜索缓存中间件初始化成功 (TTL: {settings.CACHE_TTL}s)")

            # 初始化缓存失效服务
            invalidation_service = await get_cache_invalidation_service()
            print(f"✅ 缓存失效服务初始化成功")

        except Exception as e:
            print(f"⚠️  缓存系统初始化失败: {e}")
            print(f"💡 请确保Redis已启动: {settings.REDIS_URL}")

    # 初始化自动遗忘系统
    if settings.AUTO_FORGET_ENABLED:
        from app.services.forget_scheduler import get_forget_scheduler

        try:
            forget_scheduler = get_forget_scheduler()
            await forget_scheduler.start()
            print(f"✅ 自动遗忘系统启动成功 (间隔: {settings.AUTO_FORGET_SCHEDULE_MINUTES}分钟)")

        except Exception as e:
            print(f"⚠️  自动遗忘系统启动失败: {e}")

    # 注册外部数据源适配器
    try:
        from app.services.external_source_service import register_all_adapters
        register_all_adapters()
        print("✅ 外部数据源适配器注册成功 (6个)")
    except Exception as e:
        print(f"⚠️  外部数据源适配器注册失败: {e}")

    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动完成")
    yield
    # 关闭时清理
    print("👋 应用关闭")

    # 停止遗忘调度器
    if settings.AUTO_FORGET_ENABLED:
        from app.services.forget_scheduler import get_forget_scheduler

        try:
            forget_scheduler = get_forget_scheduler()
            await forget_scheduler.stop()
            print("✅ 自动遗忘系统已停止")

        except Exception as e:
            print(f"⚠️  停止自动遗忘系统时出错: {e}")

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ClawRiver - 知识之河，让AI Agent共享和流动知识经验",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 审计日志中间件
from app.api.audit_middleware import AuditMiddleware
app.add_middleware(AuditMiddleware)

# API限流中间件（每分钟最多100次请求）
from app.api.rate_limit_middleware import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

from app.api.health import router as health_router
app.include_router(health_router)


# 注册路由
app.include_router(router, prefix="/api/v1")

# 注册流动记录路由
from app.api.transactions import router as transactions_router
app.include_router(transactions_router)

# 注册团队管理路由
from app.api.teams import router as teams_router
from app.api.team_members import router as team_members_router
from app.api.team_credits import router as team_credits_router

app.include_router(teams_router, prefix="/api")
app.include_router(team_members_router, prefix="/api")
app.include_router(team_credits_router, prefix="/api")

# 注册自动遗忘路由
from app.api.auto_forget import router as auto_forget_router
app.include_router(auto_forget_router, prefix="/api")

# 注册外部数据源路由
from app.api.external_sources import router as external_sources_router
app.include_router(external_sources_router, prefix="/api")

# 注册评估框架路由
from app.api.evaluation import router as evaluation_router
app.include_router(evaluation_router)

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
from fastapi.responses import RedirectResponse

@app.get("/")
async def root():
    return RedirectResponse(url="/static/home.html")

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
