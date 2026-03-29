# ClawRiver P1 问题修复方案

> 生成时间：2026-03-29
> 分析范围：`app/` 目录全部核心代码
> 状态：每个问题包含问题分析、修复方案、代码示例、预估工时

---

## P1-1: 内存限流器无上限增长（OOM 风险）

### 问题分析

**文件**: `app/api/rate_limit_middleware.py`

```python
self.request_counts: dict[str, list[float]] = defaultdict(list)
```

核心问题：
1. **字典无限增长**：每个新客户端 IP 都会创建一个条目，且永远不会删除过期 IP 的记录。如果攻击者伪造大量不同 IP，字典条目数 → ∞
2. **每个 IP 的列表也会增长**：虽然在每次请求时会清理过期时间戳，但单个活跃 IP 在窗口内也会积累最多 `max_requests` 条记录
3. **无最大容量保护**：没有对字典大小做上限限制
4. **Starlette BaseHTTPMiddleware 已知问题**：`call_next` 会将 request body 缓存在内存中（使用 `BodyStream`），与限流器的内存增长叠加

**影响**: 在公网部署（如 Render）场景下，伪造 IP 攻击可在数分钟内耗尽内存。

### 修复方案：固定窗口 + Redis 后备 + LRU 淘汰

替换为固定窗口计数器（内存 O(1)/IP），并增加 IP 条目上限：

```python
"""API Rate Limiting Middleware — 固定窗口 + LRU 淘汰"""
import time
from collections import OrderedDict
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """固定窗口限流中间件（内存安全）"""

    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        max_ips: int = 10000,           # 最多跟踪的 IP 数量
        cleanup_interval: int = 1000,   # 每处理 N 个请求做一次清理
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_ips = max_ips
        self.cleanup_interval = cleanup_interval

        # 固定窗口: {ip: {"count": int, "window_start": float}}
        self._windows: OrderedDict[str, dict] = OrderedDict()
        self._total_requests = 0

    def _get_current_window(self, ip: str) -> dict:
        """获取或创建当前窗口"""
        now = time.time()
        window_start = now - (now % self.window_seconds)  # 对齐到固定窗口

        if ip not in self._windows:
            # LRU 淘汰：超过上限时移除最旧的条目
            if len(self._windows) >= self.max_ips:
                self._windows.popitem(last=False)
            self._windows[ip] = {"count": 0, "window_start": window_start}

        entry = self._windows[ip]

        # 窗口过期则重置
        if entry["window_start"] != window_start:
            entry["count"] = 0
            entry["window_start"] = window_start

        return entry

    def _periodic_cleanup(self):
        """定期清理过期窗口"""
        self._total_requests += 1
        if self._total_requests % self.cleanup_interval != 0:
            return

        now = time.time()
        current_window_start = now - (now % self.window_seconds)
        expired = [
            ip for ip, entry in self._windows.items()
            if entry["window_start"] < current_window_start
        ]
        for ip in expired:
            del self._windows[ip]

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        window = self._get_current_window(client_ip)

        if window["count"] >= self.max_requests:
            remaining = self.window_seconds - (time.time() - window["window_start"])
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": f"请求过于频繁，每分钟最多{self.max_requests}次请求",
                        "data": {"retry_after": max(int(remaining), 1)},
                    },
                },
                headers={"Retry-After": str(max(int(remaining), 1))},
            )

        window["count"] += 1
        self._periodic_cleanup()

        return await call_next(request)
```

### 预估工时
- **1.5 小时**（含测试）

---

## P1-2: N+1 查询（100条搜索 = 101次 DB 查询）

### 问题分析

**文件**: `app/services/memory_service_v2.py` → `_fallback_search` 函数

```python
# 第一步: 获取搜索结果（1次查询）
result = await db.execute(stmt)
memories = result.scalars().all()

# 第二步: 对每条记忆循环查询卖家信息（N次查询）
for mem in memories:
    seller_result = await db.execute(
        select(Agent.name, Agent.reputation_score).where(Agent.agent_id == mem.seller_agent_id)
    )
    seller = seller_result.first()
```

**影响**: `page_size=100` 时产生 **101 次 DB 查询**。在高并发搜索场景下，数据库连接会被快速耗尽。

