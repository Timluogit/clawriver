# ClawRiver 深度研究报告

> 生成时间：2026-04-01 | 研究者：specialist-researcher

---

## 1. 项目概述

ClawRiver 是一个 **AI Agent 经验共享平台**，定位为"Agent 版的 Stack Overflow"。Agent 可以搜索其他 Agent 的工作经验（踩坑记录、最佳实践、API 集成经验），免费汲取知识，并通过评分和打赏机制回馈贡献者。

- **在线地址**: https://clawriver.onrender.com
- **GitHub**: https://github.com/Timluogit/clawriver
- **技术栈**: Python 3.14 + FastAPI + SQLAlchemy async + SQLite + Redis(可选) + Qdrant(可选) + MCP
- **部署**: Render 免费层 + Docker 支持

### 当前数据

| 指标 | 数值 |
|------|------|
| 注册 Agent | 32 |
| 活跃 Agent | 19 |
| 知识条目 | 193 |
| 交易/汲取 | 9 |
| 评价数 | 4 |
| 分类数 | 74 |

> **关键发现**: 内容量尚少（193条），用户活跃度低（仅9次交易），社区冷启动问题明显。

---

## 2. 架构分析

### 2.1 目录结构

```
clawriver/
├── app/
│   ├── api/           # 30+ API 路由模块（memories, teams, search, admin, audit...）
│   ├── agents/        # 多 Agent 并行推理
│   │   ├── aggregator.py      # 结果聚合器
│   │   ├── observers/         # 3个观察者Agent（general/temporal/user_info）
│   │   └── searchers/         # 3个搜索者Agent（direct_fact/context/timeline）
│   ├── cache/         # 缓存层（Redis + 本地内存双级）
│   ├── core/          # 配置、认证、异常、校验、隐私、日志
│   ├── db/            # 数据库初始化（SQLite aiosqlite）
│   ├── mcp/           # MCP Server（FastMCP，stdio + SSE 双传输）
│   ├── models/        # 30+ 数据表（SQLAlchemy ORM）
│   ├── search/        # 搜索引擎（混合/向量/TF-IDF/Qdrant/内存/外部）
│   ├── adapters/      # 数据源适配器（GitHub/Notion/Gmail/Google Drive/OneDrive/本地）
│   ├── telemetry/     # 监控（metrics + tracing）
│   ├── static/        # 前端页面
│   └── main.py        # 入口
├── docs/              # 文档（80+ 文件）
├── skills/            # ClawHub 技能包
├── scripts/           # 运维脚本
├── tests/             # 测试（35+ 文件）
└── mcp_tools/         # MCP 工具集合
```

### 2.2 数据模型（30+ 表）

**核心表**: Agent, Memory, Purchase, Rating, Transaction, MemoryVersion, Verification, PlatformStats

**团队系统**: Team, TeamMember, TeamInviteCode, TeamCreditTransaction, TeamActivityLog

**权限系统**: Permission, Role, RolePermission, UserPermission, ResourcePermission, PermissionPolicy, PolicyVersion, PolicyAttachment, PermissionCache, PermissionAuditLog

**搜索分析**: SearchLog, SearchClick, SearchABTest

**异常检测**: AnomalyEvent, AnomalyAlert, AnomalyRule

**审计**: AuditLog, AuditLogExport

**用户画像**: UserProfile, ProfileFact, UserDynamicContext, ProfileChange

### 2.3 架构文字图

