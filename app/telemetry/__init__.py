"""
OpenTelemetry 监控 - 可选模块

如果 opentelemetry 未安装，所有函数返回 None/空操作。
"""

def setup_telemetry(*args, **kwargs):
    """OpenTelemetry 未安装时返回空"""
    try:
        from opentelemetry import trace, metrics
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from .tracing import setup_tracing
        from .metrics import setup_metrics
        from ..core.logging import get_logger
        logger = get_logger(__name__)

        resource = Resource.create({
            SERVICE_NAME: kwargs.get("service_name", "clawriver"),
            "service.version": "1.0.0",
            "deployment.environment": kwargs.get("environment", "production"),
        })
        tracer_provider = setup_tracing(resource=resource, jaeger_endpoint=kwargs.get("jaeger_endpoint", "http://localhost:4317"))
        meter_provider = setup_metrics(resource=resource, prometheus_port=kwargs.get("prometheus_port", 9464))
        trace.set_tracer_provider(tracer_provider)
        metrics.set_meter_provider(meter_provider)
        logger.info("OpenTelemetry initialized")
        return tracer_provider, meter_provider
    except ImportError:
        return None, None


def get_tracer(name=None):
    try:
        from opentelemetry import trace
        return trace.get_tracer(name or __name__)
    except ImportError:
        return None


def get_meter(name=None):
    try:
        from opentelemetry import metrics
        return metrics.get_meter(name or __name__)
    except ImportError:
        return None


def shutdown_telemetry(tracer_provider=None, meter_provider=None):
    if tracer_provider:
        tracer_provider.shutdown()
    if meter_provider:
        meter_provider.shutdown()
