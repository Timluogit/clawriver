# ClawRiver 团队协作功能 - 需求分析报告

## 1. 背景

### 1.1 当前状态
- ClawRiver 已完成向量搜索升级（P0任务1）
- 目前仅支持单用户场景
- 缺乏团队协作能力，限制了企业级应用场景

### 1.2 市场需求
- 所有主流 AI 记忆平台（MemGPT、LangChain Memory、AutoGPT Memory）都支持团队协作
- 企业客户需要多人共享、协作管理 AI 记忆
- 团队场景是知识之河的核心变现场景

---

## 2. 竞品功能对比

### 2.1 MemGPT 团队功能
**功能特点：**
- ✅ 团队创建和管理
- ✅ 成员邀请和管理
- ✅ 团队记忆共享
- ✅ 角色权限控制（Admin、Member、Read-only）
- ✅ 团队记忆版本管理
- ❌ 无团队积分池
- ❌ 无团队购买功能

**优势：** 权限模型清晰，版本控制完善
**劣势：** 缺少经济模型，不支持团队集体购买

### 2.2 LangChain Memory
**功能特点：**
- ✅ 团队工作空间
- ✅ 记忆共享和协作编辑
- ✅ 多环境隔离（Development、Staging、Production）
- ✅ 精细权限控制（读、写、删除、管理）
- ❌ 无角色系统
- ❌ 无积分和购买功能

**优势：** 权限控制最精细
**劣势：** 缺少角色系统和经济激励

### 2.3 AutoGPT Memory
**功能特点：**
- ✅ 团队记忆库
- ✅ 成员邀请（通过邀请链接）
- ✅ 记忆标签分类
- ✅ 基础权限（Owner、Member）
- ❌ 权限控制简单
- ❌ 无版本管理

**优势：** 简单易用
**劣势：** 权限模型过于简单

---

## 3. MVP 功能定义

### 3.1 核心功能（P0）

#### 3.1.1 团队管理
- **创建团队**
  - 团队名称（2-50字符）
  - 团队描述（0-500字符，可选）
  - 创建者自动成为 Owner

- **团队信息**
  - 团队 ID
  - 团队名称
  - 团队描述
  - 成员数量
  - 创建时间
  - Owner 信息

- **解散团队**
  - 仅 Owner 可执行
  - 清空所有团队成员
  - 保留团队记忆（标记为归档状态）

#### 3.1.2 成员管理
- **成员角色**
  - **Owner**：团队创建者，唯一且不可转移
    - 权限：解散团队、添加/移除 Admin、添加/移除 Member、编辑团队信息
  - **Admin**：团队管理员
    - 权限：添加/移除 Member、编辑团队信息、管理团队记忆
  - **Member**：团队成员
    - 权限：查看团队记忆、创建团队记忆（需有权限）

- **邀请成员**
  - 生成 8 位邀请码（有效期 7 天）
  - 通过邀请码加入团队
  - 邀请码使用后失效

- **成员操作**
  - 移除成员（Owner/Admin）
  - 成员自行退出（除 Owner）
  - 查看成员列表

#### 3.1.3 团队记忆
- **创建团队记忆**
  - 记忆归属：team_id
  - 创建者信息记录
  - 记忆所有权：团队共享（非个人）

- **记忆权限**
  - **Owner**：所有操作权限
  - **Admin**：编辑、删除、查看
  - **Member**：查看、创建（取决于设置）
  - **未授权**：仅可见性控制

- **记忆可见性**
  - **team_only**：仅团队内可见
  - **public**：所有人可见（可选功能，P1）

- **记忆编辑**
  - 支持多人协作编辑
  - 记录编辑历史
  - 版本管理（基于现有 MemoryVersion）

#### 3.1.4 团队积分
- **团队积分池**
  - 团队共享积分账户
  - 记录充值和消费流水
  - 支持成员向团队积分池充值

- **团队购买**
  - 使用团队积分购买记忆
  - 购买记录关联团队而非个人
  - 购买的记忆自动进入团队记忆库

- **积分分配**
  - 成员贡献记录（充值金额）
  - 按贡献比例分配收益（如果团队出售记忆）
  - 可查看团队积分流水

### 3.2 扩展功能（P1 - 暂不实现）
- 团队审核机制（人工审核）
- 复杂权限继承（部门、项目组）
- 团队审计日志（详细操作日志）
- 团队统计分析（活动数据、ROI分析）
- 记忆可见性控制（public）
- 团队记忆导出
- 团队模板和预设

---

## 4. 数据模型设计

### 4.1 Team 表