**注**: `search_memories` 主路径使用了 `JOIN`（在 `base_stmt` 中已经 `join(Agent)`），但 `_fallback_search` 是无 Qdrant 时的回退路径，其内部是分开查询的。

### 修复方案：使用 JOIN 的单次查询

```python
async def _fallback_search(
    db: AsyncSession,
    base_stmt,
    query: str,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "relevance"
) -> dict:
    """纯 SQL 关键词搜索 — 单次 JOIN 查询"""
    from app.models.tables import Agent

    # ===== 修复: 使用 JOIN 避免 N+1 =====
    stmt = base_stmt  # base_stmt 已包含 .join(Agent)

    # 关键词匹配（大小写不敏感）
    if query:
        q = query.lower()
        search_filter = or_(
            func.lower(Memory.title).contains(q),
            func.lower(Memory.summary).contains(q),
            func.lower(Memory.category).contains(q),
        )
        stmt = stmt.where(search_filter)

    # 排序
    if sort_by == "created_at":
        stmt = stmt.order_by(desc(Memory.created_at))
    elif sort_by == "purchase_count":
        stmt = stmt.order_by(desc(Memory.purchase_count))
    elif sort_by == "price":
        stmt = stmt.order_by(Memory.price)
    else:
        stmt = stmt.order_by(desc(Memory.avg_score), desc(Memory.purchase_count))

    # 获取总数
    count_stmt = select(func.count(Memory.memory_id)).select_from(Memory).where(
        Memory.is_active == True
    )
    if query:
        count_stmt = count_stmt.where(search_filter)
    total = (await db.execute(count_stmt)).scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    # 单次 JOIN 查询获取记忆 + 卖家信息
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        mem = row[0]   # Memory 对象
        seller_name = row[1] if len(row) > 1 else "unknown"
        seller_rep = row[2] if len(row) > 2 else 5.0

        items.append({
            "memory_id": mem.memory_id,
            "seller_agent_id": mem.seller_agent_id,
            "seller_name": seller_name or "unknown",
            "seller_reputation": seller_rep or 5.0,
            "title": mem.title,
            "category": mem.category,
            "tags": mem.tags or [],
            "summary": mem.summary,
            "content_preview": str(mem.content)[:200] if mem.content else "",
            "format_type": mem.format_type,
            "price": mem.price,
            "purchase_count": mem.purchase_count,
            "favorite_count": mem.favorite_count,
            "avg_score": mem.avg_score,
            "verification_score": mem.verification_score,
            "executability_score": 0,
            "created_at": mem.created_at.isoformat() if mem.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "search_type": "keyword_fallback",
    }
```

**关键改动**:
1. `base_stmt` 已经包含 `select(Memory, Agent.name, Agent.reputation_score).join(Agent, ...)` ，所以直接使用即可，不再循环查询
2. 如果 `base_stmt` 的列结构不是 `(Memory, name, reputation_score)`，需要确保 `search_memories` 函数中的 `base_stmt` 定义使用了正确的 JOIN 列

### 预估工时
- **1 小时**（含验证）

---

## P1-3: 缓存系统默认关闭

### 问题分析

**文件**: `app/core/config.py`

```python
CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "false").lower() == "true"
```

**影响**:
- 默认 `false`，意味着新部署环境下所有搜索都是全量 DB 查询
- 在 `main.py` 的 lifespan 中：`if settings.CACHE_ENABLED:` 只有开启时才初始化缓存
- 搜索缓存中间件 `SearchCacheMiddleware` 完全依赖 Redis，但默认不连接
- 新用户或测试环境很可能忘记配置，导致性能瓶颈

### 修复方案：分层缓存策略

#### 3.1 修改默认值为 `true`

```python
# app/core/config.py
CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
```

#### 3.2 添加本地内存缓存后备（Redis 不可用时）

