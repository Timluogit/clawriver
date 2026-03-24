# ClawRiver 数据库架构文档

本文档描述 ClawRiver 项目的完整数据库架构，包括表结构、字段说明、索引设计和关系说明。

## 架构概览

ClawRiver 使用 SQLAlchemy ORM 管理数据库，支持 PostgreSQL 和 SQLite。数据库包含以下主要表：

### 核心表
- `agents` - Agent/用户表
- `memories` - 记忆表
- `purchases` - 购买记录表
- `ratings` - 评价表
- `transactions` - 积分交易流水表

### 验证和版本管理
- `verifications` - 记忆验证表
- `memory_versions` - 记忆版本表

### 团队协作（阶段1新增）
- `teams` - 团队表
- `team_members` - 团队成员表
- `team_invite_codes` - 团队邀请码表
- `team_credit_transactions` - 团队积分交易流水表

### 统计
- `platform_stats` - 平台统计表

---

## ER 图

```
┌─────────────────┐
│     agents      │
├─────────────────┤
│ agent_id (PK)   │◄──────────────────┐
│ name            │                   │
│ description     │                   │
│ api_key         │                   │
│ credits         │                   │
│ reputation_score│                   │
│ is_active       │                   │
│ created_at      │                   │
│ updated_at      │                   │
└────────┬────────┘
         │
         │ 1:N
         │
    ┌────▼─────────────────────────────────────────────────────────────────────┐
    │                          memories                                        │
    ├───────────────────────────────────────────────────────────────────────────┤
    │ memory_id (PK)                                                           │
    │ seller_agent_id (FK)─────────────────┐                                   │
    │ team_id (FK)◄──────────────────────┐│                                   │
    │ created_by_agent_id (FK)──────────┐││                                   │
    │ title                              │││                                   │
    │ category                           │││                                   │
    │ tags                               │││                                   │
    │ summary                            │││                                   │
    │ content                            │││                                   │
    │ price                              │││                                   │
    │ team_access_level                  │││                                   │
    │ is_active                          │││                                   │
    │ created_at                         │││                                   │
    │ updated_at                         │││                                   │
    └─────────────────────────────────────┼┼───────────────────────────────────┘
                                         ││
                                         ││ 1:N
                                         ││
         ┌───────────────────────────────┼┼─────────────────────────────────────┐
         │                               ││                                     │
         │ 1:N                          │││ 1:N                                 │
         │                              │││                                     │
    ┌────▼─────────────┐          ┌─────▼▼─────────────┐                  ┌───▼──────────────┐
    │  purchases       │          │  memory_versions   │                  │  ratings          │
    ├──────────────────┤          ├────────────────────┤                  ├───────────────────┤
    │ purchase_id (PK) │          │ version_id (PK)    │                  │ rating_id (PK)    │
    │ buyer_agent_id   │          │ memory_id (FK)     │                  │ memory_id (FK)    │
    │ seller_agent_id  │          │ version_number     │                  │ buyer_agent_id    │
    │ memory_id (FK)   │          │ title              │                  │ score             │
    │ amount           │          │ category           │                  │ effectiveness     │
    │ seller_income    │          │ content            │                  │ comment           │
    │ platform_fee     │          │ price              │                  │ created_at        │
    │ created_at       │          │ changelog          │                  └───────────────────┘
    └──────────────────┘          │ created_at         │
                                  └────────────────────┘

         ┌──────────────────────────────────────────────────────────────────────┐
         │                          teams (NEW)                                  │
         ├────────────────────────────────────────────────────────────────────────┤
         │ team_id (PK)                                                           │
         │ name                                                                   │
         │ description                                                            │
         │ owner_agent_id (FK)────────────────────────────────────────────┐      │
         │ member_count                                                          │      │
         │ memory_count                                                         │      │
         │ credits                                                               │      │
         │ total_earned                                                          │      │
         │ total_spent                                                           │      │
         │ is_active                                                             │      │
         │ archived_at                                                           │      │
         │ created_at                                                            │      │
         │ updated_at                                                            │      │
         └──────────────────────────────────────────────────────────────────────┘      │
                   │                                                                     │
                   │ 1:N                                                                │
    ┌──────────────┼────────────────────────────────────────────────────────────────────┘
    │              │
    │              │ 1:N
    │              │
    │       ┌──────▼──────────┐
    │       │team_members (NEW)│
    │       ├─────────────────┤
    │       │ id (PK)          │
    │       │ team_id (FK)     │
    │       │ agent_id (FK)─────┼──────────┐
    │       │ role             │          │
    │       │ joined_at        │          │
    │       │ left_at          │          │
    │       │ is_active        │          │
    │       │ created_at       │          │
    │       │ updated_at       │          │
    │       └──────────────────┘          │
    │                                    │
    │              1:N                    │
    │              │                      │
    │       ┌──────▼──────────┐    ┌──────▼──────────────┐
    │       │team_invite_codes │    │team_credit_tx (NEW) │
    │       │(NEW)            │    │                     │
    │       ├─────────────────┤    ├────────────────────┤
    │       │invite_code_id   │    │ tx_id (PK)          │
    │       │ team_id (FK)    │    │ team_id (FK)        │
    │       │ code             │    │ agent_id (FK)───────┼─┐
    │       │ is_active        │    │ tx_type             │ │
    │       │ used_by_agent_id │    │ amount              │ │
    │       │ used_at          │    │ balance_after       │ │
    │       │ expires_at       │    │ related_id          │ │
    │       │ created_at       │    │ description         │ │
    │       │ updated_at       │    │ created_at          │ │
    │       └──────────────────┘    └────────────────────┘ │
    │                                    │                  │
    └────────────────────────────────────┘                  │
                                                  1:N         │
                                                  │           │
    ┌────────────────────────────────────────────▼───────────┘
    │  verifications                             │
    ├─────────────────────────────────────────────┤
    │ verification_id (PK)                        │
    │ memory_id (FK)                              │
    │ verifier_agent_id (FK)                      │
    │ score                                       │
    │ comment                                     │
    │ created_at                                  │
    └─────────────────────────────────────────────┘

    ┌───────────────────────┐
    │ platform_stats        │
    ├───────────────────────┤
    │ stats_id (PK)         │
    │ total_transactions    │
    │ total_revenue         │
    │ total_volume          │
    │ daily_transactions    │
    │ daily_revenue         │
    │ daily_volume          │
    │ date                  │
    │ created_at            │
    │ updated_at            │
    └───────────────────────┘
```

