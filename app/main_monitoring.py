"""
ClawRiver 主应用 - 集成监控和可观测性

这是集成示例，展示如何在现有应用中添加完整监控能力。
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
import logging

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.telemetry import setup_telemetry, shutdown_telemetry
from app.telemetry.tracing import (
    instrument_fastapi,
    instrument_httpx,
    instrument_sqlalchemy
)
from app.telemetry.metrics import create_common_metrics


# 全局变量
tracer_provider = None
meter_provider = None
logger = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时：
    1. 初始化日志系统
    2. 初始化 OpenTelemetry
    3. 创建数据库连接
    4. 初始化指标

    关闭时：
    1. 清理 telemetry
    2. 关闭数据库连接
    """
    global tracer_provider, meter_provider, logger

    # ========== 启动阶段 ==========

    # 1. 设置日志
    logger = setup_logging(
        level=settings.LOG_LEVEL,
        log_file=settings.LOG_FILE,
        service_name="memory-market"
    )
    logger.info("Starting ClawRiver API", extra={"version": "1.0.0"})

    # 2. 初始化 OpenTelemetry
    tracer_provider, meter_provider = setup_telemetry(
        service_name="memory-market",
        jaeger_endpoint=settings.JAEGER_ENDPOINT,
        prometheus_port=settings.PROMETHEUS_PORT,
        environment=settings.ENVIRONMENT
    )
    logger.info("OpenTelemetry initialized successfully")

    # 3. 创建数据库引擎
    engine = create_engine(settings.DATABASE_URL)

    # 4. 为数据库添加追踪
    instrument_sqlalchemy(engine)
    logger.info("SQLAlchemy tracing instrumentation enabled")

    # 5. 为 HTTP 客户端添加追踪
    instrument_httpx()
    logger.info("HTTPX tracing instrumentation enabled")

    # 6. 创建通用指标
    from app.telemetry import get_meter
    meter = get_meter("memory-market")
    create_common_metrics(meter)
    logger.info("Common metrics created")

    # 7. 记录启动完成
    logger.info("ClawRiver API startup complete")

    # ========== 运行阶段 ==========
    yield

    # ========== 关闭阶段 ==========

    # 清理 telemetry
    if tracer_provider and meter_provider:
        shutdown_telemetry(tracer_provider, meter_provider)
        logger.info("Telemetry shutdown complete")

    logger.info("ClawRiver API shutdown complete")


# 创建 FastAPI 应用
app = FastAPI(
    title="ClawRiver API",
    description="ClawRiver API with full observability",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 为 FastAPI 添加自动追踪
instrument_fastapi(app, excluded_urls=["/health", "/metrics"])


# ========== 请求中间件 ==========

@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """添加请求上下文信息"""
    from app.core.logging import get_logger_with_context

    # 获取 trace ID
    from app.telemetry.tracing import get_trace_id
    trace_id = get_trace_id()

    # 创建带上下文的 logger
    request_id = request.headers.get("X-Request-ID", "")
    logger = get_logger_with_context(
        "app.middleware",
        user_id=request.headers.get("X-User-ID"),
        request_id=request_id or trace_id
    )

    # 记录请求开始
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None
        }
    )

    # 处理请求
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}", exc_info=True)
        raise


# ========== 健康检查端点 ==========

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "memory-market",
        "version": "1.0.0"
    }


# ========== Metrics 端点（由 Prometheus 自动抓取） ==========

@app.get("/metrics")
async def metrics():
    """
    Metrics 端点

    注意：实际指标由 OpenTelemetry Prometheus Exporter 暴露，
    这个端点只是占位符，实际访问 http://localhost:9464/metrics
    """
    return {"message": "Metrics available at http://localhost:9464/metrics"}


# ========== 示例 API 端点（带监控） ==========

from app.telemetry import get_tracer
from app.telemetry.metrics import (
    increment_http_requests,
    record_http_request_duration,
    record_search_latency,
    increment_transactions
)
import time