```python
"""本地内存缓存 — Redis 不可用时的后备方案"""
import time
import threading
from typing import Any, Optional
from collections import OrderedDict


class LocalCache:
    """线程安全的 LRU 本地内存缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()
        self.max_size = max_size
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            value, expires_at = self._cache[key]
            if time.time() > expires_at:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)  # LRU
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)  # 淘汰最旧
            self._cache[key] = (value, time.time() + (ttl or self.default_ttl))

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def delete_pattern(self, pattern: str) -> int:
        """简易模式匹配删除"""
        import fnmatch
        with self._lock:
            keys_to_delete = [k for k in self._cache if fnmatch.fnmatch(k, pattern)]
            for k in keys_to_delete:
                del self._cache[k]
            return len(keys_to_delete)

    def clear(self):
        with self._lock:
            self._cache.clear()


# 全局单例
local_cache = LocalCache(max_size=2000, default_ttl=300)
```

#### 3.3 修改缓存中间件支持降级

```python
# 在 app/api/search_cache_middleware.py 的 initialize 方法中：

async def initialize(self):
    """初始化：优先 Redis，失败则用本地缓存"""
    try:
        self.redis = await get_redis_client()
        await self.redis.ping()
        self._use_local = False
        logger.info("Search cache: using Redis")
    except Exception as e:
        from app.cache.local_cache import local_cache
        self._local_cache = local_cache
        self._use_local = True
        logger.warning(f"Redis unavailable, falling back to local cache: {e}")
```

#### 3.4 推荐缓存策略配置

```python
# app/core/config.py 新增
CACHE_LOCAL_MAX_SIZE: int = int(os.getenv("CACHE_LOCAL_MAX_SIZE", "2000"))
CACHE_LOCAL_TTL: int = int(os.getenv("CACHE_LOCAL_TTL", "300"))  # 5分钟
CACHE_SEARCH_TTL: int = int(os.getenv("CACHE_SEARCH_TTL", "1800"))  # 搜索缓存30分钟
CACHE_MEMORY_DETAIL_TTL: int = int(os.getenv("CACHE_MEMORY_DETAIL_TTL", "600"))  # 详情缓存10分钟
```

### 预估工时
- **2 小时**（含本地缓存实现 + 降级逻辑 + 测试）

---

## P1-4: 数据库连接池未配置

### 问题分析

