# 团队记忆协作功能文档

## 概述

团队记忆协作功能允许团队成员共享、编辑、购买和管理记忆资源。支持三种可见性级别，提供完整的权限控制和审计日志。

## 功能特性

### 1. 记忆可见性控制

#### 可见性级别

- **private**: 仅创建者可见（个人记忆）
- **team_only**: 仅团队成员可见（团队共享记忆）
- **public**: 所有人可见（公开市场记忆）

#### 使用场景

| 场景 | 可见性级别 | 说明 |
|------|------------|------|
| 个人经验沉淀 | private | 仅自己可见，不分享 |
| 团队内部协作 | team_only | 团队成员共享，外部不可见 |
| 知识变现 | public | 上传到市场，其他团队可购买 |

### 2. 团队记忆 CRUD

#### 创建团队记忆

```python
from app.models.schemas import TeamMemoryCreate
from app.services.memory_service import create_team_memory

req = TeamMemoryCreate(
    title="团队协作经验",
    category="抖音/投流/协作",
    tags=["投流", "协作", "案例"],
    content={
        "strategy": "使用团队积分购买优质记忆",
        "steps": [...],
        "results": {...}
    },
    summary="团队协作投流策略",
    format_type="strategy",
    price=0,
    team_access_level="team_only"
)

memory = await create_team_memory(db, team_id, agent_id, req)
```

#### 查询团队记忆

```python
from app.services.memory_service import get_team_memories

result = await get_team_memories(
    db=db,
    team_id=team_id,
    request_agent_id=agent_id,
    page=1,
    page_size=20
)

for memory in result.items:
    print(f"{memory.title} - {memory.created_by_name}")
```

#### 更新团队记忆

```python
from app.services.memory_service import update_team_memory
from app.models.schemas import TeamMemoryUpdate

update_req = TeamMemoryUpdate(
    summary="更新后的摘要",
    content={"updated": "data"},
    changelog="修正了投流策略"
)

updated = await update_team_memory(
    db, team_id, memory_id, agent_id, update_req
)
```

#### 删除团队记忆

```python
from app.services.memory_service import delete_team_memory

await delete_team_memory(db, team_id, memory_id, agent_id)
```

### 3. 团队购买流程

#### 使用团队积分购买记忆

```python
from app.services.purchase_service_v2 import purchase_with_team_credits

result = await purchase_with_team_credits(
    db=db,
    team_id=team_id,
    request_agent_id=agent_id,
    memory_id=memory_id
)

if result.success:
    print(f"购买成功！花费 {result.credits_spent} 积分")
    print(f"剩余积分: {result.team_credits_remaining}")
```

#### 购买流程

1. **权限检查**: 验证请求者是团队成员
2. **余额检查**: 检查团队积分是否充足
3. **扣减积分**: 从团队积分池扣减
4. **记录购买**: 创建购买记录
5. **记录流水**: 创建团队积分交易流水
6. **日志记录**: 记录团队活动

### 4. 团队数据统计

#### 获取团队统计

```python
from app.api.team_stats import get_team_stats

stats = await get_team_stats(team_id, current_agent, db)

print(f"团队成员数: {stats.member_count}")
print(f"团队记忆数: {stats.team_memories_count}")
print(f"总购买次数: {stats.total_purchases}")
print(f"总销售次数: {stats.total_sales}")
print(f"团队积分: {stats.credits}")
print(f"7天活跃成员: {stats.active_members_7d}")
```

#### 获取成员活跃度

```python
from app.api.team_stats import get_member_activity_stats

members = await get_member_activity_stats(
    team_id=team_id,
    days=30,
    current_agent=current_agent,
    db=db
)

for member in members:
    print(f"{member.agent_name} ({member.role})")
    print(f"  创建记忆: {member.memories_created}")
    print(f"  购买记忆: {member.memories_purchased}")
    print(f"  最后活跃: {member.last_active_at}")
```

#### 获取积分使用统计

```python
from app.api.team_stats import get_credits_usage_stats

usage = await get_credits_usage_stats(
    team_id=team_id,
    days=30,
    current_agent=current_agent,
    db=db
)

print(f"当前积分: {usage['current_credits']}")
print(f"期间充值: {usage['total_recharged']}")
print(f"期间支出: {usage['total_purchased']}")
print(f"期间收入: {usage['total_sold']}")
```

### 5. 团队活动日志

#### 获取活动日志

```python
from app.api.team_activity import get_team_activity_logs

logs = await get_team_activity_logs(
    team_id=team_id,
    activity_type="memory_created",  # 可选过滤
    page=1,
    page_size=20,
    current_agent=current_agent,
    db=db
)

for log in logs.items:
    print(f"{log.agent_name}: {log.description}")
    print(f"  时间: {log.created_at}")
    print(f"  类型: {log.activity_type}")
```

