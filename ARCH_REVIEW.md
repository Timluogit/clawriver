# ClawRiver 架构审查报告

> 📅 2026-03-29 | 推理专家产出
> 
> 项目规模：~40k 行 Python 代码 | 35 张数据库表 | 28 个 APIRouter | 30+ 个 Service 模块

---

## 一、架构健康度总评

### 综合评分：5.5 / 10

| 维度 | 评分 | 说明 |
|------|------|------|
| 代码组织 | 6/10 | 分层合理但职责模糊 |
| 模块耦合 | 4/10 | 大量交叉依赖和循环引用 |
| 代码复用 | 3/10 | 严重的函数级重复 |
| 可维护性 | 5/10 | 双版本并存加剧混乱 |
| 可扩展性 | 6/10 | SQLite 瓶颈明确，但迁移路径已有准备 |

---

## 二、代码架构健康度

### 2.1 路由组织：混乱但可用

**现状**：
- `routes.py` (555行) 充当"超级路由"——同时包含直写端点 + 子路由聚合 + 业务逻辑
- `main.py` 中又注册了 16 个路由，路由前缀不统一（`/api/v1` vs `/api`）
- 使用 `__import__()` 动态加载可选模块（如 ab_tests, anomaly_detection），不够规范

**具体问题**：

```python
# routes.py 中的 wildcard import —— 极差的实践
from app.models.schemas import *
from app.services.agent_service import *
from app.services.memory_service_v2 import *
from app.services.capture_service import *
```

4 处 `import *` 导致命名空间污染，不知道哪些函数从哪里来。

```python
# 动态模块加载 —— 不规范
for _mod_name in ['cache_stats', 'search_analytics', 'ab_tests', ...]:
    try:
        _optional_modules[_mod_name] = __import__(f'app.api.{_mod_name}', fromlist=[_mod_name])
    except ImportError:
        pass
```

**建议**：
1. 将 `routes.py` 拆分为 `router_registry.py`（纯聚合）+ 按领域的路由文件
2. 统一路由前缀为 `/api/v1`
3. 用 FastAPI 的 `include_router` tags 和 prefix 机制，不要在文件内直写端点
4. 消除所有 `import *`，改为显式导入

### 2.2 Services 层：职责严重重叠

**核心问题：memory_service.py vs memory_service_v2.py 并存**

| 指标 | memory_service.py | memory_service_v2.py |
|------|-------------------|----------------------|
| 行数 | 1168 | 1200 |
| 核心函数 | upload_memory, search_memories, purchase_memory, rate_memory, verify_memory, update_memory, get_my_memories... | 完全相同的函数名，几乎相同的实现 |
| 依赖方 | hybrid_search.py, evaluation.py, capture_service.py | routes.py, memories.py, unified_search.py |

两个文件**同时被不同模块引用**，形成了"分裂的大脑"——同一功能有两套实现，行为可能不同步。

**重复函数清单**（完全重复定义的函数）：

| 函数 | 重复次数 |
|------|---------|
| `gen_id()` | 6 个文件 |
| `calc_executability_score()` | 2 个文件 |
| `get_agent_level()` | 3 个文件 |
| `_calc_verification_score()` | 3 个文件 |
| `upload_memory()` | 2 个文件 |
| `search_memories()` | 2 个文件 |
| `purchase_memory()` | 2 个文件 |
| `rate_memory()` | 2 个文件 |
| `verify_memory()` | 2 个文件 |
| `update_memory()` | 2 个文件 |
| `get_memory_detail()` | 2 个文件 |
| `get_my_memories()` | 2 个文件 |
| `create_memory_version()` | 2 个文件 |
| `_update_platform_stats()` | 2 个文件 |

**其他职责过重的模块**：

- `policy_service.py` (1256行) — IAM 策略引擎 + 策略 CRUD + 策略评估，三个职责应拆分
- `team_service.py` (642行) — 团队 CRUD + 团队记忆 + 团队积分 + 团队邀请
- `anomaly_rules.py` (692行) — 规则定义 + 规则评估 + 告警触发

### 2.3 模块间耦合度

**59 处 services 间交叉引用**，形成复杂依赖网：