**文件**: `app/db/database.py`

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=_connect_args,
    pool_pre_ping=True,
)
```

**问题**:
1. **SQLite 不需要连接池**（`StaticPool` 才是正确选项），但 **PostgreSQL 需要**
2. 使用默认 `pool_size=5`、`max_overflow=10`，对 PostgreSQL 生产环境偏小
3. 无 `pool_timeout`、`pool_recycle` 配置，长时间空闲连接可能被数据库关闭
4. Neon/PostgreSQL 的 `statement_cache_size=0` 已配置，但其他 PGBouncer 兼容参数缺失

### 修复方案：根据数据库 URL 动态配置连接池

```python
"""数据库初始化 — 动态连接池配置"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.core.config import settings


def _build_engine_kwargs() -> dict:
    """根据数据库类型动态构建引擎参数"""
    kwargs = {
        "echo": settings.DEBUG,
        "pool_pre_ping": True,
    }

    if "sqlite" in settings.DATABASE_URL:
        # SQLite: 使用 StaticPool（单连接），避免多线程并发问题
        kwargs.update({
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        })
    elif "postgresql" in settings.DATABASE_URL:
        # PostgreSQL: 配置连接池
        kwargs.update({
            "pool_size": 10,               # 常驻连接数
            "max_overflow": 20,            # 突发连接数上限
            "pool_timeout": 30,            # 获取连接超时（秒）
            "pool_recycle": 1800,          # 连接回收时间（30分钟）
            "connect_args": {
                "statement_cache_size": 0,  # PGBouncer 兼容
                "prepared_statement_cache_size": 0,
            },
        })
    else:
        # 其他数据库（MySQL等）
        kwargs.update({
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        })

    return kwargs


engine = create_async_engine(settings.DATABASE_URL, **_build_engine_kwargs())
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """依赖注入：获取数据库会话"""
    async with async_session() as session:
        yield session


async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            from sqlalchemy import text
            await conn.execute(text("ALTER TABLE agents ADD COLUMN role VARCHAR(20) DEFAULT 'user'"))
        except Exception:
            pass
    print("✅ 数据库初始化完成")
```

### 预估工时
- **1 小时**

---

## P1-5: 审计日志签名未全面启用

### 问题分析

**相关文件**:
- `app/api/audit_signature_middleware.py` — 签名中间件
- `app/api/audit_middleware.py` — 审计日志写入
- `app/services/digital_signature_service.py` — 签名服务
- `app/services/key_management_service.py` — 密钥管理

**问题**:

1. **审计中间件不调用签名**：`audit_middleware.py` 中的 `_flush_queue` 和 `log_audit_event` 函数写入审计日志时，**没有调用** `sign_audit_log_before_commit`：
   ```python
   # audit_middleware.py 的 _async_flush_queue:
   for log_data in logs_to_write:
       await db.execute(insert(AuditLog).values(**log_data))
       # ❌ 缺少签名步骤！
   ```

2. **SQLAlchemy 事件监听器是空壳**：`setup_audit_signature_events` 注册了 `before_insert` 和 `load` 事件，但处理函数体都是空的（`pass`），并且 **从未被调用**：
   ```python
   @event.listens_for(AuditLog, "before_insert")
   def handle_before_insert(mapper, connection, target):
       pass  # ❌ 空实现！
   ```

3. **密钥可能未初始化**：`key_management_service.get_current_key_pair()` 如果密钥未生成，返回 `None`，签名被跳过但不报警

4. **验证未执行**：`verify_audit_log_after_load` 存在但从未被调用

### 修复方案

#### 5.1 在审计日志写入时强制签名

```python
# app/api/audit_middleware.py — 修改 _async_flush_queue

async def _async_flush_queue(self):
    """异步批量写入队列中的日志（带签名）"""
    from app.api.audit_signature_middleware import sign_audit_log_before_commit
    from app.core.config import settings

    if not self._write_queue:
        return

    logs_to_write = self._write_queue.copy()
    self._write_queue.clear()

    try:
        async for db in get_db():
            for log_data in logs_to_write:
                try:
                    # 创建 AuditLog 对象
                    audit_log = AuditLog(**log_data)
                    
                    # ✅ 签名（如果启用）
                    if settings.DIGITAL_SIGNATURE_ENABLED:
                        sign_audit_log_before_commit(db, audit_log)
                    
                    db.add(audit_log)
                except Exception as e:
                    print(f"Failed to write audit log: {e}")

            await db.commit()
            break
    except Exception as e:
        print(f"Failed to flush audit log queue: {e}")
```

#### 5.2 在 log_audit_event 中签名

```python
# app/api/audit_middleware.py — 修改 log_audit_event

async def log_audit_event(
    db: AsyncSession,
    # ... 参数不变 ...
) -> AuditLog:
    # ... 创建 audit_log 对象 ...
    
    db.add(audit_log)
    await db.flush()

    # ✅ 签名
    if settings.DIGITAL_SIGNATURE_ENABLED:
        sign_audit_log_before_commit(db, audit_log)

    return audit_log
```

#### 5.3 应用启动时初始化密钥

```python
# app/main.py — 在 lifespan 中添加

# 初始化审计签名密钥
if settings.DIGITAL_SIGNATURE_ENABLED:
    from app.services.key_management_service import key_management_service
    try:
        key_pair = key_management_service.get_current_key_pair()
        if key_pair is None:
            key_management_service.generate_key_pair()
            print("✅ 审计签名密钥已生成")
        else:
            print("✅ 审计签名密钥已加载")
    except Exception as e:
        print(f"⚠️ 审计签名密钥初始化失败: {e}")
```

#### 5.4 添加签名覆盖率监控

```python
# 在 health endpoint 或 admin endpoint 中添加签名覆盖率检查

async def get_signature_coverage(db: AsyncSession) -> dict:
    """检查审计日志签名覆盖率"""
    from sqlalchemy import text
    
    result = await db.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(signature) as signed,
            ROUND(COUNT(signature) * 100.0 / NULLIF(COUNT(*), 0), 2) as coverage_pct
        FROM audit_logs
        WHERE created_at > datetime('now', '-7 days')
    """))
    row = result.first()
    
    return {
        "total_logs_7d": row[0],
        "signed_logs_7d": row[1],
        "coverage_percent": row[2],
        "healthy": row[2] == 100.0 if row[0] > 0 else True,
    }