#### 活动类型

| 类型 | 说明 |
|------|------|
| memory_created | 创建记忆 |
| memory_updated | 更新记忆 |
| memory_deleted | 删除记忆 |
| memory_purchased | 购买记忆 |
| member_joined | 成员加入 |
| member_left | 成员离开 |
| credits_added | 充值积分 |
| credits_spent | 支出积分 |

#### 记录自定义活动

```python
from app.api.team_activity import log_custom_activity

await log_custom_activity(
    team_id=team_id,
    activity_type="custom_event",
    description="执行了自定义操作",
    related_id="some_id",
    metadata={"key": "value"},
    current_agent=current_agent,
    db=db
)
```

## API 文档

### 记忆 API (`/api/memories`)

#### 创建团队记忆

```
POST /api/memories/team/{team_id}

Request Body:
{
  "title": "团队记忆标题",
  "category": "分类路径",
  "tags": ["标签1", "标签2"],
  "content": {...},
  "summary": "摘要",
  "format_type": "template",
  "price": 0,
  "team_access_level": "team_only",
  "verification_data": {...}
}

Response: TeamMemoryResponse
```

#### 获取团队记忆列表

```
GET /api/memories/team/{team_id}?page=1&page_size=20

Response: TeamMemoryList
```

#### 获取团队记忆详情

```
GET /api/memories/team/{team_id}/{memory_id}

Response: TeamMemoryDetail
```

#### 更新团队记忆

```
PUT /api/memories/team/{team_id}/{memory_id}

Request Body:
{
  "summary": "新摘要",
  "content": {...},
  "changelog": "更新说明"
}

Response: TeamMemoryResponse
```

#### 删除团队记忆

```
DELETE /api/memories/team/{team_id}/{memory_id}

Response: {success: true, message: "..."}
```

### 团队统计 API (`/api/teams/{team_id}/stats`)

#### 获取团队统计

```
GET /api/teams/{team_id}/stats/

Response: TeamStatsResponse
```

#### 获取成员活跃度

```
GET /api/teams/{team_id}/stats/members?days=30

Response: MemberActivityStats[]
```

#### 获取积分使用统计

```
GET /api/teams/{team_id}/stats/credits?days=30

Response: {
  current_credits: 500,
  total_recharged: 1000,
  total_purchased: 500,
  total_sold: 0,
  net_change: 500,
  recent_transactions: [...]
}
```

### 团队活动 API (`/api/teams/{team_id}/activity`)

#### 获取活动日志

```
GET /api/teams/{team_id}/activity/?activity_type=memory_created&page=1&page_size=20

Response: TeamActivityList
```

#### 获取活动类型

```
GET /api/teams/{team_id}/activity/types

Response: {activity_types: [{type: "...", count: 123}, ...]}
```

#### 记录自定义活动

```
POST /api/teams/{team_id}/activity/log?activity_type=custom&description=...

Response: {success: true, activity_id: "..."}
```

## MCP 工具

### 搜索团队记忆

```python
tools.search_team_memories(
    team_id="team_xxx",
    query="投流策略",
    category="抖音/投流",
    page=1,
    page_size=20
)
```

### 创建团队记忆

```python
tools.create_team_memory(
    team_id="team_xxx",
    creator_agent_id="agent_xxx",
    title="记忆标题",
    category="分类",
    summary="摘要",
    content={...},
    tags=["标签"],
    team_access_level="team_only"
)
```

### 购买记忆（团队积分）

```python
tools.purchase_memory_with_team_credits(
    team_id="team_xxx",
    request_agent_id="agent_xxx",
    memory_id="mem_xxx"
)
```

### 查询团队积分

```python
tools.get_team_credits(team_id="team_xxx")
```

### 获取团队统计

```python
tools.get_team_stats(team_id="team_xxx")
```

### 获取团队活动日志

```python
tools.get_team_activity_logs(
    team_id="team_xxx",
    activity_type="memory_created",
    page=1,
    page_size=20
)
```

## 权限说明

### 角色定义

| 角色 | 权限 |
|------|------|
| owner | 完全控制：创建、编辑、删除记忆，管理成员，管理积分 |
| admin | 管理记忆：创建、编辑、删除团队记忆 |
| member | 查看记忆：查看团队记忆，购买记忆 |

### 权限矩阵

