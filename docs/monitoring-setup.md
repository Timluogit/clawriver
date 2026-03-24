# ClawRiver 监控系统配置指南

## 概述

ClawRiver 的监控和可观测性系统基于 OpenTelemetry 标准，提供完整的 Tracing、Metrics 和 Logs 能力。

## 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│ OpenTelemetry│────▶│   Jaeger    │
│   Service   │     │   Tracing    │     │  (Tracing)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │
       ├─────────────▶┌─────────────┐
       │              │  Prometheus │
       │              │  (Metrics)  │
       │              └─────────────┘
       │                     │
       │                     ├──────────────────────────────┐
       │                     │                              │
       │                     ▼                              ▼
       │              ┌─────────────┐              ┌─────────────┐
       │              │ Alertmanager│              │   Grafana   │
       │              │ (Alerting)  │              │ (Dashboard) │
       │              └─────────────┘              └─────────────┘
       │
       └─────────────▶┌─────────────┐
                      │    Loki     │
                      │   (Logs)    │
                      └─────────────┘
```

## 快速开始

### 1. 启动监控栈

```bash
cd /Users/sss/.openclaw/workspace/memory-market
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. 验证服务

```bash
# Prometheus
curl http://localhost:9090/-/healthy

# Grafana
curl http://localhost:3000/api/health

# Jaeger
curl http://localhost:16686/api/health

# Alertmanager
curl http://localhost:9093/-/healthy
```

### 3. 访问 Dashboard

- **Grafana**: http://localhost:3000
  - 用户名: `admin`
  - 密码: `admin123`
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **Alertmanager**: http://localhost:9093

## 配置说明

### OpenTelemetry 配置

在应用启动时初始化 telemetry：

```python
from app.telemetry import setup_telemetry
from fastapi import FastAPI

app = FastAPI()

# 初始化 telemetry
tracer_provider, meter_provider = setup_telemetry(
    service_name="memory-market",
    jaeger_endpoint="http://localhost:4317",
    prometheus_port=9464,
    environment="production"
)

# 为 FastAPI 添加 tracing
from app.telemetry.tracing import instrument_fastapi
instrument_fastapi(app)
```

### 日志配置

```python
from app.core.logging import setup_logging, get_logger

# 配置日志系统
setup_logging(
    level="INFO",
    log_file="./logs/app.log",
    service_name="memory-market"
)

# 获取 logger
logger = get_logger(__name__)
logger.info("Application started", extra={"user_id": "user_123"})
```

### Prometheus 配置

配置文件: `prometheus.yml`

主要配置项：
- `scrape_interval`: 抓取间隔（默认 15s）
- `evaluation_interval`: 规则评估间隔
- `rule_files`: 告警规则文件路径
- `scrape_configs`: 抓取目标配置

### Grafana 配置

配置文件位置：
- Datasource: `grafana/provisioning/datasources/prometheus.yml`
- Dashboards: `grafana/provisioning/dashboards/dashboards.yml`
- Dashboard JSON: `grafana/dashboards/memory-market.json`

### 告警配置

配置文件位置：
- Alert rules: `alerts/alerting.yml`
- Alertmanager: `alerts/alertmanager.yml`

告警级别：
- **critical**: 立即响应（服务宕机、错误率飙升）
- **warning**: 关注但不紧急（性能下降、资源使用高）

## 指标说明

### API 指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `http_requests_total` | Counter | HTTP 请求总数 |
| `http_request_duration_seconds` | Histogram | HTTP 请求延迟 |
| `http_requests_total{status_code="5.."}` | Counter | 5xx 错误数 |

### 业务指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `active_users_total` | Gauge | 活跃用户数 |
| `memories_total` | Gauge | 记忆总数 |
| `transactions_total` | Counter | 交易总数 |

### 性能指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `search_duration_seconds` | Histogram | 搜索延迟 |
| `qdrant_query_duration_seconds` | Histogram | Qdrant 查询延迟 |
| `db_query_duration_seconds` | Histogram | 数据库查询延迟 |

### 系统指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `node_cpu_seconds_total` | Counter | CPU 使用时间 |
| `node_memory_MemAvailable_bytes` | Gauge | 可用内存 |
| `node_filesystem_avail_bytes` | Gauge | 可用磁盘空间 |

## 告警规则

### 关键告警 (Critical)

- **ServiceDown**: 服务宕机超过 1 分钟
- **HighErrorRate**: 错误率超过 5%
- **QdrantDown**: Qdrant 不可用
- **PostgreSQLDown**: PostgreSQL 不可用

### 性能告警 (Warning)

- **HighAPILatency**: API P95 延迟超过 1s
- **SlowDatabaseQueries**: 数据库 P95 延迟超过 500ms
- **SlowVectorSearch**: Qdrant P95 延迟超过 1s
- **HighSearchLatency**: 搜索 P95 延迟超过 2s

### 业务告警 (Warning)

- **UnusualTransactionPattern**: 交易率异常高（5x 正常值）
- **DropInActiveUsers**: 活跃用户下降 50%
- **UnexpectedMemoryCountDrop**: 记忆数量快速下降

### 系统告警 (Warning)

- **HighCPUUsage**: CPU 使用率超过 80%
- **HighMemoryUsage**: 内存使用率超过 85%
- **LowDiskSpace**: 磁盘空间不足 15%

## 测试

### 运行单元测试

```bash
pytest tests/test_monitoring.py -v
```

### 运行集成测试（需要启动监控栈）

```bash
pytest tests/test_monitoring.py -v --run-slow
```

### 性能开销测试

```bash
pytest tests/test_monitoring.py::TestMonitoringIntegration::test_metric_recording_overhead -v
```

## 故障排查

### Prometheus 无法抓取指标

1. 检查应用是否暴露 metrics 端点
2. 检查 `prometheus.yml` 中的目标配置
3. 查看 Prometheus UI 的 "Targets" 页面

### Traces 未显示在 Jaeger

1. 检查 Jaeger 服务是否运行
2. 检查 OTLP exporter 配置
3. 确认采样率（默认 0.1）

### 日志未聚合到 Loki

1. 检查 Promtail 配置
2. 确认日志文件路径正确
3. 查看 Promtail 日志

### 告警未触发

1. 检查告警规则语法
2. 确认评估间隔
3. 查看 Alertmanager 日志

## 性能优化

### 降低监控开销

1. **调整采样率**: 生产环境使用 0.1 的采样率
2. **优化抓取间隔**: 关键指标 10s，一般指标 15s
3. **减少指标维度**: 避免过多的高基数标签

### 提升查询性能

1. **使用记录规则**: 预计算常用查询
2. **优化 PromQL**: 避免复杂的子查询
3. **添加索引**: 为常用查询添加 recording rules

## 下一步

- [ ] 配置实际的告警通知（邮件、Slack、Webhook）
- [ ] 创建更多业务相关的自定义指标
- [ ] 添加更多的 Dashboard
- [ ] 配置日志告警
- [ ] 设置性能基准测试
- [ ] 配置长期存储策略

## 参考文档

- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