```
memory_service_v2 → hybrid_search → memory_service (循环!)
capture_service → memory_service
memory_service_v2_team → memory_service_v2
purchase_service_v2 → memory_service_v2
```

最严重的：`hybrid_search.py` 内部 `from app.services.memory_service import _execute_search`，而 `memory_service_v2.py` 内部 `from app.search.hybrid_search import get_hybrid_engine`，形成**循环依赖**。

### 2.4 表模型膨胀

`tables.py` 单文件 1303 行，35 张表全部堆在一起，涵盖：
- 核心业务（Agent, Memory, Purchase, Rating）
- 团队系统（Team, TeamMember, TeamInviteCode, TeamCreditTransaction, TeamActivityLog）
- 权限系统（Permission, Role, RolePermission, UserPermission, ResourcePermission, PermissionCache, PermissionAuditLog, PermissionPolicy, PolicyVersion, PolicyAttachment）
- 用户画像（UserProfile, ProfileFact, UserDynamicContext, ProfileChange）
- 审计/监控（AuditLog, AuditLogExport, SearchLog, SearchClick, SearchABTest）
- 异常检测（AnomalyEvent, AnomalyAlert, AnomalyRule）

**建议拆分为**：`models/core.py`、`models/team.py`、`models/permission.py`、`models/profile.py`、`models/audit.py`、`models/anomaly.py`

---

## 三、可扩展性分析

### 3.1 并发能力估算

**当前架构（SQLite + 单进程 uvicorn）**：
- 理论并发：~50-100 QPS（读写混合），纯读 ~200 QPS
- SQLite 写入锁：同一时刻只能有一个写事务
- 实际支撑用户量：~100-500 DAU

**瓶颈链**：
```
Request → RateLimitMiddleware → AuditMiddleware → AntiCrawlerMiddleware
→ Route Handler → Service Layer → SQLite (写入锁等待) → Response
```

每个写请求（上传、购买、评价）都要等 SQLite 的 WAL 锁。高并发下写入成为瓶颈。

### 3.2 SQLite 瓶颈具体位置

| 瓶颈点 | 影响 |
|--------|------|
| 单文件写入锁 | 写入串行化，并发写入等待 |
| 无连接池管理 | aiosqlite 连接数有限 |
| 全表扫描 | `search_memories` 在无索引的 JSON 字段上做 LIKE 查询 |
| 内存索引 | `InMemoryHybridEngine` 需要全量加载，重启后冷启动慢 |
| 向量化线程 | `_vectorize_memory_async` 用 threading.Thread，无并发控制 |

### 3.3 迁移到 PostgreSQL 的工作量评估

**好消息**：项目已经做了部分准备：
```python
# database.py 已支持 PostgreSQL
if "postgresql" in settings.DATABASE_URL:
    _connect_args = {"statement_cache_size": 0}  # 兼容 Neon
```

**迁移清单**：

| 工作项 | 工作量 | 风险 |
|--------|--------|------|
| 替换 `sqlite+aiosqlite` 为 `postgresql+asyncpg` | 0.5天 | 低 |
| SQL 兼容性检查（SQLite 特有语法） | 1天 | 中 |
| JSON 字段查询差异 | 0.5天 | 低 |
| 连接池配置优化 | 0.5天 | 低 |
| 全文搜索替换（FTS5 → pg_trgm/tsvector） | 2天 | 中 |
| 迁移脚本和测试 | 1天 | 中 |
| **总计** | **~5.5天** | **中** |

**关键风险点**：
1. SQLite 的 `ILIKE` 行为与 PostgreSQL 不同
2. JSON 字段查询语法差异（`Memory.content` 是 JSON 列）
3. 内存索引需要重建

---

## 四、技术债清单

### 🔴 P0 — 必须立即修复

| # | 问题 | 影响 | 修复成本 |
|---|------|------|---------|
| 1 | **双版本 memory_service 并存** | 行为不一致，维护成本翻倍 | 2天（合并+测试） |
| 2 | **6 处重复 gen_id()** | ID 生成逻辑分散 | 0.5天 |
| 3 | **import * 通配符导入** | 命名冲突风险，不可追踪 | 0.5天 |
| 4 | **循环依赖** (hybrid_search ↔ memory_service) | 启动顺序敏感，重构困难 | 1天 |

### 🟡 P1 — 一个月内修复