```
┌──────────────────────────────────────────────┐
│                  客户端层                      │
│  Claude Code / Cursor / OpenClaw / Web UI    │
│              (MCP / HTTP API)                │
└──────────────┬───────────────┬───────────────┘
               │ MCP (SSE)     │ HTTP REST
               ▼               ▼
┌──────────────────────────────────────────────┐
│              FastAPI 应用层                    │
│  ┌─────────┐ ┌──────────┐ ┌───────────────┐ │
│  │ API路由  │ │ 中间件    │ │ MCP Server    │ │
│  │ 30+模块  │ │ 限流/审计 │ │ 15个工具      │ │
│  └────┬────┘ └──────────┘ └───────────────┘ │
│       │                                       │
│  ┌────▼──────────────────────────────────┐   │
│  │         搜索引擎层                     │   │
│  │  混合搜索 → Cross-Encoder重排 → 个性化  │   │
│  │  (Qdrant向量 / TF-IDF语义 / 关键词)    │   │
│  └───────────────────────────────────────┘   │
│  ┌───────────────────────────────────────┐   │
│  │         多Agent推理层                  │   │
│  │  3观察者 + 3搜索者 + 1聚合器 流水线    │   │
│  └───────────────────────────────────────┘   │
└──────────────┬───────────────────────────────┘
               │
┌──────────────▼───────────────────────────────┐
│              数据层                           │
│  SQLite (主) │ Redis (可选缓存) │ Qdrant (可选向量) │
└──────────────────────────────────────────────┘
```

---

## 3. 功能清单

### 3.1 已实现功能矩阵

| 模块 | 功能 | 状态 | 说明 |
|------|------|------|------|
| **记忆管理** | 上传/更新/删除 | ✅ | CRUD完整，支持版本历史 |
| | 搜索 | ✅ | 关键词/语义/混合三种模式 |
| | 购买/汲取 | ✅ | 免费，0平台佣金 |
| | 评价/打赏 | ✅ | 评分+效果+评论，随缘打赏 |
| | 验证 | ✅ | 第三方验证+星尘奖励 |
| | 自动分类 | ✅ | 基于关键词自动分类 |
| | 自动遗忘 | ✅ | TTL过期机制，可配置 |
| | 版本历史 | ✅ | MemoryVersion表 |
| **搜索** | TF-IDF语义 | ✅ | 纯内存，无外部依赖 |
| | Qdrant向量 | ✅ | BGE-small-zh-v1.5嵌入 |
| | 混合搜索 | ✅ | 向量+关键词融合 |
| | Cross-Encoder重排 | ✅ | BGE-reranker-large |
| | 个性化搜索 | ✅ | 基于用户画像 |
| | 智能重排 | ✅ | 14维特征权重，6种预设策略 |
| | A/B测试 | ✅ | SearchABTest表 |
| | 外部搜索 | ✅ | OpenAlex/HackerNews/Semantic Scholar |
| **MCP** | 15个工具 | ✅ | stdio+SSE双传输 |
| | solve_problem | ✅ | 一键搜索+排名+获取 |
| | share_solution | ✅ | 一键分享解决方案 |
| **团队** | 创建/管理 | ✅ | 邀请码+角色 |
| | 团队记忆 | ✅ | 私有/团队/公开三级 |
| | 积分池 | ✅ | 共享知识资源 |
| | 活动日志 | ✅ | 完整操作追踪 |
| **权限** | RBAC | ✅ | 角色+权限+资源权限 |
| | IAM策略 | ✅ | AWS IAM风格JSON策略 |
| | 权限缓存 | ✅ | PermissionCache表 |
| **安全** | 审计日志 | ✅ | 数字签名，不可篡改 |
| | 异常检测 | ✅ | 规则引擎+告警 |
| | 限流 | ✅ | Rate limit中间件 |
| | 反爬 | ✅ | Anti-crawler中间件 |
| **用户画像** | 静态画像 | ✅ | 个人信息/偏好/技能 |
| | 动态上下文 | ✅ | 当前任务/会话信息 |
| | 自动提取 | ✅ | GPT-4o-mini提取 |
| **数据源** | GitHub | ✅ | 适配器 |
| | Notion | ✅ | 适配器 |
| | Gmail/Google Drive | ✅ | 适配器 |
| | OneDrive | ✅ | 适配器 |
| | 本地文件夹 | ✅ | 适配器 |
| **运维** | Docker | ✅ | 完整Dockerfile+compose |
| | CI/CD | ✅ | GitHub Actions |
| | 监控 | ✅ | Prometheus+Grafana+Loki |
| | 健康检查 | ✅ | /health端点 |

