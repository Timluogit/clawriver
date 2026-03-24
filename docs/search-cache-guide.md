# 搜索缓存指南

本文档介绍 ClawRiver 的搜索缓存系统，包括架构、策略、配置和故障排查。

---

## 目录

- [概述](#概述)
- [缓存架构](#缓存架构)
- [缓存策略](#缓存策略)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [性能调优](#性能调优)
- [监控与告警](#监控与告警)
- [故障排查](#故障排查)

---

## 概述

搜索缓存系统旨在显著降低重复查询的延迟和资源消耗。通过智能缓存策略，可以将重复查询的响应时间从数百毫秒降低到<50ms。

### 核心指标

| 指标 | 目标值 |
|------|--------|
| 缓存命中率 | >70% |
| 缓存延迟 | <5ms |
| 端到端延迟（命中） | <50ms |
| 内存占用 | <2GB（10万缓存项） |

---

## 缓存架构

### 系统组件

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
┌──────▼──────────────────────┐
│  Search Cache Middleware    │
│  - 检查缓存                │
│  - 缓存命中返回             │
│  - 缓存未命中执行搜索       │
│  - 异步写入缓存             │
└──────┬──────────────────────┘
       │
       ├──────────────┬─────────────┐
       │              │             │
┌──────▼──────┐ ┌────▼──────────┐ ┌▼──────────────────┐
│   Redis     │ │   Search       │ │   Invalidation   │
│   Client    │ │   Engine       │ │   Service        │
│             │ │                │ │                   │
│ - 连接池    │ │ - 向量搜索     │ │ - 记忆更新失效    │
│ - 序列化    │ │ - 混合搜索     │ │ - 团队更新失效    │
│ - 健康检查  │ │ - 关键词搜索   │ │ - 批量失效       │
└─────────────┘ └───────────────┘ └──────────────────┘
```

### 核心模块

#### 1. Redis Client (`app/cache/redis_client.py`)

提供Redis客户端封装，包括：
- 连接池管理
- 健康检查
- 序列化/反序列化（JSON + Pickle）
- 统计信息获取

#### 2. Cache Keys (`app/cache/cache_keys.py`)

提供统一的缓存键生成策略：
- 搜索缓存键：`search:{hash}`
- 用户缓存键：`user:{user_id}:{hash}`
- 团队缓存键：`team:{team_id}:{hash}`
- 记忆缓存键：`memory:{memory_id}`

#### 3. Search Cache Middleware (`app/api/search_cache_middleware.py`)

搜索缓存中间件，提供：
- 缓存命中/未命中处理
- 异步写入缓存
- 缓存统计
- 装饰器支持

#### 4. Cache Invalidation Service (`app/services/cache_invalidation_service.py`)

缓存失效服务，提供：
- 记忆更新时失效相关缓存
- 团队更新时失效相关缓存
- 批量失效策略
- 延迟失效（防雪崩）

#### 5. Cache Stats API (`app/api/cache_stats.py`)

缓存统计API，提供：
- `GET /cache/stats` - 缓存统计
- `GET /cache/config` - 获取配置
- `PUT /cache/config` - 更新配置
- `DELETE /cache/clear` - 清空缓存
- `GET /cache/health` - 健康检查
- `GET /cache/info` - 详细信息

---

## 缓存策略

### TTL策略

- **默认TTL**: 1小时（3600秒）
- **可配置**: 通过环境变量或API动态调整
- **合理范围**: 300秒（5分钟）~ 86400秒（24小时）

### 淘汰策略

- **策略**: allkeys-lru
- **说明**: 当内存达到上限时，优先淘汰最近最少使用的键
- **最大内存**: 2GB（可配置）

### 缓存粒度

缓存键包含以下参数：
- 查询内容（query）
- 过滤条件（filters）
- 分页参数（page, page_size）
- 排序方式（sort_by）

### 失效策略

#### 主动失效

数据更新时主动失效相关缓存：
- **记忆更新**: 失效相关搜索缓存、用户缓存、记忆缓存
- **团队更新**: 失效团队相关缓存
- **用户更新**: 失效用户相关缓存

#### 延迟失效

- **默认延迟**: 5秒
- **目的**: 防止雪崩效应
- **可配置**: 通过`delay_invalidation`和`delay_seconds`参数

---

## 快速开始

### 1. 启动Redis

```bash
# 使用Docker Compose
cd /Users/sss/.openclaw/workspace/memory-market
docker-compose -f docker-compose.cache.yml up -d

# 验证Redis是否运行
docker-compose -f docker-compose.cache.yml ps
```

### 2. 配置环境变量

```bash
# 在 .env 文件中添加
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
CACHE_TTL=3600
```

### 3. 集成到搜索API

```python
from app.api.search_cache_middleware import cache_search, get_search_cache_middleware

# 方式1：使用装饰器
@cache_search(ttl=1800)
async def search_memories(query: str, filters: dict):
    # 搜索逻辑
    results = await search_engine.search(query, filters)
    return results

# 方式2：使用中间件
middleware = await get_search_cache_middleware()

async def search_with_cache(query: str, filters: dict):
    result = await middleware.search_with_cache(
        query=query,
        filters=filters,
        search_func=search_memories
    )
    return result
```

### 4. 集成到数据更新

```python
from app.services.cache_invalidation_service import get_cache_invalidation_service

# 在记忆更新后失效缓存
async def update_memory(memory_id: str, user_id: str, data: dict):
    # 更新数据库
    await db.update(memory_id, data)

    # 失效相关缓存
    service = await get_cache_invalidation_service()
    await service.invalidate_memory(memory_id, user_id=user_id, delay=False)
```

### 5. 启动API服务

```bash
# 启动FastAPI服务（包含缓存API）
uvicorn app.api.routes:app --host 0.0.0.0 --port 8000
```

---

## 配置说明

### Redis配置 (`redis/redis.conf`)

```conf
# 最大内存
maxmemory 2gb

# 淘汰策略
maxmemory-policy allkeys-lru

# 慢查询日志
slowlog-log-slower-than 10000  # 10ms
slowlog-max-len 128

# 持久化（可选）
save 900 1      # 15分钟内至少1次写入则保存
save 300 10     # 5分钟内至少10次写入则保存
save 60 10000   # 1分钟内至少10000次写入则保存
```

### 缓存配置

#### 环境变量

```bash
# Redis连接
REDIS_URL=redis://localhost:6379/0

# 缓存开关
CACHE_ENABLED=true

# 缓存过期时间（秒）
CACHE_TTL=3600

# 缓存未命中时是否写入
CACHE_ON_MISS=true

# 延迟失效（防雪崩）
CACHE_DELAY_INVALIDATION=true
CACHE_DELAY_SECONDS=5
```

#### API配置

```python
# 更新缓存配置
PUT /cache/config
{
  "enabled": true,
  "ttl": 3600,
  "cache_on_miss": true
}
```

---

## 性能调优

### 1. 提高缓存命中率

**策略**:
- 增加TTL时间
- 统一查询参数格式
- 合理设置过滤条件

**示例**:
```python
# 统一参数格式（避免重复缓存）
def normalize_filters(filters: dict) -> dict:
    return {
        k: sorted(v) if isinstance(v, list) else v
        for k, v in sorted(filters.items())
    }
```

### 2. 降低内存占用

**策略**:
- 调整Redis最大内存
- 使用更短的TTL
- 定期清理过期缓存

**示例**:
```conf
# 降低最大内存
maxmemory 1gb

# 使用更积极的淘汰策略
maxmemory-policy volatile-lru  # 只淘汰有过期时间的键
```

### 3. 优化延迟

**策略**:
- 使用本地连接（避免网络开销）
- 优化序列化（JSON > Pickle）
- 减少缓存数据量

**示例**:
```python
# 只缓存必要字段
def prepare_cache_value(result: dict) -> dict:
    return {
        "results": [
            {
                "id": r["id"],
                "title": r["title"],
                "snippet": r["snippet"][:200]  # 截断长文本
            }
            for r in result["results"]
        ],
        "total": result["total"]
    }
```

### 4. 并发优化

**策略**:
- 使用连接池
- 异步写入缓存
- 批量失效

**示例**:
```python
# 异步写入缓存（不阻塞响应）
asyncio.create_task(write_cache(key, value))
```

---

## 监控与告警

### Grafana Dashboard

访问 `http://localhost:3000/d/cache-performance` 查看缓存性能仪表板。

**关键指标**:
- 缓存命中率趋势
- 缓存大小趋势
- 缓存延迟趋势
- 缓存淘汰统计

### Prometheus指标

```yaml
# 缓存命中率
rate(redis_cache_hits_total[5m]) / (rate(redis_cache_hits_total[5m]) + rate(redis_cache_misses_total[5m])) * 100

# 缓存延迟
histogram_quantile(0.95, rate(cache_latency_bucket[5m]))

# Redis内存使用
redis_memory_used_bytes / redis_memory_max_bytes * 100
```

### 告警规则

```yaml
groups:
  - name: cache_alerts
    rules:
      # 缓存命中率过低
      - alert: LowCacheHitRate
        expr: cache_hit_rate < 50
        for: 5m
        annotations:
          summary: "Cache hit rate is below 50%"

      # Redis内存使用过高
      - alert: HighRedisMemoryUsage
        expr: redis_memory_usage > 80
        for: 5m
        annotations:
          summary: "Redis memory usage is above 80%"

      # Redis连接失败
      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        annotations:
          summary: "Redis is not responding"
```

---

## 故障排查

### 问题1: 缓存命中率为0

**原因**:
- 缓存未启用
- TTL设置过短
- 查询参数不一致

**解决**:
```bash
# 检查缓存状态
curl http://localhost:8000/cache/config

# 查看缓存统计
curl http://localhost:8000/cache/stats

# 检查Redis键
redis-cli KEYS "search:*"
```

### 问题2: 缓存未命中仍然返回旧数据

**原因**:
- 缓存失效未生效
- 延迟失效时间过长

**解决**:
```python
# 手动清空缓存
await service.invalidate_memory(memory_id, delay=False)

# 检查失效队列
redis-cli KEYS "*invalidation*"
```

### 问题3: Redis内存占用过高

**原因**:
- TTL设置过长
- 淘汰策略不当
- 缓存数据量过大

**解决**:
```conf
# 调整最大内存
maxmemory 1gb

# 调整淘汰策略
maxmemory-policy allkeys-lru

# 清空缓存
redis-cli FLUSHDB
```

### 问题4: 缓存延迟过高

**原因**:
- Redis连接池耗尽
- 网络延迟
- 序列化开销

**解决**:
```python
# 增加连接池大小
RedisClient(max_connections=100)

# 使用本地Redis
REDIS_URL=redis://localhost:6379/0

# 优化序列化
# 优先使用JSON而不是Pickle
```

### 问题5: 缓存一致性问题

**原因**:
- 失效策略不完整
- 延迟失效导致过期数据

**解决**:
```python
# 立即失效（延迟失效改为False）
await service.invalidate_memory(memory_id, delay=False)

# 使用更全面的失效模式
patterns = [
    "search:*",
    f"user:{user_id}:*",
    f"team:{team_id}:*",
    f"memory:{memory_id}"
]
```

---

## 最佳实践

### 1. 缓存键设计

- 使用MD5哈希避免键过长
- 包含所有影响结果的参数
- 排序参数保证一致性

### 2. 缓存值设计

- 只缓存必要字段
- 移除动态数据（时间戳、计数器）
- 使用轻量级序列化

### 3. 失效策略

- 数据更新立即失效
- 批量操作批量失效
- 使用延迟失效防雪崩

### 4. 监控

- 持续监控命中率
- 关注延迟和内存
- 设置告警阈值

---

## 总结

搜索缓存系统通过智能缓存策略显著提升了查询性能。关键成功因素包括：

1. **合理的缓存策略**: TTL、淘汰策略、失效策略
2. **完善的监控**: 实时跟踪命中率、延迟、内存
3. **快速响应问题**: 详细的日志和告警机制
4. **持续优化**: 根据业务需求调整配置

如有问题，请参考本文档的故障排查章节或联系技术团队。