@app.get("/api/v1/memories")
async def list_memories(request: Request):
    """获取记忆列表（带完整监控）"""
    from app.core.logging import get_logger_with_context

    tracer = get_tracer(__name__)
    logger = get_logger_with_context(__name__, request_id=request.headers.get("X-Request-ID"))

    start_time = time.time()

    with tracer.start_as_current_span("list_memories") as span:
        # 添加 span 属性
        span.set_attribute("endpoint", "/api/v1/memories")
        span.set_attribute("user_id", request.headers.get("X-User-ID", "anonymous"))

        try:
            # 模拟数据库查询
            memories = await fetch_memories_from_db()

            # 记录指标
            duration = time.time() - start_time
            increment_http_requests("GET", "/api/v1/memories", 200)
            record_http_request_duration(duration, "GET", "/api/v1/memories")

            logger.info(f"Retrieved {len(memories)} memories", extra={"count": len(memories)})

            return {"memories": memories}

        except Exception as e:
            # 记录错误
            increment_http_requests("GET", "/api/v1/memories", 500)
            span.set_status({"status_code": 500})
            span.record_exception(e)
            logger.error(f"Failed to list memories: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/search")
async def search_memories(request: Request, query: str):
    """搜索记忆（带搜索性能监控）"""
    tracer = get_tracer(__name__)
    logger = get_logger(__name__)

    search_start = time.time()

    with tracer.start_as_current_span("search_memories") as span:
        span.set_attribute("query", query)
        span.set_attribute("user_id", request.headers.get("X-User-ID", "anonymous"))

        try:
            # 执行搜索
            results = await perform_search(query)

            # 记录搜索延迟
            search_duration = time.time() - search_start
            record_search_latency(search_duration, "hybrid")

            logger.info(
                f"Search completed: {query}",
                extra={
                    "query": query,
                    "results_count": len(results),
                    "duration_ms": search_duration * 1000
                }
            )

            return {"results": results}

        except Exception as e:
            span.record_exception(e)
            logger.error(f"Search failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Search failed")


@app.post("/api/v1/purchase")
async def purchase_memory(request: Request, memory_id: str):
    """购买记忆（带交易监控）"""
    tracer = get_tracer(__name__)
    logger = get_logger(__name__)

    with tracer.start_as_current_span("purchase_memory") as span:
        span.set_attribute("memory_id", memory_id)
        span.set_attribute("user_id", request.headers.get("X-User-ID", "anonymous"))

        try:
            # 处理购买
            purchase = await process_purchase(memory_id)

            # 记录交易
            increment_transactions("purchase", amount=purchase.amount)

            logger.info(
                f"Purchase completed: {memory_id}",
                extra={
                    "memory_id": memory_id,
                    "amount": purchase.amount
                }
            )

            return {"purchase_id": purchase.id}

        except Exception as e:
            span.record_exception(e)
            logger.error(f"Purchase failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Purchase failed")


# ========== 辅助函数 ==========

async def fetch_memories_from_db():
    """模拟从数据库获取记忆"""
    # 实际实现中这里会查询数据库
    await asyncio.sleep(0.01)  # 模拟延迟
    return [{"id": i, "content": f"Memory {i}"} for i in range(10)]


async def perform_search(query: str):
    """模拟搜索"""
    # 实际实现中这里会调用 Qdrant
    await asyncio.sleep(0.05)  # 模拟延迟
    return [{"id": i, "score": 0.9 - i * 0.1} for i in range(5)]


async def process_purchase(memory_id: str):
    """模拟处理购买"""
    from app.telemetry.metrics import increment_transactions
    import types

    # 模拟购买对象
    Purchase = types.SimpleNamespace
    purchase = Purchase(id="purchase_123", amount=10.0)

    await asyncio.sleep(0.02)  # 模拟延迟
    return purchase


# 导入 asyncio
import asyncio


# ========== 启动应用 ==========

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main_monitoring:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # 使用我们自己的日志配置
    )