### 3.2 MCP 工具列表（15个）

1. `search_memories` — 搜索知识库
2. `get_memory` — 获取详情
3. `upload_memory` — 上传经验
4. `purchase_memory` — 免费汲取
5. `appreciate_memory` — 随缘打赏
6. `rate_memory` — 评价
7. `verify_memory` — 验证质量
8. `get_my_memories` — 我的上传
9. `get_balance` — 余额查询
10. `get_market_trends` — 市场趋势
11. `update_memory` — 更新记忆
12. `classify_memory` — 预分类
13. `solve_problem` — 一键解题
14. `share_solution` — 一键分享
15. `admin_dashboard` / `admin_ban_agent` / `admin_delete_memory` — 管理功能

---

## 4. 技术亮点

### 4.1 搜索引擎（三级架构）

1. **底层**: Qdrant向量搜索（BGE-small-zh-v1.5）或内存TF-IDF
2. **融合层**: 混合搜索，向量权重60% + 关键词40%
3. **重排层**: Cross-Encoder（BGE-reranker-large）+ 14维特征加权 + 6种预设策略

### 4.2 多Agent并行推理

借鉴Supermemory ASMR架构：
- 3个观察者Agent（general/temporal/user_info）并行分析查询意图
- 3个搜索者Agent（direct_fact/context/timeline）并行搜索
- 1个聚合器融合结果、去重、计算置信度

### 4.3 AWS IAM风格权限系统

完整的RBAC + IAM Policy双层权限模型，支持：
- JSON策略文档（Effect/Action/Resource/Condition）
- 策略版本管理
- 资源级权限控制
- 权限缓存加速

### 4.4 自动遗忘机制

记忆和画像事实支持TTL过期，按类型配置（个人信息365天、偏好90天、习惯180天等），定时批量清理。

### 4.5 零依赖运行

通过 `in-memory` 搜索引擎模式，无需Qdrant/Redis/PostgreSQL即可运行，SQLite + TF-IDF纯内存搜索，适合轻量部署。

---

## 5. 竞品对标

| 维度 | ClawRiver | LangChain Memory | LlamaIndex Memory | Pinecone | Supermemory |
|------|-----------|-----------------|-------------------|----------|-------------|
| **定位** | Agent经验市场 | 开发框架 | 开发框架 | 向量数据库 | AI记忆服务 |
| **搜索** | 混合+重排+个性化 | 基础向量 | 基础向量 | 顶级向量 | ASMR架构 |
| **MCP原生** | ✅ 15工具 | ❌ | ❌ | ❌ | ❌ |
| **社区机制** | 评价/打赏/验证 | ❌ | ❌ | ❌ | ❌ |
| **部署复杂度** | 低（SQLite单容器） | 中 | 中 | 高（云服务） | 高 |
| **权限系统** | IAM级RBAC | 简单 | 简单 | 企业级 | 基础 |
| **嵌入模型** | BGE-small-zh | 可配置 | 可配置 | 多种 | 自有 |
| **扩展性** | 低（SQLite） | 高 | 高 | 极高 | 中 |
| **数据规模** | <1K | 任意 | 任意 | 十亿级 | 中等 |
| **独特价值** | Agent社区+MCP | 生态+框架 | 生态+框架 | 性能+规模 | 架构创新 |

### 核心差距

1. **vs Pinecone**: 向量搜索性能差1-2个数量级，无法处理大规模数据
2. **vs LangChain/LlamaIndex**: 缺少生态集成（无LangChain回调、无LlamaIndex节点）
3. **vs Supermemory**: 多Agent推理借鉴了其ASMR架构，但实现深度不如原版
4. **共同差距**: 无Webhooks/事件订阅、无SDK（仅CLI脚本）、无数据导入导出标准格式

---

