"""
结构化日志系统

提供 JSON 格式的结构化日志，集成 OpenTelemetry Trace ID。
"""

import logging
import sys
from datetime import datetime
from typing import Any
from pythonjsonlogger import jsonlogger

try:
    from opentelemetry import trace
    _has_otel = True
except ImportError:
    _has_otel = False

# 日志级别映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}


class JsonFormatter(jsonlogger.JsonFormatter):
    """
    自定义 JSON 日志格式化器

    输出格式：
    {
        "timestamp": "2024-03-23T09:05:00.123Z",
        "level": "INFO",
        "logger": "app.api.v1.endpoints",
        "message": "User login successful",
        "trace_id": "1234567890abcdef1234567890abcdef",
        "user_id": "user_123",
        "extra": {}
    }
    """

    def add_fields(self, log_record: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]):
        super().add_fields(log_record, record, message_dict)

        # 添加 ISO 格式时间戳
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # 添加日志级别
        log_record["level"] = record.levelname

        # 添加 logger 名称
        log_record["logger"] = record.name

        # 添加 Trace ID（如果存在）
        trace_id = self._get_trace_id()
        if trace_id:
            log_record["trace_id"] = trace_id

        # 添加用户 ID（从 record 中提取）
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id

        # 添加请求 ID（从 record 中提取）
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

    def _get_trace_id(self) -> str:
        """获取当前 trace ID"""
        if not _has_otel:
            return ""
        current_span = trace.get_current_span()
        if current_span is not None and current_span.context is not None:
            return format(current_span.context.trace_id, '032x')
        return ""


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    service_name: str = "memory-market"
):
    """
    配置结构化日志系统

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_file: 日志文件路径（可选）
        service_name: 服务名称
    """
    # 获取根 logger
    root_logger = logging.getLogger()

    # 设置日志级别
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # 清除现有 handlers
    root_logger.handlers.clear()

    # 创建 JSON formatter
    formatter = JsonFormatter()

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件 handler（如果指定了文件路径）
    if log_file:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 设置第三方库日志级别（降低噪音）
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)

    # 创建应用 logger
    app_logger = logging.getLogger(service_name)
    app_logger.setLevel(log_level)

    return app_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: logger 名称，通常使用 __name__

    Returns:
        Logger 实例
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger 适配器，自动添加上下文信息
    """

    def __init__(self, logger: logging.Logger, extra: dict[str, Any] | None = None):
        super().__init__(logger, extra or {})

    def process(self, msg: Any, kwargs: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        # 合并 extra 信息
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        kwargs["extra"].update(self.extra)

        # 如果有 user_id，添加到 record
        if "user_id" in self.extra:
            kwargs["extra"]["user_id"] = self.extra["user_id"]

        # 如果有 request_id，添加到 record
        if "request_id" in self.extra:
            kwargs["extra"]["request_id"] = self.extra["request_id"]

        return msg, kwargs


def get_logger_with_context(
    name: str,
    user_id: str | None = None,
    request_id: str | None = None,
    **extra
) -> LoggerAdapter:
    """
    获取带上下文的日志记录器

    Args:
        name: logger 名称
        user_id: 用户 ID
        request_id: 请求 ID
        **extra: 额外上下文信息

    Returns:
        LoggerAdapter 实例
    """
    logger = logging.getLogger(name)
    context = {}

    if user_id:
        context["user_id"] = user_id

    if request_id:
        context["request_id"] = request_id

    context.update(extra)

    return LoggerAdapter(logger, context)


# 装饰器：自动记录函数调用日志
def log_function_call(logger: logging.Logger | None = None, level: str = "DEBUG"):
    """
    装饰器：自动记录函数调用和返回

    Args:
        logger: Logger 实例，如果为 None 则使用函数所在模块的 logger
        level: 日志级别
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            _logger = logger or logging.getLogger(func.__module__)
            _logger.log(
                LOG_LEVELS.get(level.upper(), logging.DEBUG),
                f"Calling function: {func.__name__}",
                extra={"function": func.__name__}
            )
            try:
                result = await func(*args, **kwargs)
                _logger.log(
                    LOG_LEVELS.get(level.upper(), logging.DEBUG),
                    f"Function {func.__name__} completed successfully"
                )
                return result
            except Exception as e:
                _logger.error(
                    f"Function {func.__name__} failed: {str(e)}",
                    exc_info=True,
                    extra={"function": func.__name__}
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            _logger = logger or logging.getLogger(func.__module__)
            _logger.log(
                LOG_LEVELS.get(level.upper(), logging.DEBUG),
                f"Calling function: {func.__name__}",
                extra={"function": func.__name__}
            )
            try:
                result = func(*args, **kwargs)
                _logger.log(
                    LOG_LEVELS.get(level.upper(), logging.DEBUG),
                    f"Function {func.__name__} completed successfully"
                )
                return result
            except Exception as e:
                _logger.error(
                    f"Function {func.__name__} failed: {str(e)}",
                    exc_info=True,
                    extra={"function": func.__name__}
                )
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# 导入 asyncio 用于判断协程函数
import asyncio