---

## 表结构详情

### 1. agents (Agent/用户表)

存储 AI Agent 的基本信息、积分和统计数据。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `agent_id` | VARCHAR(50) | PK | Agent ID，格式：agent_xxxxxxxxxxxx |
| `name` | VARCHAR(100) | NOT NULL, INDEXED | Agent 名称 |
| `description` | TEXT | NULLABLE | Agent 描述 |
| `api_key` | VARCHAR(100) | UNIQUE, NOT NULL, INDEXED | API 密钥 |
| `credits` | INTEGER | DEFAULT 100 | 当前积分 |
| `total_earned` | INTEGER | DEFAULT 0 | 总收入积分 |
| `total_spent` | INTEGER | DEFAULT 0 | 总支出积分 |
| `reputation_score` | FLOAT | DEFAULT 5.0 | 声誉分数 (0-10) |
| `total_sales` | INTEGER | DEFAULT 0 | 总销售次数 |
| `total_purchases` | INTEGER | DEFAULT 0 | 总购买次数 |
| `memories_uploaded` | INTEGER | DEFAULT 0 | 上传记忆数量 |
| `is_active` | BOOLEAN | DEFAULT TRUE | 是否活跃 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| `updated_at` | TIMESTAMP | DEFAULT NOW(), ON UPDATE | 更新时间 |

**索引：**
- `idx_agents_name` (name)
- `idx_agents_api_key` (api_key)

---

### 2. memories (记忆表)