```

### 预估工时
- **2 小时**（含密钥初始化 + 签名集成 + 覆盖率检查）

---

## P1-6: memory_id 无格式验证

### 问题分析

**memory_id 的使用遍布 30+ 个文件**，均无格式验证：

```python
# tables.py
memory_id = Column(String(50), primary_key=True, default=lambda: gen_id("mem"))

# gen_id 函数生成格式: "mem_{12位hex}"，例如 "mem_a1b2c3d4e5f6"
```

**问题**:
1. API 端点接收 `memory_id` 时无验证，攻击者可注入任意字符串
2. 没有长度限制检查（虽然数据库字段是 `String(50)`，但 SQL 注入前不会报错）
3. 没有 `SELECT`/`INSERT`/`DROP` 等 SQL 关键词过滤
4. 所有使用 `memory_id` 的查询都是参数化查询（SQLAlchemy ORM），所以**实际 SQL 注入风险较低**，但：
   - 可能导致意外的查询行为
   - 路径遍历（如果 `memory_id` 用于文件路径）
   - 日志注入

**memory_id 格式规范**:
- 前缀: `mem_`
- 后缀: 12 位十六进制字符（`[0-9a-f]`）
- 总长度: 16 字符
- 正则: `^mem_[0-9a-f]{12}$`

其他 ID 格式：
| ID 类型 | 前缀 | 格式 | 正则 |
|---------|------|------|------|
| memory_id | `mem_` | `mem_` + 12 hex | `^mem_[0-9a-f]{12}$` |
| agent_id | `agent_` | `agent_` + 12 hex | `^agent_[0-9a-f]{12}$` |
| team_id | `team_` | `team_` + 12 hex | `^team_[0-9a-f]{12}$` |
| purchase_id | `pur_` | `pur_` + 12 hex | `^pur_[0-9a-f]{12}$` |

### 修复方案

#### 6.1 创建通用 ID 验证工具

```python
"""app/core/validators.py — ID 格式验证"""
import re
from typing import Optional
from fastapi import HTTPException

# ID 格式规范
ID_PATTERNS = {
    "memory": re.compile(r"^mem_[0-9a-f]{12}$"),
    "agent": re.compile(r"^agent_[0-9a-f]{12}$"),
    "team": re.compile(r"^team_[0-9a-f]{12}$"),
    "purchase": re.compile(r"^pur_[0-9a-f]{12}$"),
    "rating": re.compile(r"^rat_[0-9a-f]{12}$"),
    "verification": re.compile(r"^ver_[0-9a-f]{12}$"),
    "audit": re.compile(r"^audit_[0-9a-f]{12}$"),
    "version": re.compile(r"^ver_[0-9a-f]{12}$"),
}

# 通用 ID 模式（前缀_12位hex，总长 <= 50）
GENERAL_ID_PATTERN = re.compile(r"^[a-z]+_[0-9a-f]{6,20}$")

# 严格的 hex 前缀白名单
ALLOWED_PREFIXES = {"mem", "agent", "team", "pur", "rat", "ver", "audit",
                     "tx", "stats", "perm", "role", "pol", "pver", "patt",
                     "uprof", "fact", "ucont", "pchange", "abtest", "anom",
                     "alert", "rule", "exp", "inv", "tctx", "act", "pcache",
                     "paudit", "click", "search"}


def validate_id(
    value: str,
    id_type: Optional[str] = None,
    field_name: str = "id",
) -> str:
    """
    验证 ID 格式
    
    Args:
        value: 待验证的 ID 值
        id_type: ID 类型（memory/agent/team 等），如果为 None 则使用通用规则
        field_name: 字段名（用于错误消息）
    
    Returns:
        验证通过的 ID 值
    
    Raises:
        HTTPException: 格式不合法时抛出 400 错误
    """
    if not value or not isinstance(value, str):
        raise HTTPException(status_code=400, detail=f"{field_name} 不能为空")
    
    # 长度限制（数据库字段为 String(50)）
    if len(value) > 50:
        raise HTTPException(
            status_code=400, 
            detail=f"{field_name} 格式不合法：长度超过限制"
        )
    
    # 只允许安全字符
    if not re.match(r"^[a-z0-9_]+$", value):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} 格式不合法：只允许小写字母、数字和下划线"
        )
    
    # 前缀白名单检查
    prefix = value.split("_")[0] if "_" in value else ""
    if prefix not in ALLOWED_PREFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} 格式不合法：未知前缀 '{prefix}'"
        )
    
    # 特定类型严格验证
    if id_type and id_type in ID_PATTERNS:
        if not ID_PATTERNS[id_type].match(value):
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} 格式不合法：期望格式 {id_type}_xxxxxxxxxxxx"
            )
    
    return value


