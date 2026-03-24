# ClawRiver 监控和可观测性指南

## 目录

1. [监控目标](#监控目标)
2. [核心概念](#核心概念)
3. [使用指南](#使用指南)
4. [最佳实践](#最佳实践)
5. [常见问题](#常见问题)
6. [扩展指南](#扩展指南)

## 监控目标

### 可观察性三大支柱

| 支柱 | 工具 | 目标 | 关键指标 |
|-----|------|------|---------|
| **Tracing** | Jaeger | 追踪请求路径 | Trace ID, Span, 延迟 |
| **Metrics** | Prometheus | 数值化监控 | 请求率、错误率、延迟 |
| **Logs** | Loki | 事件记录 | 错误日志、调试信息 |

### 关键性能指标 (KPI)

#### 故障发现
- **故障发现时间**: < 5 分钟
- **问题定位时间**: < 30 分钟
- **告警准确率**: > 95%

#### 性能监控
- **API 响应时间**: P95 < 1s
- **错误率**: < 1%
- **数据库查询**: P95 < 500ms
- **Qdrant 查询**: P95 < 1s

#### 业务监控
- **用户活跃度**: 实时统计
- **记忆数量**: 实时统计
- **购买交易**: 实时统计
- **团队活动**: 实时统计

## 核心概念

### Tracing (链路追踪)

#### 什么是 Trace？

Trace 代表一个完整的请求生命周期，从客户端发起请求到收到响应的所有步骤。

```python
# 示例：创建一个 trace
from app.telemetry import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("user_search"):
    # 这个 span 会被自动记录
    user_id = get_current_user()
    search_results = perform_search(query)
```

#### Span 层级

```
Trace: user_search_request
├─ Span: authentication
├─ Span: database_query
│  └─ Span: qdrant_search
└─ Span: response_serialization
```

#### Trace ID 传播

```python
# 自动传播（FastAPI 中间件处理）
# 手动传播（如果需要跨服务调用）
from app.telemetry.tracing import inject_trace_context

headers = {}
inject_trace_context(headers)
# headers 现在包含 traceparent
```

### Metrics (指标监控)

#### 指标类型

**Counter (计数器)**
- 只增不减的数值
- 适用场景: 请求总数、错误总数、交易数

```python
from app.telemetry.metrics import increment_http_requests

increment_http_requests("GET", "/api/v1/memories", 200)
```

**Gauge (仪表)**
- 可增可减的数值
- 适用场景: 当前连接数、活跃用户数、内存使用

```python
from app.telemetry.metrics import set_active_users

set_active_users(123)
```

**Histogram (直方图)**
- 记录值的分布情况
- 适用场景: 响应时间、请求大小

```python
from app.telemetry.metrics import record_http_request_duration

record_http_request_duration(0.123, "GET", "/api/v1/memories")
```

#### 百分位数

直方图自动计算百分位数：
- P50: 中位数
- P95: 95% 的请求快于这个值
- P99: 99% 的请求快于这个值

```promql
# PromQL 查询 P95 延迟
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Logs (日志)

#### 结构化日志

使用 JSON 格式，包含丰富的上下文信息：

```json
{
  "timestamp": "2024-03-23T09:05:00.123Z",
  "level": "INFO",
  "logger": "app.api.v1.endpoints",
  "message": "User login successful",
  "trace_id": "1234567890abcdef1234567890abcdef",
  "user_id": "user_123",
  "request_id": "req_456"
}
```

#### 日志级别

- **DEBUG**: 详细的调试信息
- **INFO**: 一般信息（推荐用于生产）
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

## 使用指南

### 开发环境

#### 1. 启动应用和监控

```bash
# 启动监控栈
docker-compose -f docker-compose.monitoring.yml up -d

# 启动应用（带 telemetry）
python -m app.main
```

#### 2. 添加 Tracing

```python
from app.telemetry import get_tracer

tracer = get_tracer(__name__)

async def create_memory(user_id: str, content: str):
    with tracer.start_as_current_span("create_memory") as span:
        # 添加属性
        span.set_attribute("user.id", user_id)
        span.set_attribute("memory.length", len(content))

        # 业务逻辑
        memory = await save_to_db(content)

        # 设置状态
        span.set_status(trace.Status(trace.StatusCode.OK))
        return memory
```

#### 3. 添加 Metrics

```python
from app.telemetry.metrics import (
    create_custom_counter,
    create_custom_histogram,
    increment_transactions
)

# 创建自定义指标
meter = get_meter("business_metrics")
purchase_counter = create_custom_counter(
    meter,
    name="purchases_total",
    description="Total number of purchases"
)

# 记录指标
increment_transactions("purchase", amount=10.0)
```

#### 4. 添加日志

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

logger.info(
    "Memory created successfully",
    extra={
        "user_id": user_id,
        "memory_id": memory.id,
        "memory_length": len(content)
    }
)
```

### 生产环境

#### 1. 配置告警通知

编辑 `alerts/alertmanager.yml`：

```yaml
receivers:
  - name: 'critical-receiver'
    email_configs:
      - to: 'on-call@memory-market.com'
        headers:
          Subject: '[CRITICAL] {{ .GroupLabels.alertname }}'
    slack_configs:
      - channel: '#critical-alerts'
        title: '🚨 CRITICAL ALERT'
```

#### 2. 调整采样率

```python
tracer_provider, meter_provider = setup_telemetry(
    service_name="memory-market",
    jaeger_endpoint="http://jaeger:4317",
    sample_rate=0.1  # 生产环境使用 10% 采样率
)
```

#### 3. 配置日志持久化

```python
setup_logging(
    level="INFO",
    log_file="./logs/app.log",
    service_name="memory-market"
)
```

### 故障排查流程

#### 1. 发现问题

在 Grafana Dashboard 中查看：
- 错误率飙升
- 响应时间增加
- 系统资源使用高

#### 2. 定位问题

**查看告警**

```bash
# 访问 Alertmanager
open http://localhost:9093
```

**查看 Metrics**

```promql
# 在 Prometheus 中查询
rate(http_requests_total{status_code="5.."}[5m])
```

**查看 Logs**

```bash
# 在 Grafana Loki 中搜索
{level="error"} |= "database connection"
```

**查看 Traces**

```bash
# 在 Jaeger 中查找
open http://localhost:16686
# 搜索 trace ID 或 service name
```

#### 3. 分析根因

1. 在 Jaeger 中查看慢请求的完整调用链
2. 找出最慢的 span
3. 查看相关日志
4. 分析数据库查询或外部调用

#### 4. 解决问题

1. 修复问题代码
2. 优化慢查询
3. 添加缓存
4. 扩容资源

## 最佳实践

### Tracing

✅ **DO:**
- 为关键业务操作添加 tracing
- 使用有意义的 span 名称
- 添加有用的属性（user_id, request_id）
- 保持 span 层级合理

❌ **DON'T:**
- 过度采样（生产环境 0.1 即可）
- 创建过深的 span 层级
- 在 span 中存储敏感数据
- 在 hot path 中创建不必要的 span

### Metrics

✅ **DO:**
- 使用合适的指标类型（Counter/Gauge/Histogram）
- 为关键操作添加指标
- 使用一致的命名规范
- 添加有用的标签

❌ **DON'T:**
- 创建高基数标签（user_id）
- 过度采样指标
- 忽略指标命名规范
- 记录无关紧要的指标

### Logging

✅ **DO:**
- 使用结构化日志
- 记录足够的上下文信息
- 使用适当的日志级别
- 记录错误和异常

❌ **DON'T:**
- 记录敏感信息
- 在循环中记录过多日志
- 使用 INFO 记录调试信息
- 忽略错误日志

### 告警

✅ **DO:**
- 设置合理的阈值
- 为告警添加 runbook 链接
- 配置抑制规则
- 定期审查告警规则

❌ **DON'T:**
- 告警过多（警报疲劳）
- 告警过少（遗漏关键问题）
- 忽略告警严重程度
- 不及时处理告警

## 常见问题

### Q: Traces 为什么没有显示在 Jaeger？

**A:** 检查以下几点：
1. Jaeger 服务是否运行
2. OTLP exporter 配置是否正确
3. 采样率是否为 0
4. 等待一段时间（可能有延迟）

### Q: Prometheus 无法抓取应用指标？

**A:** 检查以下几点：
1. 应用是否暴露 `/metrics` 端点
2. `prometheus.yml` 中的目标配置是否正确
3. 网络连接是否正常
4. 在 Prometheus UI 查看 "Targets" 页面

### Q: 日志未聚合到 Loki？

**A:** 检查以下几点：
1. Promtail 配置是否正确
2. 日志文件路径是否正确
3. Promtail 服务是否运行
4. 查看 Promtail 日志

### Q: 告警未触发？

**A:** 检查以下几点：
1. 告警规则语法是否正确
2. 评估间隔是否合理
3. 条件是否真的满足
4. Alertmanager 是否配置正确

### Q: 性能开销太大？

**A:** 优化策略：
1. 降低采样率（0.1 或更低）
2. 延长抓取间隔
3. 减少指标数量
4. 优化日志输出

## 扩展指南

### 添加自定义 Dashboard

1. 在 Grafana 中创建新 Dashboard
2. 添加图表和查询
3. 导出为 JSON
4. 保存到 `grafana/dashboards/` 目录
5. Grafana 会自动加载

### 添加自定义告警

1. 编辑 `alerts/alerting.yml`
2. 添加新的告警规则
3. 重新加载 Prometheus 配置
4. 验证告警是否触发

### 集成第三方服务

#### Datadog

```python
from opentelemetry.exporter.datadog import (
    DatadogSpanExporter,
    DatadogMetricReader
)
```

#### New Relic

```python
from opentelemetry.exporter.newrelic import (
    NewRelicSpanExporter,
    NewRelicMetricReader
)
```

### 配置 SLO (Service Level Objectives)

```promql
# 定义 SLO
# 目标: 99.9% 的请求成功率

sum(rate(http_requests_total{status_code=~"2..|3.."}[30d]))
/
sum(rate(http_requests_total[30d]))
```

### 配置 SLA (Service Level Agreement)

```promql
# 定义 SLA 告警
# 如果低于 99.9% 则告警

(
  sum(rate(http_requests_total{status_code=~"2..|3.."}[30d]))
  /
  sum(rate(http_requests_total[30d]))
) < 0.999
```

## 参考资源

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [Observability Engineering](https://www.oreilly.com/library/view/observability-engineering/9781492076720/)