```python
class Team(Base):
    """团队表"""
    __tablename__ = "teams"

    team_id = Column(String(50), primary_key=True, default=lambda: gen_id("team"))

    # 基本信息
    name = Column(String(50), nullable=False, index=True)  # 团队名称
    description = Column(Text, nullable=True)  # 团队描述

    # Owner 信息
    owner_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    # 统计
    member_count = Column(Integer, default=1)  # 成员数量（含 Owner）
    memory_count = Column(Integer, default=0)  # 团队记忆数量

    # 积分池
    credits = Column(Integer, default=0)  # 团队积分
    total_earned = Column(Integer, default=0)  # 总收入
    total_spent = Column(Integer, default=0)  # 总支出

    # 状态
    is_active = Column(Boolean, default=True)  # 是否活跃
    archived_at = Column(DateTime, nullable=True)  # 归档时间（解散时）

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="team")
    invite_codes = relationship("TeamInviteCode", back_populates="team", cascade="all, delete-orphan")
    credit_transactions = relationship("TeamCreditTransaction", back_populates="team", cascade="all, delete-orphan")
```

### 4.2 TeamMember 表

```python
class TeamMember(Base):
    """团队成员表"""
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, autoincrement=True)

    team_id = Column(String(50), ForeignKey("teams.team_id"), nullable=False, index=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=False, index=True)

    # 角色枚举
    role = Column(String(20), nullable=False, default="member")  # owner/admin/member

    # 元数据
    joined_at = Column(DateTime, server_default=func.now())  # 加入时间
    left_at = Column(DateTime, nullable=True)  # 离开时间（退出或被移除）
    is_active = Column(Boolean, default=True)  # 是否活跃

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    team = relationship("Team", back_populates="members")
    agent = relationship("Agent")
```

**索引设计：**
- `idx_team_id`: (team_id)
- `idx_agent_id`: (agent_id)
- `idx_team_agent`: (team_id, agent_id) - 唯一索引（一个用户在一个团队只能有一个角色）

### 4.3 TeamInviteCode 表

```python
class TeamInviteCode(Base):
    """团队邀请码表"""
    __tablename__ = "team_invite_codes"

    invite_code_id = Column(String(50), primary_key=True, default=lambda: gen_id("inv"))

    team_id = Column(String(50), ForeignKey("teams.team_id"), nullable=False, index=True)
    code = Column(String(8), unique=True, nullable=False, index=True)  # 8位邀请码

    # 状态
    is_active = Column(Boolean, default=True)  # 是否有效
    used_by_agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True)  # 使用者
    used_at = Column(DateTime, nullable=True)  # 使用时间

    # 有效期
    expires_at = Column(DateTime, nullable=False)  # 过期时间（默认7天）

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    team = relationship("Team", back_populates="invite_codes")
    used_by = relationship("Agent")
```

**索引设计：**
- `idx_code`: (code) - 唯一索引
- `idx_team_id`: (team_id)
- `idx_expires_at`: (expires_at) - 用于定时清理过期邀请码

### 4.4 TeamCreditTransaction 表

```python
class TeamCreditTransaction(Base):
    """团队积分交易流水表"""
    __tablename__ = "team_credit_transactions"

    tx_id = Column(String(50), primary_key=True, default=lambda: gen_id("tctx"))

    team_id = Column(String(50), ForeignKey("teams.team_id"), nullable=False, index=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id"), nullable=True, index=True)  # 操作者（充值时为成员，其他可为空）

    tx_type = Column(String(50), nullable=False)  # recharge（充值）/purchase（购买）/sale（销售）/refund（退款）
    amount = Column(Integer, nullable=False)  # 正数=收入，负数=支出
    balance_after = Column(Integer, nullable=False)  # 交易后余额

    related_id = Column(String(50), nullable=True)  # 关联ID（记忆ID、购买ID等）
    description = Column(String(200), nullable=True)  # 说明

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    team = relationship("Team", back_populates="credit_transactions")
    agent = relationship("Agent")
```

**索引设计：**
- `idx_team_id`: (team_id)
- `idx_agent_id`: (agent_id)
- `idx_created_at`: (created_at) - 用于时间查询

### 4.5 Memory 表扩展

```python
# 在 Memory 表中添加以下字段

class Memory(Base):
    """记忆表"""
    # ... 现有字段 ...

    # 团队协作字段
    team_id = Column(String(50), ForeignKey("teams.team_id"), nullable=True, index=True)  # 所属团队
    team_access_level = Column(String(20), default="private")  # private/team_only/public

    # 关系
    team = relationship("Team", back_populates="memories")
```

**索引设计：**
- `idx_team_id`: (team_id)
- `idx_team_access_level`: (team_access_level)

---

## 5. 权限模型设计（RBAC）

### 5.1 角色定义

