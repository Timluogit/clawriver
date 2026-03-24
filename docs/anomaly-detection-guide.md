# 异常检测与告警指南

## 目录

1. [概述](#概述)
2. [异常检测原理](#异常检测原理)
3. [规则配置指南](#规则配置指南)
4. [告警配置指南](#告警配置指南)
5. [API使用指南](#api使用指南)
6. [Grafana监控](#grafana监控)
7. [故障排查](#故障排查)
8. [最佳实践](#最佳实践)

---

## 概述

异常检测系统是 ClawRiver 的安全监控核心，通过实时检测用户行为、交易、系统指标等数据，主动识别潜在的安全威胁和异常行为，并通过多渠道告警及时通知管理员。

### 核心能力

- **实时检测**: 基于事件的实时异常检测，延迟<1分钟
- **高准确率**: 检测准确率>90%，误报率<5%
- **多类型覆盖**: 支持10+种异常类型（登录、交易、查询、行为、系统）
- **多渠道告警**: 支持邮件、Webhook、Slack等多种告警方式
- **智能聚合**: 自动聚合相似告警，避免告警风暴
- **可配置规则**: 灵活的规则配置系统，易于扩展

### 系统架构

```
事件数据源
    ↓
异常检测引擎 (AnomalyDetectionService)
    ↓
规则匹配器 (AnomalyRule)
    ├─ 登录异常规则
    ├─ 交易异常规则
    ├─ 查询异常规则
    ├─ 行为异常规则
    └─ 系统异常规则
    ↓
异常事件 (AnomalyEvent)
    ↓
告警服务 (AnomalyAlertingService)
    ↓
告警渠道
    ├─ 邮件
    ├─ Webhook
    └─ Slack
```

---

## 异常检测原理

### 检测流程

1. **事件采集**: 从审计日志、交易记录、搜索日志等数据源采集事件
2. **规则匹配**: 遍历所有启用的检测规则，对事件进行检查
3. **异常判定**: 根据规则逻辑和阈值配置，判断是否为异常
4. **事件创建**: 生成异常事件记录到数据库
5. **告警触发**: 根据告警配置创建告警并发送通知
6. **反馈学习**: 管理员确认异常后，更新规则统计

### 异常类型

#### 1. 登录异常 (login)

- **异地登录**: 用户从新的地理位置或IP地址登录
- **频繁失败**: 短时间内多次登录失败

#### 2. 交易异常 (transaction)

- **大额交易**: 单笔交易金额超过阈值
- **频繁交易**: 短时间内大量交易

#### 3. 查询异常 (query)

- **敏感词查询**: 搜索包含敏感关键词
- **异常频率**: 查询频率异常高

#### 4. 行为异常 (behavior)

- **异常活跃度**: 短时间内操作次数异常
- **异常操作**: 频繁执行敏感操作
- **异常访问模式**: 访问大量不同对象

#### 5. 系统异常 (system)

- **错误率飙升**: 系统错误率异常升高
- **延迟飙升**: 响应延迟异常升高

### 检测指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 检测延迟 | <1分钟 | 从事件发生到检测完成的时间 |
| 检测准确率 | >90% | 真阳性/(真阳性+假阳性) |
| 误报率 | <5% | 假阳性/总检测数 |
| 告警发送成功率 | >95% | 成功发送的告警/总告警数 |

---

## 规则配置指南

### 默认规则

系统预置了11种默认规则，首次运行时自动初始化：

1. **异地登录检测** (remote_login)
2. **频繁登录失败检测** (frequent_failed_login)
3. **大额交易检测** (large_amount_transaction)
4. **频繁交易检测** (frequent_transaction)
5. **敏感词查询检测** (sensitive_word_query)
6. **异常查询频率检测** (abnormal_query_frequency)
7. **异常活跃度检测** (abnormal_activity)
8. **异常操作检测** (abnormal_operation)
9. **错误率飙升检测** (error_rate_spike)
10. **延迟飙升检测** (latency_spike)
11. **异常访问模式检测** (unusual_access_pattern)

### 规则配置结构

```python
{
    "name": "规则名称",
    "anomaly_type": "异常类型",
    "anomaly_subtype": "异常子类型",
    "detection_logic": {
        # 检测逻辑配置
    },
    "threshold_config": {
        # 阈值配置
    },
    "alert_severity": "告警级别",
    "alert_channels": ["email", "webhook", "slack"],
    "alert_cooldown_minutes": 60  # 告警冷却时间
}
```

### 配置示例

#### 示例1: 调整异地登录检测阈值

```python
{
    "name": "异地登录检测",
    "anomaly_type": "login",
    "anomaly_subtype": "remote_login",
    "detection_logic": {},
    "threshold_config": {
        "max_new_ip_count": 5  # 从3调整为5
    },
    "alert_severity": "warning",
    "alert_channels": ["email"],
    "alert_cooldown_minutes": 120  # 从60调整为120分钟
}
```

#### 示例2: 配置敏感词列表

```python
{
    "name": "敏感词查询检测",
    "anomaly_type": "query",
    "anomaly_subtype": "sensitive_word",
    "detection_logic": {
        "sensitive_words": [
            "password",
            "token",
            "key",
            "secret",
            "admin",
            "root",
            "api_key",
            "access_token"
        ]
    },
    "threshold_config": {},
    "alert_severity": "warning",
    "alert_channels": ["email"],
    "alert_cooldown_minutes": 60
}
```

#### 示例3: 调整大额交易阈值

```python
{
    "name": "大额交易检测",
    "anomaly_type": "transaction",
    "anomaly_subtype": "large_amount",
    "detection_logic": {},
    "threshold_config": {
        "threshold": 200000,  # 2000元（从1000元调整）
        "use_relative_threshold": True  # 启用相对阈值
    },
    "alert_severity": "critical",  # 从warning升级为critical
    "alert_channels": ["email", "webhook", "slack"],
    "alert_cooldown_minutes": 30
}
```

### 自定义规则

#### 步骤1: 创建规则类

```python
from app.services.anomaly_rules import AnomalyRule

class CustomRule(AnomalyRule):
    def check(self, event_data: Dict[str, Any], db: Session) -> Optional[Dict[str, Any]]:
        # 实现检测逻辑
        if condition:
            return {
                "title": "自定义异常",
                "description": "异常描述",
                "evidence": {...},
                "confidence": 0.9
            }
        return None
```

#### 步骤2: 注册规则

```python
from app.services.anomaly_rules import AnomalyRuleFactory

# 注册规则类
AnomalyRuleFactory._rule_classes["custom_rule"] = CustomRule
```

#### 步骤3: 创建规则记录

```python
from app.models.tables import AnomalyRule

rule = AnomalyRule(
    name="自定义规则",
    anomaly_type="custom",
    anomaly_subtype="custom_rule",
    detection_logic={},
    threshold_config={},
    alert_severity="warning",
    alert_channels=["email"],
    alert_cooldown_minutes=60
)

db.add(rule)
db.commit()
```

---

## 告警配置指南

### 告警级别

| 级别 | 说明 | 响应时间 |
|------|------|----------|
| Critical | 严重异常，需要立即处理 | <15分钟 |
| Warning | 警告异常，需要关注 | <1小时 |
| Info | 信息性异常，需要记录 | <4小时 |

### 告警渠道配置

#### 邮件配置

```python
{
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "your_email@gmail.com",
    "smtp_password": "your_app_password",
    "from_email": "noreply@memorymarket.com",
    "to_emails": [
        "admin@memorymarket.com",
        "security@memorymarket.com"
    ]
}
```

#### Webhook配置

```python
{
    "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
}
```

#### Slack配置

```python
{
    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "channel": "#alerts"  # 或 "#security"
}
```

### 告警聚合

相似告警会自动聚合，避免告警风暴：

- **聚合键**: 规则ID + 异常类型 + 异常子类型 (+ 目标对象)
- **聚合窗口**: 告警冷却时间内
- **聚合内容**: 合并告警消息，显示聚合数量

示例：
```
[已聚合 3 个相似告警]

异常类型: login/frequent_failed_login
检测时间: 2026-03-23 10:30:00
置信度: 95.00%

描述: 用户在短时间内频繁登录失败

证据:
  ...
```

### 告警冷却

为了避免同一异常重复告警，系统实现了告警冷却机制：

- **冷却时间**: 每个规则可配置（默认60分钟）
- **冷却范围**: 相同聚合键的告警
- **冷却重置**: 异常被确认为真阳性或假阳性后，冷却重置

---

## API使用指南

### 异常事件API

#### 1. 获取异常事件列表

```bash
GET /anomalies?limit=100&anomaly_type=login&severity=critical&status=new
```

参数：
- `limit`: 返回数量（1-1000）
- `anomaly_type`: 异常类型（login/transaction/query/behavior/system）
- `severity`: 严重程度（critical/warning/info）
- `status`: 状态（new/investigating/resolved/false_positive）

响应：
```json
{
  "total": 10,
  "items": [
    {
      "event_id": "anom_xxx",
      "anomaly_type": "login",
      "anomaly_subtype": "frequent_failed_login",
      "severity": "critical",
      "title": "频繁登录失败",
      "description": "...",
      "target_type": "agent",
      "target_id": "agent_xxx",
      "confidence": 0.95,
      "status": "new",
      "detected_at": "2026-03-23T10:30:00",
      "confirmed_at": null,
      "resolution_note": null
    }
  ]
}
```

#### 2. 获取异常详情

```bash
GET /anomalies/{event_id}
```

#### 3. 确认异常

```bash
POST /anomalies/{event_id}/confirm?is_true_positive=true&resolution_note=用户账号被盗
```

参数：
- `is_true_positive`: 是否为真阳性（true/false）
- `resolution_note`: 解决说明（可选）

#### 4. 获取异常统计

```bash
GET /anomalies/stats/summary?start_time=2026-03-16T00:00:00&end_time=2026-03-23T23:59:59
```

响应：
```json
{
  "total_count": 100,
  "by_type": {
    "login": 30,
    "transaction": 25,
    "query": 20,
    "behavior": 15,
    "system": 10
  },
  "by_severity": {
    "critical": 20,
    "warning": 50,
    "info": 30
  },
  "by_status": {
    "new": 40,
    "investigating": 20,
    "resolved": 30,
    "false_positive": 10
  },
  "accuracy": 0.85
}
```

### 告警API

#### 1. 获取告警列表

```bash
GET /anomalies/alerts?limit=100&status=pending&severity=critical&channel_type=email
```

参数：
- `limit`: 返回数量（1-1000）
- `status`: 状态（pending/sent/failed/acknowledged）
- `severity`: 严重程度（critical/warning/info）
- `channel_type`: 渠道类型（email/webhook/slack）

#### 2. 获取告警详情

```bash
GET /anomalies/alerts/{alert_id}
```

#### 3. 确认告警

```bash
POST /anomalies/alerts/{alert_id}/ack
```

#### 4. 手动发送待发送告警

```bash
POST /anomalies/alerts/send?limit=50
```

#### 5. 获取告警统计

```bash
GET /anomalies/alerts/stats/summary?start_time=2026-03-16T00:00:00&end_time=2026-03-23T23:59:59
```

### 检测规则API

#### 1. 获取检测规则列表

```bash
GET /anomalies/rules
```

响应：
```json
{
  "total": 11,
  "items": [
    {
      "rule_id": "rule_xxx",
      "name": "异地登录检测",
      "description": null,
      "anomaly_type": "login",
      "anomaly_subtype": "remote_login",
      "alert_severity": "warning",
      "alert_channels": ["email"],
      "alert_cooldown_minutes": 60,
      "is_enabled": true,
      "total_detections": 100,
      "true_positive_count": 85,
      "false_positive_count": 5,
      "created_at": "2026-03-23T10:00:00",
      "updated_at": "2026-03-23T10:00:00"
    }
  ]
}
```

#### 2. 获取规则详情

```bash
GET /anomalies/rules/{rule_id}
```

#### 3. 启用/禁用规则

```bash
POST /anomalies/rules/{rule_id}/toggle?is_enabled=false
```

### 工具API

#### 手动触发异常检测

```bash
POST /anomalies/detect
```

请求体：
```json
{
  "agent_id": "agent_xxx",
  "ip_address": "10.0.0.1",
  "action_type": "login",
  "action_category": "auth"
}
```

#### 手动触发告警聚合

```bash
POST /anomalies/alerts/aggregate
```

---

## Grafana监控

### Dashboard概览

异常检测与告警Dashboard包含以下面板：

1. **异常事件趋势**: 时间序列图，显示异常事件数量随时间变化
2. **异常严重程度分布**: 饼图，显示不同严重程度的异常比例
3. **异常类型分布**: 时间序列图，显示不同类型异常的数量
4. **检测准确率**: 仪表盘，显示检测准确率
5. **告警发送成功率**: 仪表盘，显示告警发送成功率
6. **最近异常事件**: 表格，显示最近的异常事件列表
7. **异常状态分布**: 时间序列图，显示不同状态的异常数量
8. **告警渠道分布**: 饼图，显示不同渠道的告警比例
9. **检测规则统计**: 表格，显示各规则的检测统计

### 使用Dashboard

1. **导入Dashboard**: 在Grafana中导入`grafana/dashboards/anomaly-detection.json`
2. **配置数据源**: 配置PostgreSQL数据源连接到MemoryMarketDB
3. **设置刷新**: Dashboard默认30秒自动刷新
4. **查看统计**: 通过图表了解异常检测的整体情况
5. **定位问题**: 点击图表或表格项查看详细信息

### 常用查询

#### 查询最近1小时的关键异常

```sql
SELECT
  event_id,
  anomaly_type,
  title,
  severity,
  detected_at
FROM anomaly_events
WHERE
  detected_at >= NOW() - INTERVAL '1 hour'
  AND severity = 'critical'
ORDER BY
  detected_at DESC;
```

#### 查询准确率低的规则

```sql
SELECT
  rule_id,
  name,
  total_detections,
  true_positive_count,
  false_positive_count,
  (true_positive_count::FLOAT / NULLIF(total_detections, 0)) * 100 AS accuracy
FROM anomaly_rules
WHERE
  total_detections > 10
  AND (true_positive_count::FLOAT / NULLIF(total_detections, 0)) * 100 < 80
ORDER BY
  accuracy ASC;
```

#### 查询发送失败的告警

```sql
SELECT
  alert_id,
  event_id,
  channel_type,
  status,
  error_message,
  retry_count,
  created_at
FROM anomaly_alerts
WHERE
  status = 'failed'
  AND retry_count < max_retries
ORDER BY
  created_at DESC;
```

---

## 故障排查

### 常见问题

#### 1. 异常检测延迟过高

**症状**: 异常检测延迟超过1分钟

**原因**:
- 规则数量过多，检测耗时过长
- 数据库查询性能问题
- 检测服务资源不足

**解决方案**:
```python
# 检查规则数量
rules = db.query(AnomalyRule).filter(AnomalyRule.is_enabled == True).all()
print(f"启用的规则数量: {len(rules)}")

# 禁用不必要的规则
db.query(AnomalyRule).filter(AnomalyRule.rule_id == "rule_id").update({"is_enabled": False})

# 优化数据库查询
# 添加索引（已在表定义中）
```

#### 2. 误报率过高

**症状**: 误报率超过5%

**原因**:
- 规则阈值设置过低
- 检测逻辑不够精确
- 缺乏上下文信息

**解决方案**:
```python
# 查看误报最多的规则
rules = db.query(AnomalyRule).order_by(AnomalyRule.false_positive_count.desc()).limit(10).all()

for rule in rules:
    accuracy = rule.true_positive_count / rule.total_detections if rule.total_detections > 0 else 0
    print(f"{rule.name}: 准确率={accuracy:.2%}, 假阳性={rule.false_positive_count}")

# 调整规则阈值
rule.threshold_config["max_new_ip_count"] = 5  # 提高阈值
```

#### 3. 告警发送失败

**症状**: 告警状态为failed

**原因**:
- 告警渠道配置错误
- 网络连接问题
- 告警渠道服务不可用

**解决方案**:
```python
# 查看失败的告警
failed_alerts = db.query(AnomalyAlert).filter(AnomalyAlert.status == "failed").all()

for alert in failed_alerts:
    print(f"告警ID: {alert.alert_id}, 错误: {alert.error_message}")

# 检查配置
import os
print(f"SMTP配置: {os.getenv('SMTP_HOST')}")
print(f"Webhook URL: {os.getenv('WEBHOOK_URL')}")

# 手动重试
service = AnomalyAlertingService(db)
alerts = service.send_pending_alerts(limit=10)
```

#### 4. 告警风暴

**症状**: 短时间内收到大量告警

**原因**:
- 系统出现大规模异常
- 告警聚合配置不当
- 告警冷却时间设置过短

**解决方案**:
```python
# 查看异常事件统计
stats = detection_service.get_anomaly_stats()
print(f"异常总数: {stats['total_count']}")
print(f"按类型分布: {stats['by_type']}")

# 启用告警聚合
alerts = alerting_service.aggregate_alerts()

# 调整告警冷却时间
rule.alert_cooldown_minutes = 120  # 延长冷却时间
```

### 日志分析

#### 查看检测日志

```bash
# 查看异常检测服务的日志
tail -f logs/anomaly_detection.log

# 查看特定规则的活动
grep "remote_login" logs/anomaly_detection.log
```

#### 查看告警日志

```bash
# 查看告警发送日志
tail -f logs/anomaly_alerting.log

# 查看失败的告警
grep "Failed to send" logs/anomaly_alerting.log
```

### 性能优化

#### 数据库优化

```sql
-- 检查索引
SELECT
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE
  tablename IN ('anomaly_events', 'anomaly_alerts', 'anomaly_rules');

-- 分析查询性能
EXPLAIN ANALYZE
SELECT * FROM anomaly_events
WHERE detected_at >= NOW() - INTERVAL '7 days'
ORDER BY detected_at DESC
LIMIT 100;
```

#### 规则优化

```python
# 按性能排序规则
rule_stats = []
for rule in db.query(AnomalyRule).all():
    avg_time = rule.avg_detection_time if hasattr(rule, 'avg_detection_time') else 0
    rule_stats.append({
        "name": rule.name,
        "total_detections": rule.total_detections,
        "avg_time": avg_time
    })

# 禁用低优先级规则
for stat in sorted(rule_stats, key=lambda x: x["total_detections"])[:3]:
    print(f"考虑禁用低优先级规则: {stat['name']}")
```

---

## 最佳实践

### 1. 规则配置最佳实践

- **逐步调优**: 从宽松阈值开始，逐步收紧
- **监控效果**: 定期查看规则准确率和误报率
- **分层告警**: Critical级别的异常配置更严格的规则
- **业务适配**: 根据业务特点调整规则

### 2. 告警管理最佳实践

- **及时响应**: Critical级别的告警15分钟内响应
- **确认反馈**: 及时确认异常，提供准确的反馈
- **定期审查**: 每周审查异常事件，优化规则
- **告警分级**: 不同级别配置不同的响应流程

### 3. 系统维护最佳实践

- **定期清理**: 定期清理已解决的异常和旧告警
- **性能监控**: 监控检测延迟和系统性能
- **备份配置**: 定期备份规则配置
- **更新规则**: 根据新的威胁情报更新规则

### 4. 安全最佳实践

- **最小权限**: 告警服务使用最小权限运行
- **加密存储**: 告警渠道配置加密存储
- **审计日志**: 所有操作记录到审计日志
- **定期演练**: 定期进行异常检测演练

### 5. 监控指标

建议定期监控以下指标：

- **检测延迟**: <1分钟
- **检测准确率**: >90%
- **误报率**: <5%
- **告警发送成功率**: >95%
- **告警响应时间**: Critical<15分钟, Warning<1小时, Info<4小时

### 6. 故障恢复

- **高可用**: 部署多个检测服务实例
- **自动重试**: 告警发送失败自动重试
- **降级策略**: 检测服务异常时降级为定时检测
- **数据备份**: 定期备份异常事件和告警数据

---

## 附录

### A. 异常类型速查表

| 异常类型 | 异常子类型 | 检测规则 | 默认严重程度 |
|---------|-----------|---------|------------|
| login | remote_login | 异地登录 | warning |
| login | frequent_failed_login | 频繁失败 | critical |
| transaction | large_amount | 大额交易 | warning |
| transaction | frequent | 频繁交易 | warning |
| query | sensitive_word | 敏感词 | warning |
| query | abnormal_frequency | 异常频率 | warning |
| behavior | abnormal_activity | 异常活跃 | warning |
| behavior | abnormal_operation | 异常操作 | warning |
| behavior | unusual_access_pattern | 异常访问 | warning |
| system | error_rate_spike | 错误率 | critical |
| system | latency_spike | 延迟 | critical |

### B. API状态码

| 状态码 | 说明 |
|-------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

### C. 数据库表结构

详见 `app/models/tables.py`:

- `anomaly_events`: 异常事件表
- `anomaly_alerts`: 异常告警表
- `anomaly_rules`: 异常检测规则表

### D. 相关文档

- [API参考文档](./api-reference.md)
- [监控指南](./monitoring-guide.md)
- [审计日志指南](./audit-log-guide.md)
- [Grafana配置](./monitoring-setup.md)

---

## 更新日志

### v1.0.0 (2026-03-23)

- 初始版本发布
- 支持11种默认检测规则
- 支持邮件、Webhook、Slack告警
- 提供Grafana Dashboard
- 完整的API接口
- 单元测试覆盖

---

**文档版本**: 1.0.0
**最后更新**: 2026-03-23
**维护者**: ClawRiver Team
