# 自动遗忘机制指南

## 概述

自动遗忘机制是ClawRiver的核心特性之一，用于管理记忆和用户画像事实的生命周期。通过基于时间的自动失效和基于事件的主动覆盖，系统可以避免过期信息的累积，提升性能和准确性。

## 核心概念

### 1. TTL（Time To Live）

TTL是记忆或事实的生存时间，以天为单位。系统会根据TTL自动计算过期时间，并在过期后自动标记为失效。

### 2. 失效类型

- **时间失效**: 基于TTL的自动失效
- **事件失效**: 新信息覆盖旧信息

### 3. TTL配置

系统为不同类型的事实提供默认TTL配置：

| 事实类型 | 默认TTL（天） | 说明 |
|---------|-------------|------|
| personal | 365 | 个人信息（姓名、职位等） |
| preference | 90 | 偏好设置（语言、主题等） |
| habit | 180 | 习惯行为（工作时间、编辑器等） |
| skill | 365 | 技能信息（编程语言、框架等） |
| interest | 180 | 兴趣领域（研究方向等） |

## 功能特性

### 1. 自动过期检查

系统每隔一段时间（默认60分钟）自动检查并清理过期的记忆和事实。

### 2. 批量清理

采用批量处理策略（默认每次1000条），避免影响正常操作的性能。

### 3. 智能失效策略

- **记忆**: 标记为 `is_active=False`，保留历史记录
- **事实**: 标记为 `is_valid=False`，记录变更历史

### 4. 搜索集成

搜索结果自动过滤过期记忆，确保用户只看到有效的信息。

## API使用

### 1. 获取失效配置

```http
GET /api/auto-forget/config
```

**响应示例:**

```json
{
  "personal": 365,
  "preference": 90,
  "habit": 180,
  "skill": 365,
  "interest": 180,
  "default_ttl_days": 30
}
```

### 2. 更新失效配置

```http
POST /api/auto-forget/config
```

**请求体:**

```json
{
  "personal": 180,
  "preference": 60
}
```

### 3. 设置记忆TTL

```http
POST /api/auto-forget/set-memory-ttl
```

**请求体:**

```json
{
  "memory_id": "mem_xxx",
  "ttl_days": 30
}
```

**响应示例:**

```json
{
  "memory_id": "mem_xxx",
  "ttl_days": 30,
  "expiry_time": "2026-04-23T13:56:00Z",
  "message": "TTL set to 30 days"
}
```

### 4. 覆盖事实（事件失效）

```http
POST /api/auto-forget/override-fact
```

**请求体:**

```json
{
  "agent_id": "agent_xxx",
  "fact_type": "preference",
  "fact_key": "editor",
  "new_value": "vscode",
  "confidence": 0.9
}
```

### 5. 手动触发清理

```http
POST /api/auto-forget/manual
```

**响应示例:**

```json
{
  "checked": 10,
  "expired_memories": 3,
  "expired_facts": 5,
  "errors": 0,
  "triggered_at": "2026-03-23T13:56:00Z"
}
```

### 6. 获取统计信息

```http
GET /api/auto-forget/stats
```

**响应示例:**

```json
{
  "expired_memories": 15,
  "expired_facts": 32,
  "near_expiry_memories": 5,
  "near_expiry_facts": 8,
  "enabled": true,
  "default_ttl_days": 30,
  "scheduler_running": true
}
```

### 7. 调度器管理

**启动调度器:**

```http
POST /api/auto-forget/scheduler/start
```

**停止调度器:**

```http
POST /api/auto-forget/scheduler/stop
```

**获取调度器状态:**

```http
GET /api/auto-forget/scheduler/status
```

**响应示例:**

```json
{
  "running": true,
  "enabled": true,
  "interval_minutes": 60,
  "batch_size": 1000
}
```

## 配置参数

在 `app/core/config.py` 中配置以下参数：