| 角色 | 权限级别 | 说明 |
|------|---------|------|
| **Owner** | 最高权限 | 团队创建者，唯一且不可转移 |
| **Admin** | 管理权限 | 团队管理员，可管理成员和记忆 |
| **Member** | 普通权限 | 团队成员，可查看和创建记忆（取决于设置） |

### 5.2 权限矩阵

| 操作 | Owner | Admin | Member |
|------|-------|-------|--------|
| 解散团队 | ✅ | ❌ | ❌ |
| 编辑团队信息（名称、描述） | ✅ | ✅ | ❌ |
| 添加 Admin | ✅ | ❌ | ❌ |
| 移除 Admin | ✅ | ❌ | ❌ |
| 添加 Member | ✅ | ✅ | ❌ |
| 移除 Member | ✅ | ✅ | ❌ |
| 查看成员列表 | ✅ | ✅ | ✅ |
| 创建邀请码 | ✅ | ✅ | ❌ |
| 查看团队积分 | ✅ | ✅ | ✅ |
| 向团队积分池充值 | ✅ | ✅ | ✅ |
| 使用团队积分购买记忆 | ✅ | ✅ | ❌ |
| 创建团队记忆 | ✅ | ✅ | ✅ |
| 编辑团队记忆 | ✅ | ✅ | ❌ |
| 删除团队记忆 | ✅ | ✅ | ❌ |
| 查看团队记忆 | ✅ | ✅ | ✅ |

### 5.3 权限检查逻辑

```python
class TeamPermissionChecker:
    """团队权限检查器"""

    @staticmethod
    def can_dismiss_team(role: str) -> bool:
        return role == "owner"

    @staticmethod
    def can_edit_team_info(role: str) -> bool:
        return role in ["owner", "admin"]

    @staticmethod
    def can_add_member(role: str) -> bool:
        return role in ["owner", "admin"]

    @staticmethod
    def can_remove_member(target_role: str, operator_role: str) -> bool:
        """移除成员：Admin不能移除Owner"""
        if operator_role not in ["owner", "admin"]:
            return False
        if target_role == "owner":
            return False
        if operator_role == "admin" and target_role == "admin":
            return False
        return True

    @staticmethod
    def can_create_invite_code(role: str) -> bool:
        return role in ["owner", "admin"]

    @staticmethod
    def can_purchase_with_team_credits(role: str) -> bool:
        return role in ["owner", "admin"]

    @staticmethod
    def can_edit_memory(role: str, memory_owner_id: str, operator_id: str) -> bool:
        """编辑记忆：Owner/Admin可编辑所有记忆，Member仅能编辑自己创建的"""
        if role in ["owner", "admin"]:
            return True
        if role == "member" and memory_owner_id == operator_id:
            return True
        return False

    @staticmethod
    def can_delete_memory(role: str) -> bool:
        return role in ["owner", "admin"]
```

---

## 6. 向后兼容性设计

### 6.1 单用户场景保护
- 所有新增表和字段均为 **可选**（nullable=True）
- 现有 API 不受影响，继续支持单用户流程
- 现有 Memory 表的 `seller_agent_id` 字段保持不变

### 6.2 数据隔离
- 团队数据通过 `team_id` 字段隔离
- 单用户记忆 `team_id` 为 NULL
- 权限检查先判断是否为团队记忆，再检查角色权限

### 6.3 API 兼容
```python
# 现有 API 保持不变
POST /api/v1/memories          # 创建个人记忆
GET  /api/v1/memories/{id}     # 获取记忆（自动判断权限）

# 新增 API（不影响现有 API）
POST /api/v1/teams             # 创建团队
POST /api/v1/teams/{id}/invite # 生成邀请码
POST /api/v1/teams/{id}/members # 添加成员
POST /api/v1/memories/team     # 创建团队记忆
POST /api/v1/teams/{id}/purchase # 使用团队积分购买
```

---

## 7. 数据安全设计

### 7.1 数据隔离
- 团队数据严格隔离，通过 `team_id` 索引
- 权限检查在 API 层和数据库层双重验证

### 7.2 最小权限原则
- 新用户默认为 Member 角色
- Member 默认仅查看权限，不可编辑团队记忆
- 所有写操作需要显式权限检查

### 7.3 审计日志（P1，暂不实现）
- 记录所有团队操作日志
- 支持查询团队变更历史

---

## 8. MVP 验收标准

### 8.1 功能验收
- [ ] 创建团队并自动成为 Owner
- [ ] 生成邀请码并成功邀请成员加入
- [ ] 成员角色正确分配（Owner/Admin/Member）
- [ ] Owner 可以解散团队
- [ ] Admin 可以添加和移除 Member
- [ ] 创建团队记忆并正确关联 team_id
- [ ] 团队积分池充值和消费
- [ ] 使用团队积分购买记忆并自动进入团队记忆库