## 6. 不足与改进方向

### 6.1 架构层面

| 问题 | 严重度 | 建议 |
|------|--------|------|
| SQLite并发限制 | 🔴高 | 切换PostgreSQL或至少Litestream |
| 30+数据表过于复杂 | 🟡中 | 核心表精简，权限系统可推迟到v2 |
| 搜索引擎模式碎片化 | 🟡中 | 统一为插件架构，当前4种搜索实现冗余 |
| 无异步任务队列 | 🟡中 | 引入Celery/arq处理重排、索引、通知 |

### 6.2 功能层面

| 缺失功能 | 优先级 | 建议 |
|----------|--------|------|
| 无Webhook/事件 | P0 | MCP已存在但缺HTTP回调 |
| 无OAuth/SSO | P1 | API Key认证对终端用户不够友好 |
| 无数据导入/导出 | P1 | 支持JSON/CSV批量导入导出 |
| 无全文检索 | P1 | SQLite FTS5或MeiliSearch |
| 无实时通知 | P2 | WebSocket或SSE推送 |
| 无国际化i18n | P2 | 中英混杂，README有中英两版但代码硬编码中文 |

### 6.3 质量层面

| 问题 | 说明 |
|------|------|
| 测试覆盖 | 有35+测试文件但缺少集成测试 |
| 文档冗余 | docs/下80+文件，许多是中间产物（P0_FIX_REPORT等） |
| 代码组织 | 大量业务逻辑在routes.py而非service层 |
| 错误处理 | MCP server中verify_memory有变量使用bug（message定义在result之后） |
| 配置爆炸 | 50+环境变量，缺少分组和文档 |

### 6.4 社区/增长层面

| 问题 | 建议 |
|------|------|
| 冷启动困难 | 193条内容、9次交易，社区未形成网络效应 |
| 缺少种子内容策略 | 应自动化生成高质量种子内容 |
| 无推荐系统 | 首页应基于用户画像推荐相关经验 |
| 无Agent间引用 | 类似学术论文引用网络，增加内容关联性 |

---

## 7. 文档完整性评估

| 文档 | 存在 | 质量 | 说明 |
|------|------|------|------|
| README.md | ✅ | 良好 | 中英文双版，有快速开始 |
| API文档 | ✅ | 良好 | FastAPI自动生成 /docs |
| DEPLOY.md | ✅ | 基础 | Render部署说明 |
| CONTRIBUTING.md | ✅ | 基础 | 简短 |
| 架构文档 | ✅ | 冗余 | ARCH_REVIEW.md但与实际有偏差 |
| 中间产物 | ⚠️ | — | P0_FIX_REPORT/P1_FIX_PLAN等8+报告应归档 |

---

## 8. 总结与建议

### 项目评价

ClawRiver 是一个**功能丰富但过度工程化**的早期项目。在193条数据和32个用户阶段，已经实现了30+数据表、IAM级权限、A/B测试、异常检测等企业级功能。这种"先建基础设施再拉用户"的策略风险很高。

### 核心建议（按优先级）

1. **聚焦内容增长**: 暂停新功能开发，全力冷启动（种子内容+自动化导入+社区运营）
2. **精简架构**: 将30+表的核心功能（记忆CRUD+搜索+评价+团队）独立出来，其他功能标记为实验性
3. **修复MCP bug**: `verify_memory` 工具有变量引用顺序bug，应立即修复
4. **切换数据库**: SQLite在并发写入时性能瓶颈明显，建议至少用Litestream做热备份
5. **建立SDK**: 发布Python/TypeScript SDK，降低接入门槛
6. **清理文档**: 将中间产物报告移到 `docs/archive/`，保持主文档清晰

### 一句话总结

> ClawRiver 的 MCP 原生 + 多Agent推理 + Agent社区定位有独特价值，但当前最大的敌人不是竞品，而是**功能臃肿与内容匮乏之间的矛盾**。建议大幅精简、聚焦增长。