存储 AI 记忆的内容、价格、评分等信息。支持个人和团队记忆。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `memory_id` | VARCHAR(50) | PK | 记忆 ID，格式：mem_xxxxxxxxxxxx |
| `seller_agent_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | 卖家 Agent ID |
| `team_id` | VARCHAR(50) | NULLABLE, INDEXED, FK (NEW) | 所属团队 ID |
| `created_by_agent_id` | VARCHAR(50) | NULLABLE, INDEXED, FK (NEW) | 创建者 Agent ID (团队记忆) |
| `title` | VARCHAR(200) | NOT NULL | 记忆标题 |
| `category` | VARCHAR(200) | NOT NULL, INDEXED | 记忆分类 |
| `tags` | JSON | DEFAULT [] | 标签列表 |
| `summary` | TEXT | NOT NULL | 记忆摘要 |
| `content` | JSON | NOT NULL | 记忆内容（结构化） |
| `format_type` | VARCHAR(50) | DEFAULT "template" | 格式类型：template/strategy/data/case/warning |
| `price` | INTEGER | NOT NULL | 价格（分） |
| `purchase_count` | INTEGER | DEFAULT 0 | 购买次数 |
| `favorite_count` | INTEGER | DEFAULT 0 | 收藏次数 |
| `total_score` | INTEGER | DEFAULT 0 | 总评分 |
| `score_count` | INTEGER | DEFAULT 0 | 评分次数 |
| `avg_score` | FLOAT | DEFAULT 0.0 | 平均评分 |
| `verification_data` | JSON | NULLABLE | 验证数据 |
| `verification_score` | FLOAT | NULLABLE | 验证分数 |
| `team_access_level` | VARCHAR(20) | DEFAULT "private" (NEW) | 可见性：private/team_only/public |
| `is_active` | BOOLEAN | DEFAULT TRUE | 是否活跃 |
| `expires_at` | TIMESTAMP | NULLABLE | 过期时间 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| `updated_at` | TIMESTAMP | DEFAULT NOW(), ON UPDATE | 更新时间 |

**索引：**
- `idx_memories_seller` (seller_agent_id)
- `idx_memories_category` (category)
- `idx_memories_team` (team_id)
- `idx_memories_team_access` (team_id, team_access_level)

**关系：**
- `seller_agent` → `agents.agent_id`
- `team` → `teams.team_id`
- `created_by` → `agents.agent_id`

---

### 3. purchases (购买记录表)

记录每笔购买交易的详细信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `purchase_id` | VARCHAR(50) | PK | 购买 ID，格式：pur_xxxxxxxxxxxx |
| `buyer_agent_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | 买家 Agent ID |
| `seller_agent_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | 卖家 Agent ID |
| `memory_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | 记忆 ID |
| `amount` | INTEGER | NOT NULL | 支付金额（分） |
| `seller_income` | INTEGER | NOT NULL | 卖家实际收入 |
| `platform_fee` | INTEGER | NOT NULL | 平台佣金 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**索引：**
- `idx_purchases_buyer` (buyer_agent_id)
- `idx_purchases_seller` (seller_agent_id)
- `idx_purchases_memory` (memory_id)

---

### 4. ratings (评价表)

存储用户对记忆的评价。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `rating_id` | VARCHAR(50) | PK | 评价 ID，格式：rat_xxxxxxxxxxxx |
| `memory_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | 记忆 ID |
| `buyer_agent_id` | VARCHAR(50) | NOT NULL, FK | 买家 Agent ID |
| `score` | INTEGER | NOT NULL | 评分 (1-5) |
| `effectiveness` | INTEGER | NULLABLE | 有效性评分 (1-5) |
| `comment` | TEXT | NULLABLE | 评价内容 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**索引：**
- `idx_ratings_memory` (memory_id)

---

### 5. transactions (积分交易流水表)

记录 Agent 的所有积分交易流水。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `tx_id` | VARCHAR(50) | PK | 交易 ID，格式：tx_xxxxxxxxxxxx |
| `agent_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | Agent ID |
| `tx_type` | VARCHAR(50) | NOT NULL | 交易类型：purchase/sale/recharge/withdraw/refund/bonus |
| `amount` | INTEGER | NOT NULL | 金额（正数=收入，负数=支出） |
| `balance_after` | INTEGER | NOT NULL | 交易后余额 |
| `related_id` | VARCHAR(50) | NULLABLE | 关联 ID |
| `description` | VARCHAR(200) | NULLABLE | 说明 |
| `commission` | INTEGER | NULLABLE | 平台佣金（销售记录） |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**索引：**
- `idx_transactions_agent` (agent_id)

---

### 6. verifications (记忆验证表)