| # | 问题 | 影响 | 修复成本 |
|---|------|------|---------|
| 5 | 路由前缀不统一 (`/api` vs `/api/v1`) | 客户端混淆 | 1天 |
| 6 | `tables.py` 1303行单文件 | 可维护性差 | 1天 |
| 7 | `routes.py` 混合路由注册和业务逻辑 | 职责不清 | 1天 |
| 8 | Settings 类 100+ 配置项无分组 | 配置混乱 | 1天 |
| 9 | 无数据库迁移工具（手动 ALTER TABLE） | schema 变更不可追踪 | 1天（引入 Alembic） |
| 10 | lifespan 中大量 try/except 吞异常 | 启动问题难排查 | 0.5天 |

### 🟢 P2 — 技术优化

| # | 问题 | 影响 | 修复成本 |
|---|------|------|---------|
| 11 | `_vectorize_memory_async` 用裸 threading.Thread | 无并发控制，无错误传播 | 1天（改用 BackgroundTasks 或 asyncio） |
| 12 | 无 typed Dict/Pydantic model 用于 service 层返回 | 类型安全差 | 2天 |
| 13 | 硬编码的字符串常量（角色、权限类型等） | 拼写错误无编译检查 | 1天（改用 Enum） |
| 14 | 日志使用 print() 而非 logging | 生产环境不可控 | 1天 |
| 15 | 无依赖注入框架，直接导入全局单例 | 测试困难 | 2天 |

### 过时/问题依赖

| 依赖 | 问题 |
|------|------|
| `torch>=2.0.0` | 生产环境极重（~2GB），应作为可选依赖 |
| `sentence-transformers>=2.7.0` | 同上，推理部署不必要 |
| `pydantic==2.9.0` | 固定版本，可能有安全修复未更新 |
| `python-jose` | 维护不活跃，建议迁移到 PyJWT |
| `passlib[bcrypt]` | bcrypt 有更好的替代（argon2） |

---

## 五、竞品对比分析

### 5.1 ClawRiver vs mem0 (51k⭐)

| 维度 | ClawRiver | mem0 |
|------|-----------|------|
| **定位** | Agent 经验共享市场 | AI 通用记忆层 |
| **核心模型** | 市场交易（买卖/评价） | 个人记忆管理（增删查改） |
| **记忆类型** | 结构化知识（模板/策略/案例） | 非结构化偏好/事实 |
| **搜索** | 混合搜索（关键词+语义+重排） | 向量搜索 + LLM 提取 |
| **MCP** | ✅ 原生支持 | ❌ 无 MCP |
| **多用户** | ✅ 团队协作 + 权限系统 | ✅ 用户隔离 |
| **部署复杂度** | 单容器 512MB | 需向量数据库 |
| **开源协议** | MIT | MIT |
| **SDK** | HTTP API + MCP | Python SDK + REST API + JS SDK |
| **嵌入式模型** | 本地 bge-small-zh | 远程 API（gpt-4o 等） |
| **向量存储** | Qdrant（可选）/ 内存 | Qdrant/Chroma/PG 等多种 |
| **Star 数** | ~10 | 51k |

**mem0 架构优势**：
- 清晰的抽象层：Memory → VectorStore → LLM
- 多种向量存储后端（可插拔）
- 有 managed service 选项（SaaS）
- 有学术论文和 LOCOMO benchmark 验证

**mem0 不擅长而 ClawRiver 擅长的**：
- Agent 间的知识共享（mem0 只做单用户记忆）
- MCP 协议原生支持
- 知识可执行度评分（executability score）
- 团队协作和权限管理
- 轻量部署（无需向量数据库也能工作）

### 5.2 ClawRiver vs LangSmith

| 维度 | ClawRiver | LangSmith |
|------|-----------|-----------|
| **定位** | 知识共享市场 | LLM 应用观测平台 |
| **核心功能** | 搜索/交易/评价知识 | Trace/Debug/Evaluate LLM 调用 |
| **目标用户** | Agent 开发者 | LLM 应用开发者 |
| **重合度** | 低（不同赛道） | — |

LangSmith 是 LLM 可观测性工具，与 ClawRiver 不是直接竞品。但从"AI 基础设施"角度看，LangSmith 的 evaluation 功能与 ClawRiver 的评估框架有少量重合。

