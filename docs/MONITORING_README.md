# ClawRiver 监控系统 - 快速参考

## 🚀 快速启动

### 1. 启动监控栈

```bash
cd /Users/sss/.openclaw/workspace/memory-market
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. 验证服务

```bash
# 运行测试脚本
./test_monitoring.sh
```

### 3. 访问 Dashboard

| 服务 | URL | 凭证 |
|-----|-----|------|
| Grafana | http://localhost:3000 | admin / admin123 |
| Prometheus | http://localhost:9090 | - |
| Jaeger | http://localhost:16686 | - |
| Alertmanager | http://localhost:9093 | - |

## 📊 Dashboard 预览

### 主要 Dashboard

**ClawRiver - Monitoring Dashboard**
- API Request Rate: 请求速率趋势
- API Latency (P95): API 响应时间
- Active Users: 活跃用户数
- Total Memories: 记忆总数
- Transaction Rate: 交易速率
- Error Rate: 错误率
- System Metrics: CPU/Memory/Disk 使用率

访问: http://localhost:3000/d/memory-market-main

## 🔧 配置文件

| 文件 | 说明 |
|-----|------|
| `app/telemetry/__init__.py` | OpenTelemetry 主配置 |
| `app/telemetry/tracing.py` | Tracing (Jaeger) 配置 |
| `app/telemetry/metrics.py` | Metrics (Prometheus) 配置 |
| `app/core/logging.py` | 日志系统配置 |
| `prometheus.yml` | Prometheus 抓取配置 |
| `alerts/alerting.yml` | 告警规则 |
| `alerts/alertmanager.yml` | 告警通知配置 |
| `docker-compose.monitoring.yml` | 监控服务定义 |

## 📈 关键指标

### 性能指标

- **API 响应时间**: P95 < 1s
- **错误率**: < 1%
- **数据库查询**: P95 < 500ms
- **Qdrant 查询**: P95 < 1s

### 业务指标

- **活跃用户**: 实时统计
- **记忆数量**: 实时统计
- **交易数量**: 实时统计

### 系统指标

- **CPU 使用率**: < 80%
- **内存使用率**: < 85%
- **磁盘空间**: > 15%

## 🚨 告警规则

### Critical (立即响应)

- `ServiceDown`: 服务宕机
- `HighErrorRate`: 错误率 > 5%
- `QdrantDown`: Qdrant 不可用
- `PostgreSQLDown`: PostgreSQL 不可用

### Warning (关注)

- `HighAPILatency`: API 延迟 > 1s
- `SlowDatabaseQueries`: DB 查询 > 500ms
- `SlowVectorSearch`: Qdrant 查询 > 1s
- `HighCPUUsage`: CPU > 80%
- `HighMemoryUsage`: 内存 > 85%

## 🧪 测试

### 运行所有测试

```bash
pytest tests/test_monitoring.py -v
```

### 运行特定测试

```bash
# Tracing 测试
pytest tests/test_monitoring.py::TestTracing -v

# Metrics 测试
pytest tests/test_monitoring.py::TestMetrics -v

# Logging 测试
pytest tests/test_monitoring.py::TestLogging -v

# 集成测试
pytest tests/test_monitoring.py::TestMonitoringIntegration -v
```

### 性能开销测试

```bash
pytest tests/test_monitoring.py::TestMonitoringIntegration::test_metric_recording_overhead -v
```

## 📚 文档

- [监控配置指南](docs/monitoring-setup.md)
- [监控使用指南](docs/monitoring-guide.md)

## 🛠️ 故障排查

### Prometheus 无法抓取指标

1. 检查应用是否暴露 `/metrics` 端点
2. 检查 `prometheus.yml` 中的目标配置
3. 访问 http://localhost:9090/targets

### Traces 未显示在 Jaeger

1. 检查 Jaeger 服务: `docker ps | grep jaeger`
2. 检查 OTLP exporter 配置
3. 确认采样率 > 0

### 告警未触发

1. 检查告警规则语法
2. 查看 Prometheus UI → Status → Rules
3. 检查 Alertmanager 配置

## 🎯 下一步

- [ ] 配置实际的告警通知（邮件/Slack）
- [ ] 创建更多自定义 Dashboard
- [ ] 添加更多业务指标
- [ ] 配置日志告警
- [ ] 设置 SLO/SLA
- [ ] 配置长期存储策略

## 📞 支持

如有问题，请查看：
1. [监控配置指南](docs/monitoring-setup.md)
2. [监控使用指南](docs/monitoring-guide.md)
3. Grafana/Prometheus/Jaeger 官方文档