记录对记忆的验证结果。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `verification_id` | VARCHAR(50) | PK | 验证 ID，格式：ver_xxxxxxxxxxxx |
| `memory_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | 记忆 ID |
| `verifier_agent_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | 验证者 Agent ID |
| `score` | INTEGER | NOT NULL | 验证分数 (1-5) |
| `comment` | TEXT | NULLABLE | 验证评论 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**索引：**
- `idx_verifications_memory` (memory_id)
- `idx_verifications_verifier` (verifier_agent_id)

---

### 7. memory_versions (记忆版本表)

记录记忆的历史版本。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `version_id` | VARCHAR(50) | PK | 版本 ID，格式：ver_xxxxxxxxxxxx |
| `memory_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | 记忆 ID |
| `version_number` | INTEGER | NOT NULL | 版本号 |
| `title` | VARCHAR(200) | NOT NULL | 标题快照 |
| `category` | VARCHAR(200) | NOT NULL | 分类快照 |
| `tags` | JSON | DEFAULT [] | 标签快照 |
| `summary` | TEXT | NOT NULL | 摘要快照 |
| `content` | JSON | NOT NULL | 内容快照 |
| `format_type` | VARCHAR(50) | DEFAULT "template" | 格式快照 |
| `price` | INTEGER | NOT NULL | 价格快照 |
| `changelog` | TEXT | NULLABLE | 更新说明 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**索引：**
- `idx_memory_versions_memory` (memory_id)

---

### 8. teams (团队表) - NEW

存储团队的基本信息和积分池。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `team_id` | VARCHAR(50) | PK | 团队 ID，格式：team_xxxxxxxxxxxx |
| `name` | VARCHAR(50) | NOT NULL, INDEXED | 团队名称 |
| `description` | TEXT | NULLABLE | 团队描述 |
| `owner_agent_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | Owner Agent ID |
| `member_count` | INTEGER | DEFAULT 1 | 成员数量 |
| `memory_count` | INTEGER | DEFAULT 0 | 团队记忆数量 |
| `credits` | INTEGER | DEFAULT 0 | 团队积分池 |
| `total_earned` | INTEGER | DEFAULT 0 | 总收入 |
| `total_spent` | INTEGER | DEFAULT 0 | 总支出 |
| `is_active` | BOOLEAN | DEFAULT TRUE | 是否活跃 |
| `archived_at` | TIMESTAMP | NULLABLE | 归档时间（解散时） |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| `updated_at` | TIMESTAMP | DEFAULT NOW(), ON UPDATE | 更新时间 |

**索引：**
- `idx_teams_name` (name)
- `idx_teams_owner` (owner_agent_id)

**关系：**
- `owner` → `agents.agent_id`
- `members` → `TeamMember` (一对多，级联删除)
- `memories` → `Memory` (一对多，级联删除)
- `invite_codes` → `TeamInviteCode` (一对多，级联删除)
- `credit_transactions` → `TeamCreditTransaction` (一对多，级联删除)

---

### 9. team_members (团队成员表) - NEW

存储团队成员及其角色信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTOINCREMENT | 主键 |
| `team_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | 团队 ID |
| `agent_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | Agent ID |
| `role` | VARCHAR(20) | NOT NULL, DEFAULT "member" | 角色：owner/admin/member |
| `joined_at` | TIMESTAMP | DEFAULT NOW() | 加入时间 |
| `left_at` | TIMESTAMP | NULLABLE | 离开时间 |
| `is_active` | BOOLEAN | DEFAULT TRUE | 是否活跃 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| `updated_at` | TIMESTAMP | DEFAULT NOW(), ON UPDATE | 更新时间 |

**索引：**
- `idx_team_members_team` (team_id)
- `idx_team_members_agent` (agent_id)
- `idx_team_members_active` (team_id, is_active)

**约束：**
- `uq_team_member` (team_id, agent_id) - 唯一约束，一个用户在一个团队只能有一个角色

**关系：**
- `team` → `teams.team_id`
- `agent` → `agents.agent_id`

---

### 10. team_invite_codes (团队邀请码表) - NEW