def validate_memory_id(memory_id: str) -> str:
    """验证 memory_id 格式"""
    return validate_id(memory_id, "memory", "memory_id")


def validate_agent_id(agent_id: str) -> str:
    """验证 agent_id 格式"""
    return validate_id(agent_id, "agent", "agent_id")


def validate_team_id(team_id: str) -> str:
    """验证 team_id 格式"""
    return validate_id(team_id, "team", "team_id")
```

#### 6.2 在 API 端点中使用验证

```python
# app/api/memories.py — 修改各端点

from app.core.validators import validate_memory_id

@router.get("/{memory_id}", response_model=MemoryDetail)
async def get_memory(
    memory_id: str,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """获取记忆详情（需要已购买）"""
    # ✅ 验证 memory_id 格式
    memory_id = validate_memory_id(memory_id)
    
    try:
        return await get_memory_detail(db, memory_id, current_agent.agent_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="未购买此记忆")
    except ValueError:
        raise HTTPException(status_code=404, detail="记忆不存在")


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update(
    memory_id: str,
    req: MemoryUpdate,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """更新记忆"""
    # ✅ 验证 memory_id 格式
    memory_id = validate_memory_id(memory_id)
    
    try:
        result = await update_memory(db, memory_id, current_agent.agent_id, req)
        if not result:
            raise HTTPException(status_code=404, detail="记忆不存在")
        return result
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权修改此记忆")
```

#### 6.3 在 Pydantic Schema 中添加验证

```python
# app/models/schemas.py — 在请求模型中添加 validator

from pydantic import field_validator
import re

class PurchaseRequest(BaseModel):
    memory_id: str
    
    @field_validator('memory_id')
    @classmethod
    def validate_memory_id(cls, v):
        if not re.match(r'^mem_[0-9a-f]{12}$', v):
            raise ValueError('memory_id 格式不合法')
        return v
```

### 预估工时
- **2 小时**（含验证器 + API 集成 + Schema 验证 + 测试）

---

## 总工时估算

| 问题 | 优先级 | 预估工时 | 风险等级 |
|------|--------|----------|----------|
| P1-1: 内存限流器 OOM | 🔴 Critical | 1.5h | 可被远程利用导致服务崩溃 |
| P1-2: N+1 查询 | 🔴 Critical | 1h | 高并发下数据库雪崩 |
| P1-3: 缓存默认关闭 | 🟡 High | 2h | 搜索性能差、DB 压力大 |
| P1-4: 连接池未配置 | 🟡 High | 1h | 连接泄漏、PostgreSQL 生产环境隐患 |
| P1-5: 审计签名未启用 | 🟡 High | 2h | 审计日志可被篡改、合规风险 |
| P1-6: memory_id 无验证 | 🟠 Medium | 2h | 潜在安全风险（SQL 注入风险低） |
| **合计** | | **9.5 小时** | |

## 建议修复顺序

1. **P1-1** (限流器) — 直接影响服务稳定性
2. **P1-4** (连接池) — 生产环境基础配置
3. **P1-2** (N+1 查询) — 性能瓶颈
4. **P1-3** (缓存) — 减轻数据库压力
5. **P1-5** (审计签名) — 安全合规
6. **P1-6** (ID 验证) — 纵深防御

---

## 附：架构建议

1. **限流中间件**: 考虑迁移到 Nginx 层限流（`limit_req_zone`），避免应用层内存压力
2. **缓存策略**: 引入多级缓存（L1: 进程内 LRU → L2: Redis），与 P1-3 修复一起实施
3. **审计签名**: 考虑使用 `@event.listens_for(AuditLog, "before_insert")` 做自动签名，避免遗漏
4. **ID 验证**: 作为 FastAPI 依赖注入（`Depends`），可在路由层面统一处理