### 8.2 性能验收
- [ ] 创建团队 < 100ms
- [ ] 成员邀请 < 200ms
- [ ] 权限检查 < 50ms
- [ ] 团队记忆查询 < 200ms（支持分页）

### 8.3 安全验收
- [ ] 权限检查覆盖所有写操作
- [ ] 团队数据隔离严格
- [ ] 无 SQL 注入风险
- [ ] 无权限绕过漏洞

---

## 9. 风险评估

### 9.1 技术风险
| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 权限模型设计复杂度高 | 高 | 中 | 简化 MVP 权限，仅 3 个角色 |
| 向后兼容性问题 | 中 | 低 | 新字段 nullable，严格测试 |
| 团队积分池并发问题 | 中 | 中 | 使用数据库事务和乐观锁 |
| 数据迁移问题 | 低 | 低 | 提供迁移脚本，支持回滚 |

### 9.2 业务风险
| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 用户团队协作需求不足 | 中 | 低 | MVP 快速验证，根据反馈调整 |
| 团队积分滥用 | 中 | 中 | 限制单次充值金额，风控监控 |
| 团队记忆冲突 | 低 | 中 | 版本管理和冲突解决机制 |

---

## 10. 下一步建议

### 10.1 阶段1：数据库设计（推荐）
1. 创建数据库迁移脚本
2. 在开发环境验证表结构
3. 编写数据库测试用例
4. 评估索引优化

### 10.2 阶段2：核心功能开发
1. 实现团队创建和管理 API
2. 实现成员邀请和管理 API
3. 实现团队权限检查中间件
4. 编写单元测试

### 10.3 阶段3：记忆协作功能
1. 扩展 Memory 表（添加 team_id）
2. 实现团队记忆创建和查询 API
3. 实现团队积分池逻辑
4. 集成到现有购买流程

### 10.4 阶段4：测试和文档
1. 端到端测试
2. API 文档（OpenAPI/Swagger）
3. 用户使用指南
4. 开发者文档

---

## 附录：数据库迁移脚本（示例）

```sql
-- 创建团队表
CREATE TABLE teams (
    team_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    owner_agent_id VARCHAR(50) NOT NULL,
    member_count INTEGER DEFAULT 1,
    memory_count INTEGER DEFAULT 0,
    credits INTEGER DEFAULT 0,
    total_earned INTEGER DEFAULT 0,
    total_spent INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    archived_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX idx_teams_name ON teams(name);
CREATE INDEX idx_teams_owner ON teams(owner_agent_id);

-- 创建团队成员表
CREATE TABLE team_members (
    id SERIAL PRIMARY KEY,
    team_id VARCHAR(50) NOT NULL,
    agent_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    left_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    UNIQUE(team_id, agent_id)
);

CREATE INDEX idx_team_members_team ON team_members(team_id);
CREATE INDEX idx_team_members_agent ON team_members(agent_id);

-- 创建邀请码表
CREATE TABLE team_invite_codes (
    invite_code_id VARCHAR(50) PRIMARY KEY,
    team_id VARCHAR(50) NOT NULL,
    code VARCHAR(8) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    used_by_agent_id VARCHAR(50),
    used_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (used_by_agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX idx_team_invite_codes_code ON team_invite_codes(code);
CREATE INDEX idx_team_invite_codes_team ON team_invite_codes(team_id);
CREATE INDEX idx_team_invite_codes_expires ON team_invite_codes(expires_at);

-- 创建团队积分交易表
CREATE TABLE team_credit_transactions (
    tx_id VARCHAR(50) PRIMARY KEY,
    team_id VARCHAR(50) NOT NULL,
    agent_id VARCHAR(50),
    tx_type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    related_id VARCHAR(50),
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX idx_team_credit_tx_team ON team_credit_transactions(team_id);
CREATE INDEX idx_team_credit_tx_agent ON team_credit_transactions(agent_id);
CREATE INDEX idx_team_credit_tx_created ON team_credit_transactions(created_at);

-- 扩展记忆表
ALTER TABLE memories
ADD COLUMN team_id VARCHAR(50),
ADD COLUMN team_access_level VARCHAR(20) DEFAULT 'private',
ADD FOREIGN KEY (team_id) REFERENCES teams(team_id);

CREATE INDEX idx_memories_team ON memories(team_id);
CREATE INDEX idx_memories_access_level ON memories(team_access_level);
```

---

**文档版本：** v1.0
**最后更新：** 2026-03-23
**作者：** OpenClaw AI Assistant