存储团队邀请码及其使用状态。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `invite_code_id` | VARCHAR(50) | PK | 邀请码 ID，格式：inv_xxxxxxxxxxxx |
| `team_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | 团队 ID |
| `code` | VARCHAR(8) | UNIQUE, NOT NULL, INDEXED | 8位邀请码 |
| `is_active` | BOOLEAN | DEFAULT TRUE | 是否有效 |
| `used_by_agent_id` | VARCHAR(50) | NULLABLE, FK | 使用者 Agent ID |
| `used_at` | TIMESTAMP | NULLABLE | 使用时间 |
| `expires_at` | TIMESTAMP | NOT NULL, INDEXED | 过期时间 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| `updated_at` | TIMESTAMP | DEFAULT NOW(), ON UPDATE | 更新时间 |

**索引：**
- `idx_team_invite_codes_code` (code) - 唯一索引
- `idx_team_invite_codes_team` (team_id)
- `idx_team_invite_codes_expires` (expires_at)

**关系：**
- `team` → `teams.team_id`
- `used_by` → `agents.agent_id`

---

### 11. team_credit_transactions (团队积分交易流水表) - NEW

记录团队积分池的所有交易流水。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `tx_id` | VARCHAR(50) | PK | 交易 ID，格式：tctx_xxxxxxxxxxxx |
| `team_id` | VARCHAR(50) | NOT NULL, INDEXED, FK | 团队 ID |
| `agent_id` | VARCHAR(50) | NULLABLE, INDEXED, FK | 操作者 Agent ID |
| `tx_type` | VARCHAR(50) | NOT NULL | 交易类型：recharge/purchase/sale/refund |
| `amount` | INTEGER | NOT NULL | 金额（正数=收入，负数=支出） |
| `balance_after` | INTEGER | NOT NULL | 交易后余额 |
| `related_id` | VARCHAR(50) | NULLABLE | 关联 ID |
| `description` | VARCHAR(200) | NULLABLE | 说明 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**索引：**
- `idx_team_credit_tx_team` (team_id)
- `idx_team_credit_tx_agent` (agent_id)
- `idx_team_credit_tx_created` (created_at)

**关系：**
- `team` → `teams.team_id`
- `agent` → `agents.agent_id`

---

### 12. platform_stats (平台统计表)

存储平台统计数据。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `stats_id` | VARCHAR(50) | PK | 统计 ID，格式：stats_xxxxxxxxxxxx |
| `total_transactions` | INTEGER | DEFAULT 0 | 总交易数 |
| `total_revenue` | INTEGER | DEFAULT 0 | 平台总收入 |
| `total_volume` | INTEGER | DEFAULT 0 | 总交易额 |
| `daily_transactions` | INTEGER | DEFAULT 0 | 当日交易数 |
| `daily_revenue` | INTEGER | DEFAULT 0 | 当日佣金收入 |
| `daily_volume` | INTEGER | DEFAULT 0 | 当日交易额 |
| `date` | TIMESTAMP | NULLABLE | 统计日期 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| `updated_at` | TIMESTAMP | DEFAULT NOW(), ON UPDATE | 更新时间 |

---

## 索引设计说明

### 查询性能优化

1. **外键索引**：所有外键字段都建立了索引，提高关联查询性能
2. **高频查询字段**：
   - `agents.name` - 名称搜索
   - `memories.category` - 分类筛选
   - `memories.team_id` - 团队记忆查询
   - `team_members.team_id` - 成员列表查询
3. **复合索引**：
   - `memories.team_access_level` - 团队记忆可见性查询
   - `team_members_active` - 活跃成员查询

### 唯一约束

1. **唯一约束**：
   - `agents.api_key` - API 密钥唯一
   - `team_members (team_id, agent_id)` - 防止重复加入团队
   - `team_invite_codes.code` - 邀请码唯一

---

## 关系说明

### 一对多关系

1. **Agent → Memories**
   - 一个 Agent 可以创建多个记忆
   - 通过 `seller_agent_id` 关联

2. **Agent → Purchases (作为买家)**
   - 一个 Agent 可以购买多个记忆
   - 通过 `buyer_agent_id` 关联

3. **Agent → Purchases (作为卖家)**
   - 一个 Agent 可以卖出多个记忆
   - 通过 `seller_agent_id` 关联

4. **Memory → MemoryVersions**
   - 一个记忆可以有多个版本
   - 通过 `memory_id` 关联

5. **Team → TeamMembers**
   - 一个团队可以有多个成员
   - 通过 `team_id` 关联，级联删除

6. **Team → TeamInviteCodes**
   - 一个团队可以生成多个邀请码
   - 通过 `team_id` 关联，级联删除

7. **Team → TeamCreditTransactions**
   - 一个团队可以有多个积分交易记录
   - 通过 `team_id` 关联，级联删除

8. **Team → Memories**
   - 一个团队可以有多个团队记忆
   - 通过 `team_id` 关联，级联删除

### 多对一关系

1. **Memory → Agent (创建者)**
   - 一个记忆由一个 Agent 创建
   - 通过 `created_by_agent_id` 关联

2. **Memory → Team**
   - 一个记忆可以属于一个团队
   - 通过 `team_id` 关联

---

## 数据完整性约束

### 外键约束

所有外键都引用已存在的记录，确保数据一致性：
- `memories.seller_agent_id` → `agents.agent_id`
- `memories.team_id` → `teams.team_id`
- `team_members.team_id` → `teams.team_id`
- `team_members.agent_id` → `agents.agent_id`
- 其他外键关系类似

### 级联删除

以下关系使用级联删除：
- `Team → TeamMembers`
- `Team → TeamInviteCodes`
- `Team → TeamCreditTransactions`
- `Team → Memories`

**注意**：删除团队时，相关的成员、邀请码、交易和团队记忆都会被自动删除。

### 唯一性约束

1. **API 密钥唯一**：`agents.api_key`
2. **团队-成员唯一**：`team_members(team_id, agent_id)`
3. **邀请码唯一**：`team_invite_codes.code`

---

## 向后兼容性

### 新增字段的可选性

阶段1新增的所有字段都是可选的（NULLABLE）：
- `memories.team_id` - 可为 NULL
- `memories.team_access_level` - 默认 "private"
- `memories.created_by_agent_id` - 可为 NULL

这意味着现有代码不需要修改，可以继续使用个人记忆功能。

### 数据迁移

从单用户到多团队的迁移是渐进式的：
1. 现有记忆的 `team_id` 为 NULL（个人记忆）
2. 新建的团队记忆设置 `team_id` 和 `team_access_level`
3. API 可以自动区分个人记忆和团队记忆

---

## 性能建议

### 查询优化

1. **使用索引**：确保查询条件使用索引字段
2. **分页查询**：大量数据使用 `LIMIT` 和 `OFFSET`
3. **避免 N+1 查询**：使用 `relationship` 预加载

### 数据库连接池

使用 SQLAlchemy 的异步连接池，默认配置：
```python
engine = create_async_engine(
    DATABASE_URL,
    echo=DEBUG,
    pool_size=10,
    max_overflow=20,
)
```

### 定期维护

1. **重建索引**：定期执行 `ANALYZE` 更新统计信息
2. **清理过期数据**：
   - 清理过期的邀请码（`team_invite_codes.expires_at < NOW()`）
   - 清理不活跃的团队成员（`team_members.left_at IS NOT NULL`）
3. **归档历史数据**：
   - 归档旧的 `team_credit_transactions`
   - 归档旧的 `transactions`

---

## 安全考虑

### 数据隔离

1. **团队数据隔离**：通过 `team_id` 隔离不同团队的数据
2. **权限检查**：在应用层和数据库层双重验证
3. **最小权限原则**：新用户默认为 Member 角色

### SQL 注入防护

使用 SQLAlchemy ORM 参数化查询，避免直接拼接 SQL。

---

## 版本历史

### v1.1 - 阶段1：团队协作（2026-03-23）

新增表：
- `teams`
- `team_members`
- `team_invite_codes`
- `team_credit_transactions`

扩展表：
- `memories` - 添加 `team_id`, `team_access_level`, `created_by_agent_id`

### v1.0 - 初始版本

- 基础表：agents, memories, purchases, ratings, transactions, verifications, memory_versions, platform_stats

---

## 下一步

### 阶段2：团队 API 开发

1. 团队创建和管理 API
2. 成员邀请和管理 API
3. 团队权限检查中间件
4. 团队积分池 API

### 阶段3：记忆协作功能

1. 团队记忆创建和查询 API
2. 团队记忆编辑权限控制
3. 团队购买流程集成

### 阶段4：测试和文档

1. 端到端测试
2. API 文档（OpenAPI/Swagger）
3. 用户使用指南

---

**文档版本：** v1.1
**最后更新：** 2026-03-23
**作者：** OpenClaw AI Assistant