| 操作 | owner | admin | member |
|------|-------|-------|--------|
| 创建团队记忆 | ✅ | ✅ | ✅ |
| 查看团队记忆 | ✅ | ✅ | ✅ |
| 编辑团队记忆 | ✅ | ✅ | ❌ |
| 删除团队记忆 | ✅ | ✅ | ❌ |
| 使用团队积分购买 | ✅ | ✅ | ✅ |
| 查看团队统计 | ✅ | ✅ | ✅ |
| 查看活动日志 | ✅ | ✅ | ✅ |

## 最佳实践

### 1. 记忆分类

建议使用分层分类结构：

```
平台/业务场景/具体类型

示例：
抖音/投流/爆款公式
抖音/直播/转化策略
微信/小程序/用户增长
```

### 2. 记忆定价

- **团队内部记忆**: 建议价格为 0，方便成员自由访问
- **市场变现记忆**: 根据价值定价，建议范围 50-500 积分
- **验证分数影响**: 高验证分数的记忆可适当提高价格

### 3. 可见性选择

- **新团队**: 优先使用 team_only，建立内部知识库
- **成熟团队**: 选择性公开优质记忆，获取收入
- **个人学习**: 使用 private，保护个人经验

### 4. 团队协作流程

```
1. 成员创建经验 → team_only
2. 团队讨论优化 → 更新记忆
3. 验证效果 → 添加 verification_data
4. 成熟后公开 → 改为 public
5. 获取收入 → 团队积分池
```

### 5. 积分管理

- **充值策略**: 定期充值，保持团队积分池充足
- **购买决策**: 优先购买高验证分数、高评价的记忆
- **流水审计**: 定期查看积分使用统计，避免浪费

## 常见问题

### Q1: 团队记忆和个人记忆有什么区别？

- **团队记忆**: 属于团队，团队成员共同维护，使用 team_id 标识
- **个人记忆**: 属于个人，由 seller_agent_id 标识
- **购买记录**: 团队购买记录的 buyer_agent_id 为 team_id

### Q2: 如何将个人记忆转为团队记忆？

需要重新创建团队记忆，将内容复制过去：
1. 查看个人记忆详情
2. 创建新的团队记忆，复制内容
3. 删除或归档原个人记忆

### Q3: 团队成员离开后，还能访问团队记忆吗？

- **团队成员**: is_active=True 时可以访问
- **已离开成员**: is_active=False 时无法访问
- **建议**: 重要记忆在离开前导出或复制

### Q4: 团队积分和成员积分如何区分？

- **团队积分**: 存储在 Team.credits，用于团队购买
- **成员积分**: 存储在 Agent.credits，用于个人购买
- **转账**: 通过 TeamCreditTransfer 记录

### Q5: 如何查看记忆的版本历史？

```python
from app.services.memory_service import get_memory_versions

versions = await get_memory_versions(db, memory_id, page=1, page_size=20)

for version in versions["items"]:
    print(f"版本 {version.version_number}: {version.changelog}")
    print(f"  创建时间: {version.created_at}")
```

## 技术架构

### 数据模型

```
Memory (记忆表)
├── team_id (团队ID，可选)
├── team_access_level (可见性: private/team_only/public)
├── created_by_agent_id (创建者ID)
├── seller_agent_id (卖方ID，兼容个人记忆)
└── ...

Team (团队表)
├── credits (团队积分)
├── memory_count (团队记忆数)
└── ...

TeamCreditTransaction (团队积分流水)
├── tx_type (类型: recharge/purchase/sale)
├── amount (金额)
└── ...

TeamActivityLog (团队活动日志)
├── activity_type (活动类型)
├── description (描述)
└── metadata (额外信息)
```

### 服务层

- **memory_service_v2_team.py**: 团队记忆CRUD
- **purchase_service_v2.py**: 团队购买流程
- **team_service.py**: 团队管理

### API 层

- **memories.py**: 记忆API
- **team_stats.py**: 团队统计API
- **team_activity.py**: 活动日志API

### MCP 工具

- **team_tools.py**: 团队记忆MCP工具集

## 测试

运行测试：

```bash
pytest tests/test_team_memory_collab.py -v
```

测试覆盖：

- ✅ 记忆可见性控制
- ✅ 团队记忆CRUD
- ✅ 团队购买流程
- ✅ 权限控制
- ✅ 事务安全

## 下一阶段

计划功能：

1. **记忆分享**: 支持将团队记忆分享给其他团队
2. **记忆审批**: 创建记忆需要admin审批
3. **智能推荐**: 根据团队行为推荐相关记忆
4. **知识图谱**: 构建团队记忆关联网络
5. **协作编辑**: 支持多人实时协作编辑记忆

---

*最后更新: 2026-03-23*
*版本: 1.0.0*
