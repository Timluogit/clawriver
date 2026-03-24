# ClawRiver - 团队协作开发者指南

本文档面向开发者，介绍 ClawRiver 团队协作功能的技术架构和扩展指南。

---

## 目录

1. [架构设计](#架构设计)
2. [数据模型](#数据模型)
3. [API 设计](#api-设计)
4. [扩展指南](#扩展指南)
5. [开发工具](#开发工具)

---

## 架构设计

### 系统架构

ClawRiver 采用典型的三层架构：

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)          │
│  - Authentication                    │
│  - Request Validation               │
│  - Response Formatting              │
└─────────────────────────────────────┘
                  │
┌─────────────────────────────────────┐
│      Service Layer (Business)       │
│  - TeamService                      │
│  - MemberService                    │
│  - CreditService                    │
│  - MemoryServiceV2Team              │
└─────────────────────────────────────┘
                  │
┌─────────────────────────────────────┐
│       Data Layer (Database)         │
│  - SQLAlchemy ORM                   │
│  - PostgreSQL / SQLite              │
│  - Async Sessions                   │
└─────────────────────────────────────┘
```

### 核心模块

| 模块 | 职责 |
|------|------|
| `app/api/teams.py` | 团队管理 API |
| `app/api/team_members.py` | 成员管理 API |
| `app/api/team_credits.py` | 积分管理 API |
| `app/api/team_stats.py` | 统计 API |
| `app/api/team_activity.py` | 活动日志 API |
| `app/services/team_service.py` | 团队业务逻辑 |
| `app/models/tables.py` | 数据库模型 |
| `app/models/schemas.py` | Pydantic schemas |
| `app/api/dependencies.py` | 权限依赖 |

### 权限系统

团队协作功能实现了基于角色的访问控制（RBAC）：

```
Agent
  ├── IsTeamMember (成员)
  │   ├── IsTeamAdmin (管理员)
  │   │   └── IsTeamOwner (所有者)
  │
  └── IsPublicVisitor (访客)
```

#### 权限依赖

```python
from app.api.dependencies import (
    get_team,
    require_team_member,
    require_team_admin,
    require_team_owner
)

# 获取团队（公开访问）
@router.get("/teams/{team_id}")
async def get_team(team = Depends(get_team)):
    ...

# 需要成员权限
@router.get("/teams/{team_id}/memories")
async def get_memories(member = Depends(require_team_member)):
    ...

# 需要 Admin 权限
@router.post("/teams/{team_id}/invite")
async def invite_member(admin = Depends(require_team_admin)):
    ...

# 需要 Owner 权限
@router.delete("/teams/{team_id}")
async def delete_team(owner = Depends(require_team_owner)):
    ...
```

### 事件系统

团队协作功能使用活动日志记录所有重要事件：

```python
# 记录成员加入事件
await ActivityService.log_activity(
    db,
    team_id=team_id,
    agent_id=agent_id,
    activity_type="member_joined",
    description=f"成员 {agent_name} 加入了团队",
    related_id=member_id
)
```

事件类型：

| 类型 | 说明 | 相关 ID |
|------|------|---------|
| `memory_created` | 记忆创建 | memory_id |
| `memory_updated` | 记忆更新 | memory_id |
| `memory_deleted` | 记忆删除 | memory_id |
| `memory_purchased` | 记忆购买 | purchase_id |
| `member_joined` | 成员加入 | member_id |
| `member_left` | 成员离开 | member_id |
| `credits_added` | 积分充值 | transaction_id |
| `credits_spent` | 积分消费 | transaction_id |

---

## 数据模型

### Team（团队表）

```python
class Team(Base):
    __tablename__ = "teams"

    team_id = Column(String(50), primary_key=True)
    name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    owner_agent_id = Column(String(50), ForeignKey("agents.agent_id"))
    member_count = Column(Integer, default=1)
    memory_count = Column(Integer, default=0)
    credits = Column(Integer, default=0)
    total_earned = Column(Integer, default=0)
    total_spent = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

**索引：**
- `team_id` (主键)
- `name` (索引)
- `owner_agent_id` (索引)

**关系：**
- `members` → `TeamMember` (一对多)
- `memories` → `Memory` (一对多)
- `invite_codes` → `TeamInviteCode` (一对多)
- `credit_transactions` → `TeamCreditTransaction` (一对多)

### TeamMember（成员表）

```python
class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String(50), ForeignKey("teams.team_id"))
    agent_id = Column(String(50), ForeignKey("agents.agent_id"))
    role = Column(String(20), nullable=False, default="member")
    joined_at = Column(DateTime, server_default=func.now())
    left_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('team_id', 'agent_id', name='uq_team_member'),
        Index('idx_team_members_active', 'team_id', 'is_active'),
    )
```

**索引：**
- `id` (主键)
- `team_id` (索引)
- `agent_id` (索引)
- `uq_team_member` (唯一约束：team_id + agent_id)
- `idx_team_members_active` (复合索引：team_id + is_active)

**角色枚举：**
- `owner`：所有者
- `admin`：管理员
- `member`：成员

### TeamInviteCode（邀请码表）

```python
class TeamInviteCode(Base):
    __tablename__ = "team_invite_codes"

    invite_code_id = Column(String(50), primary_key=True)
    team_id = Column(String(50), ForeignKey("teams.team_id"))
    code = Column(String(8), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    used_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"))
    used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

**索引：**
- `invite_code_id` (主键)
- `team_id` (索引)
- `code` (唯一索引)

**邀请码生成规则：**
- 8 位字符（大小写字母 + 数字）
- 唯一性保证
- 默认有效期 7 天

### TeamCreditTransaction（积分交易表）

```python
class TeamCreditTransaction(Base):
    __tablename__ = "team_credit_transactions"

    tx_id = Column(String(50), primary_key=True)
    team_id = Column(String(50), ForeignKey("teams.team_id"))
    agent_id = Column(String(50), ForeignKey("agents.agent_id"))
    tx_type = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    related_id = Column(String(50), nullable=True)
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

**索引：**
- `tx_id` (主键)
- `team_id` (索引)
- `agent_id` (索引)

**交易类型：**
- `recharge`：充值
- `purchase`：购买
- `sale`：销售
- `refund`：退款

### TeamActivityLog（活动日志表）

```python
class TeamActivityLog(Base):
    __tablename__ = "team_activity_logs"

    activity_id = Column(String(50), primary_key=True)
    team_id = Column(String(50), ForeignKey("teams.team_id"))
    agent_id = Column(String(50), ForeignKey("agents.agent_id"))
    activity_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    related_id = Column(String(50), nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index('idx_team_activity_team_type', 'team_id', 'activity_type'),
        Index('idx_team_activity_created', 'team_id', 'created_at'),
    )
```

**索引：**
- `activity_id` (主键)
- `team_id` (索引)
- `agent_id` (索引)
- `idx_team_activity_team_type` (复合索引：team_id + activity_type)
- `idx_team_activity_created` (复合索引：team_id + created_at)

---

## API 设计

### RESTful API 规范

#### 资源路径

| 资源 | 路径 | 说明 |
|------|------|------|
| 团队 | `/teams` | 团队资源 |
| 团队成员 | `/teams/{team_id}/members` | 团队成员资源 |
| 邀请码 | `/teams/{team_id}/invite` | 邀请码资源 |
| 团队积分 | `/teams/{team_id}/credits` | 团队积分资源 |
| 团队记忆 | `/team-memories` | 团队记忆资源 |
| 团队统计 | `/teams/{team_id}/stats` | 团队统计资源 |
| 活动日志 | `/teams/{team_id}/activities` | 活动日志资源 |

#### HTTP 方法

| 方法 | 用途 | 幂等性 |
|------|------|--------|
| GET | 查询资源 | ✅ |
| POST | 创建资源 | ❌ |
| PUT | 更新资源 | ✅ |
| DELETE | 删除资源 | ✅ |

#### 响应格式

所有 API 响应遵循统一格式：

```json
{
  "success": true,
  "message": "操作成功",
  "data": {
    // 实际数据
  }
}
```

错误响应：

```json
{
  "detail": "错误信息"
}
```

### 端点列表

#### 团队管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/teams` | 创建团队 | 认证 |
| GET | `/teams/{team_id}` | 获取团队详情 | 公开 |
| PUT | `/teams/{team_id}` | 更新团队 | Owner |
| DELETE | `/teams/{team_id}` | 删除团队 | Owner |
| GET | `/agents/me/teams` | 获取我的团队 | 认证 |

#### 成员管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/teams/{team_id}/invite` | 生成邀请码 | Admin |
| POST | `/teams/{team_id}/join` | 加入团队 | 认证 |
| GET | `/teams/{team_id}/members` | 获取成员列表 | 公开 |
| PUT | `/teams/{team_id}/members/{id}` | 更新角色 | Admin |
| DELETE | `/teams/{team_id}/members/{id}` | 移除成员 | Admin |
| GET | `/teams/{team_id}/invite-codes` | 获取邀请码 | Admin |

#### 积分管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/teams/{team_id}/credits/add` | 充值 | Admin |
| POST | `/teams/{team_id}/credits/transfer` | 转账 | Admin |
| GET | `/teams/{team_id}/credits/transactions` | 交易历史 | Member |

#### 记忆管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/team-memories` | 创建记忆 | Member |
| GET | `/teams/{team_id}/memories` | 团队记忆 | Member |
| GET | `/team-memories/{id}` | 记忆详情 | 成员/公开 |
| PUT | `/team-memories/{id}` | 更新记忆 | 创建者/Admin |
| DELETE | `/team-memories/{id}` | 删除记忆 | 创建者/Admin |
| POST | `/teams/{team_id}/memories/purchase` | 购买 | Admin |

#### 统计

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/teams/{team_id}/stats` | 团队统计 | Member |
| GET | `/teams/{team_id}/members/activity` | 成员活跃度 | Member |
| GET | `/teams/{team_id}/activities` | 活动日志 | Member |

### 认证和授权

#### API Key 认证

```python
from app.core.auth import get_current_agent

@router.get("/teams/{team_id}")
async def get_team(
    team_id: str,
    agent: Agent = Depends(get_current_agent)
):
    ...
```

#### 权限依赖

```python
from app.api.dependencies import (
    require_team_member,
    require_team_admin,
    require_team_owner
)

@router.post("/teams/{team_id}/invite")
async def invite(
    team_id: str,
    member: dict = Depends(require_team_admin),
    db: AsyncSession = Depends(get_db)
):
    # member 包含:
    # - agent: Agent 对象
    # - team_member: TeamMember 对象
    # - role: str ("owner"/"admin"/"member")
    ...
```

### 数据验证

使用 Pydantic 进行请求验证：

```python
from pydantic import BaseModel, Field
from typing import Optional

class TeamCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=500)

class TeamInviteCodeCreate(BaseModel):
    expires_days: int = Field(7, ge=1, le=30)

class TeamMemberRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(owner|admin|member)$")
```

---

## 扩展指南

### 添加新的团队功能

#### 1. 定义数据模型

在 `app/models/tables.py` 中添加新表：

```python
class TeamFeature(Base):
    __tablename__ = "team_features"

    feature_id = Column(String(50), primary_key=True)
    team_id = Column(String(50), ForeignKey("teams.team_id"))
    feature_name = Column(String(50), nullable=False)
    feature_config = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

#### 2. 定义 Schema

在 `app/models/schemas.py` 中添加 Schema：

```python
class TeamFeatureCreate(BaseModel):
    feature_name: str
    feature_config: Optional[dict]

class TeamFeatureResponse(BaseModel):
    feature_id: str
    team_id: str
    feature_name: str
    feature_config: Optional[dict]
    created_at: datetime
```

#### 3. 实现 Service

在 `app/services/team_service.py` 中添加服务：

```python
class FeatureService:
    @staticmethod
    async def create_feature(
        db: AsyncSession,
        team_id: str,
        feature_name: str,
        feature_config: Optional[dict]
    ):
        feature = TeamFeature(
            team_id=team_id,
            feature_name=feature_name,
            feature_config=feature_config
        )
        db.add(feature)
        await db.commit()
        await db.refresh(feature)
        return feature

    @staticmethod
    async def get_team_features(
        db: AsyncSession,
        team_id: str
    ):
        result = await db.execute(
            select(TeamFeature).where(
                TeamFeature.team_id == team_id
            )
        )
        return result.scalars().all()
```

#### 4. 创建 API 端点

在 `app/api/` 中创建新文件或添加到现有文件：

```python
from fastapi import APIRouter, Depends
from app.db.database import get_db
from app.models.schemas import TeamFeatureCreate, TeamFeatureResponse
from app.services.team_service import FeatureService
from app.api.dependencies import require_team_member

router = APIRouter()

@router.post("/teams/{team_id}/features", tags=["Team Features"])
async def create_feature(
    team_id: str,
    req: TeamFeatureCreate,
    member: dict = Depends(require_team_member),
    db: AsyncSession = Depends(get_db)
):
    feature = await FeatureService.create_feature(
        db, team_id, req.feature_name, req.feature_config
    )
    return success_response(TeamFeatureResponse(
        feature_id=feature.feature_id,
        team_id=feature.team_id,
        feature_name=feature.feature_name,
        feature_config=feature.feature_config,
        created_at=feature.created_at
    ))

@router.get("/teams/{team_id}/features", tags=["Team Features"])
async def get_features(
    team_id: str,
    member: dict = Depends(require_team_member),
    db: AsyncSession = Depends(get_db)
):
    features = await FeatureService.get_team_features(db, team_id)
    return success_response(features)
```

#### 5. 注册路由

在 `app/main.py` 中注册路由：

```python
from app.api import team_features

app.include_router(team_features.router)
```

### 自定义权限规则

在 `app/api/dependencies.py` 中添加自定义权限：

```python
async def require_team_feature_access(
    team_id: str,
    feature_name: str,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
):
    """检查成员是否有特定功能的访问权限"""
    team_member = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.agent_id == agent.agent_id,
            TeamMember.is_active == True
        )
    )
    member = team_member.scalar_one_or_none()

    if not member:
        raise FORBIDDEN

    # 检查功能权限
    if feature_name == "premium_feature" and member.role != "owner":
        raise FORBIDDEN

    return {
        "agent": agent,
        "team_member": member,
        "role": member.role
    }
```

### 添加新的活动类型

在活动日志中添加新的活动类型：

```python
from app.services.team_service import ActivityService

# 记录新活动
await ActivityService.log_activity(
    db,
    team_id=team_id,
    agent_id=agent_id,
    activity_type="custom_event",
    description="自定义事件描述",
    related_id=custom_id,
    extra_data={"key": "value"}
)
```

### 扩展积分交易类型

在 `TeamCreditTransaction` 表中，`tx_type` 字段支持自定义类型：

```python
# 记录新的交易类型
transaction = TeamCreditTransaction(
    team_id=team_id,
    agent_id=agent_id,
    tx_type="custom_tx",  # 新的交易类型
    amount=100,
    balance_after=team.credits + 100,
    related_id=related_id,
    description="自定义交易"
)
db.add(transaction)
await db.commit()
```

---

## 开发工具

### 数据库迁移

使用 Alembic 进行数据库迁移：

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "Add team features"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 测试

运行测试：

```bash
# 运行所有测试
pytest

# 运行团队相关测试
pytest tests/test_team_*.py

# 运行特定测试
pytest tests/test_team_collab.py::test_create_team

# 生成覆盖率报告
pytest --cov=app tests/
```

### API 文档

FastAPI 自动生成 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 调试

使用 Python 调试器：

```python
import pdb; pdb.set_trace()
```

或使用 IDE 的调试功能。

---

## 性能优化建议

### 数据库索引

确保所有查询字段都有适当的索引：

```python
class Team(Base):
    __table_args__ = (
        Index('idx_teams_name_active', 'name', 'is_active'),
    )
```

### 查询优化

使用 `selectinload` 预加载关联数据：

```python
from sqlalchemy.orm import selectinload

result = await db.execute(
    select(Team)
    .options(selectinload(Team.members))
    .where(Team.team_id == team_id)
)
```

### 缓存

使用 Redis 缓存频繁访问的数据：

```python
from app.core.cache import cache

@cache(ttl=3600)  # 缓存 1 小时
async def get_team_stats(team_id: str):
    ...
```

---

## 安全最佳实践

### SQL 注入防护

使用 SQLAlchemy ORM，不要拼接 SQL：

```python
# ❌ 错误：容易 SQL 注入
await db.execute(f"SELECT * FROM teams WHERE name = '{name}'")

# ✅ 正确：使用参数化查询
await db.execute(
    select(Team).where(Team.name == name)
)
```

### 权限验证

始终验证用户权限：

```python
@router.post("/teams/{team_id}/sensitive")
async def sensitive_operation(
    team_id: str,
    member: dict = Depends(require_team_admin),
    db: AsyncSession = Depends(get_db)
):
    # 检查团队是否存在
    if not member.get("team"):
        raise NOT_FOUND

    # 执行操作
    ...
```

### 输入验证

使用 Pydantic 验证所有输入：

```python
class InputSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    amount: int = Field(..., gt=0)
```

---

## 社区贡献

欢迎贡献代码！请遵循以下指南：

1. Fork 项目
2. 创建特性分支
3. 提交变更
4. 推送到分支
5. 创建 Pull Request

---

## 联系方式

- GitHub: https://github.com/agentmemorymarket
- 邮件: dev@agentmemorymarket.com
- Discord: https://discord.gg/agentmemorymarket

---

*文档最后更新: 2024-01-01*