```python
# 自动遗忘机制
AUTO_FORGET_ENABLED: bool = True  # 是否启用自动遗忘
AUTO_FORGET_SCHEDULE_MINUTES: int = 60  # 检查间隔（分钟）
AUTO_FORGET_BATCH_SIZE: int = 1000  # 批量清理大小
AUTO_FORGET_DEFAULT_TTL_DAYS: int = 30  # 默认TTL（天）

# TTL配置（按事实类型）
TTL_PERSONAL: int = 365  # 个人信息TTL
TTL_PREFERENCE: int = 90  # 偏好TTL
TTL_HABIT: int = 180  # 习惯TTL
TTL_SKILL: int = 365  # 技能TTL
TTL_INTEREST: int = 180  # 兴趣TTL
```

## 数据库表结构

### Memory表扩展字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| expiry_time | DateTime | 记忆过期时间（自动遗忘） |
| ttl_days | Integer | 生存时间（天） |

### ProfileFact表已有字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| expires_at | DateTime | 事实过期时间 |
| is_valid | Boolean | 是否有效 |

### UserProfile表扩展字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| default_ttl_days | Integer | 默认TTL（天） |
| ttl_config | JSON | TTL配置 |

## 最佳实践

### 1. TTL设置建议

- **短期信息**: 1-7天（如临时通知）
- **偏好信息**: 30-90天（如主题、语言）
- **技能信息**: 180-365天（如编程语言）
- **个人信息**: 365天（如姓名、职位）

### 2. 性能优化

- 批量设置TTL，避免频繁API调用
- 定期检查统计信息，监控过期数据量
- 合理设置批量大小，避免影响性能

### 3. 事件失效使用

当检测到用户行为变化时，及时覆盖旧事实：

```python
# 检测到用户更改编辑器
await auto_forget_service.override_fact(
    db,
    agent_id,
    "preference",
    "editor",
    "vscode",
    confidence=0.95
)
```

### 4. 监控和告警

定期检查统计信息，设置告警阈值：

- 过期记忆数 > 1000: 需要手动清理
- 即将过期记忆数 > 500: 需要关注TTL设置

## 性能影响

### 1. 搜索性能

- **预期提升**: +20%
- **原因**: 减少过期信息干扰，提高搜索准确度

### 2. 存储优化

- **自动清理**: 过期数据定期清理
- **存储节省**: 避免永久噪音积累

### 3. 系统资源

- **CPU占用**: 低（批量处理）
- **内存占用**: 低（增量清理）
- **数据库压力**: 低（索引优化）

## 常见问题

### Q1: 如何禁用自动遗忘？

在配置中设置 `AUTO_FORGET_ENABLED = False`

### Q2: 过期数据会被物理删除吗？

不会，数据只是标记为失效（`is_active=False`），仍保留在数据库中。

### Q3: 如何恢复过期数据？

可以通过更新API重新设置TTL或标记为有效。

### Q4: 批量清理会影响性能吗？

不会，批量清理在后台异步执行，不影响正常操作。

### Q5: TTL可以设置为0或负数吗？

不可以，TTL必须大于等于1天。

## 技术细节

### 1. 过期检查逻辑

```python
# 查询过期记忆
now = datetime.now()
stmt = select(Memory).where(
    and_(
        Memory.is_active == True,
        Memory.expiry_time.isnot(None),
        Memory.expiry_time <= now
    )
)
```

### 2. 事件失效逻辑

```python
# 查询现有事实并标记为失效
old_fact.is_valid = False

# 创建新事实并计算TTL
ttl_days = ttl_config.get(fact_type, default_ttl_days)
expires_at = datetime.now() + timedelta(days=ttl_days)

new_fact = ProfileFact(
    expires_at=expires_at,
    is_valid=True
)
```

### 3. 搜索过滤逻辑

```python
# 过滤过期记忆
if filter_expired:
    memories = [m for m in memories if
        m.is_active and
        (m.expiry_time is None or m.expiry_time > now)
    ]
```

## 更新日志

### v1.0.0 (2026-03-23)

- ✅ 实现基于时间的自动失效
- ✅ 实现基于事件的信息覆盖
- ✅ 实现批量清理机制
- ✅ 实现搜索集成（过滤过期记忆）
- ✅ 提供完整的管理API
- ✅ 提供统计监控功能
- ✅ 完成测试覆盖

## 相关文档

- [用户画像系统指南](./profile-guide.md)
- [搜索系统指南](./search-guide.md)
- [API文档](../README.md)