### 5.3 差异化分析

**ClawRiver 的独特优势**：

1. **Agent 经济模型** — 知识市场 + 星尘积分 + 随缘打赏，这是其他工具没有的
2. **MCP 原生** — Agent 生态的"App Store"，天然适配 OpenClaw/Claude Code 等工具
3. **知识可执行度** — 不只存内容，还评估 Agent 能不能直接用
4. **零外部依赖模式** — 内存搜索 + SQLite，512MB 即可运行
5. **团队协作** — 多 Agent 共享知识资源

**ClawRiver 的劣势**：

1. **用户基数** — mem0 有 51k star 和 YC 背书，ClawRiver 才起步
2. **SDK 生态** — mem0 有 Python + JS SDK，ClawRiver 只有 HTTP API
3. **学术验证** — mem0 有 LOCOMO benchmark 论文，ClawRiver 无
4. **通用性** — mem0 适用于任何 AI 记忆场景，ClawRiver 聚焦 Agent 经验
5. **代码质量** — mem0 代码架构清晰，ClawRiver 技术债较重

---

## 六、改进优先级与路线图

### Phase 1: 紧急止血（1-2 周）

```
优先级：🔴 P0
目标：消除最大的技术债，为后续扩展扫清障碍
```

| 任务 | 工时 | 负责 |
|------|------|------|
| 合并 memory_service.py 和 memory_service_v2.py | 2天 | — |
| 消除 gen_id() 重复（提取到 utils） | 0.5天 | — |
| 消除 import *，改为显式导入 | 0.5天 | — |
| 解除 hybrid_search ↔ memory_service 循环依赖 | 1天 | — |
| 引入 Alembic 数据库迁移 | 1天 | — |

### Phase 2: 架构清理（3-4 周）

```
优先级：🟡 P1
目标：模块化、可测试、可维护
```

| 任务 | 工时 | 负责 |
|------|------|------|
| 拆分 tables.py 为多个模型文件 | 1天 | — |
| 重构路由：统一前缀 + 拆分 routes.py | 2天 | — |
| Settings 分组（DatabaseConfig, CacheConfig 等） | 1天 | — |
| 引入 logging 替代 print() | 1天 | — |
| 字符串常量改为 Enum | 1天 | — |
| 编写核心模块单元测试 | 3天 | — |

### Phase 3: 数据库迁移（2-3 周）

```
优先级：🟡 P1
目标：生产级数据库，支撑更大规模
```

| 任务 | 工时 | 负责 |
|------|------|------|
| PostgreSQL 迁移 + Alembic | 3天 | — |
| 引入 pgvector 替代内存向量搜索 | 2天 | — |
| 连接池优化 | 1天 | — |
| 搜索性能测试和优化 | 2天 | — |

### Phase 4: 生态建设（1-2 月）

```
优先级：🟢 P2
目标：SDK、文档、社区
```

| 任务 | 工时 | 负责 |
|------|------|------|
| Python SDK 包（pip install clawriver） | 5天 | — |
| JavaScript SDK | 5天 | — |
| API 文档完善 + 示例 | 3天 | — |
| Benchmark 评估报告（vs mem0） | 3天 | — |
| CI/CD pipeline | 2天 | — |

### 路线图可视化

```
2026 Q2:
  Week 1-2:  Phase 1 (紧急止血)
  Week 3-6:  Phase 2 (架构清理)
  Week 7-9:  Phase 3 (数据库迁移)

2026 Q3:
  Week 1-8:  Phase 4 (生态建设)
```

---

## 七、总结

### 核心判断

ClawRiver 的**产品定位是独特的**——Agent 经验共享市场 + MCP 原生 + 知识可执行度评分，这在当前市场上有明确的差异化空间。mem0 做的是"AI 的记忆"，ClawRiver 做的是"Agent 之间共享经验"——两者互补而非竞争。

但**代码架构是最大风险**。双版本 service 并存、循环依赖、import * 等问题使得每次功能变更都像在拆弹。如果不先解决技术债，项目将越来越难迭代。

### 一句话建议

> **先还债，再加速。用 2 周做 Phase 1 止血，否则后面每走一步都是泥潭。**
