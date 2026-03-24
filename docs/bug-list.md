# 🐛 ClawRiver - Bug清单

> **版本**: v1.0  
> **日期**: 2026-03-23  
> **来源**: 测试执行结果  
> **总计**: 203个问题 (110 failures + 93 errors)

---

## Bug分类统计

| 类别 | 数量 | 优先级 | 状态 |
|------|------|--------|------|
| 环境依赖问题 | 93 | P0 | 🔴 待修复 |
| Pydantic模型错误 | 25 | P0 | 🔴 待修复 |
| 业务逻辑错误 | 30 | P1 | 🔴 待修复 |
| 代码弃用警告 | 240 | P2 | 🟡 待更新 |
| **总计** | **388** | - | - |

---

## P0 - 严重问题 (阻塞测试)

### BUG-001: Redis服务未启动
- **类别**: 环境依赖
- **影响**: 所有搜索缓存相关测试 (20+ 测试)
- **错误**: `Redis ping failed: Error Multiple exceptions: [Errno 61] Connect call failed ('127.0.0.1', 6379)`
- **文件**: `app/cache/redis_client.py`
- **解决方案**: 
  1. 启动Redis服务: `brew services start redis`
  2. 或添加Redis mock到测试配置
- **状态**: 🔴 待修复

### BUG-002: KEY_ENCRYPTION_SALT环境变量缺失
- **类别**: 环境依赖
- **影响**: 数字签名相关测试 (40+ 测试)
- **错误**: `ValueError: KEY_ENCRYPTION_SALT environment variable is required`
- **文件**: `app/services/key_management_service.py:58`
- **解决方案**: 
  1. 设置环境变量: `export KEY_ENCRYPTION_SALT=73616c7431323334353637383930313233343536373839303132333435363738`
  2. 或在测试conftest中设置默认值
- **状态**: 🔴 待修复

### BUG-003: TeamMemoryResponse模型缺少字段
- **类别**: Pydantic模型错误
- **影响**: 团队协作模块测试 (40+ 测试)
- **错误**: `ValidationError: 7 validation errors for TeamMemoryResponse`
- **文件**: `app/models/schemas.py`
- **原因**: 测试数据与模型定义不匹配
- **解决方案**: 更新模型定义或测试数据
- **状态**: 🔴 待修复

### BUG-004: TeamActivityLog模型缺少字段
- **类别**: Pydantic模型错误
- **影响**: 团队活动日志测试
- **错误**: `ValidationError: 2 validation errors for TeamActivityLog`
- **文件**: `app/models/schemas.py`
- **解决方案**: 更新模型定义
- **状态**: 🔴 待修复

### BUG-005: redis.asyncio模块不存在
- **类别**: 依赖版本问题
- **影响**: 测试收集阶段
- **错误**: `ModuleNotFoundError: No module named 'redis.asyncio'`
- **文件**: `app/cache/redis_client.py:11`
- **原因**: redis包版本不支持asyncio
- **解决方案**: `venv/bin/pip install redis>=4.2.0`
- **状态**: 🔴 待修复

---

## P1 - 高优先级问题

### BUG-006: 评估框架failed_cases计数错误
- **类别**: 业务逻辑错误
- **影响**: test_evaluation.py
- **错误**: `assert result.failed_cases == 2` 失败，实际为0
- **文件**: `app/eval/evaluation.py`
- **原因**: 错误案例未正确计入failed_cases
- **解决方案**: 修复评估逻辑
- **状态**: 🔴 待修复

### BUG-007: 异常检测fixture设置问题
- **类别**: 测试配置问题
- **影响**: test_anomaly_detection.py
- **错误**: `ERROR at setup of test_frequent_failed_login_rule`
- **文件**: `tests/test_anomaly_detection.py`
- **原因**: fixture依赖问题
- **解决方案**: 修复fixture配置
- **状态**: 🔴 待修复

### BUG-008: 审计日志测试数据库会话问题
- **类别**: 测试配置问题
- **影响**: test_audit_logs.py (15+ 测试)
- **错误**: 多种数据库会话相关错误
- **文件**: `tests/test_audit_logs.py`
- **原因**: 数据库fixture配置问题
- **解决方案**: 修复conftest.py中的数据库fixture
- **状态**: 🔴 待修复

### BUG-009: 搜索分析测试失败
- **类别**: 业务逻辑错误
- **影响**: test_search_analytics.py (10+ 测试)
- **错误**: 多种断言失败
- **文件**: `app/api/search_analytics.py`
- **原因**: 分析逻辑错误
- **解决方案**: 修复分析逻辑
- **状态**: 🔴 待修复

### BUG-010: 用户画像提取测试失败
- **类别**: 业务逻辑错误
- **影响**: test_user_profiles.py
- **错误**: `test_extract_from_conversation` 失败
- **文件**: `app/api/user_profiles.py`
- **原因**: 画像提取逻辑错误
- **解决方案**: 修复提取逻辑
- **状态**: 🔴 待修复

### BUG-011: 权限过期测试失败
- **类别**: 业务逻辑错误
- **影响**: test_permissions.py
- **错误**: `test_permission_expiration` 失败
- **文件**: `app/api/permissions.py`
- **原因**: 过期逻辑错误
- **解决方案**: 修复过期检查逻辑
- **状态**: 🔴 待修复

### BUG-012: 批量权限操作失败
- **类别**: 业务逻辑错误
- **影响**: test_permissions.py
- **错误**: `test_bulk_permission_operations` 失败
- **文件**: `app/api/permissions.py`
- **原因**: 批量操作逻辑错误
- **解决方案**: 修复批量操作
- **状态**: 🔴 待修复

---

## P2 - 中优先级问题

### BUG-013: Pydantic弃用警告 - min_items/max_items
- **类别**: 代码弃用
- **影响**: 240个警告
- **文件**: `app/models/schemas.py:225`
- **错误**: `PydanticDeprecatedSince20: 'min_items' is deprecated`
- **解决方案**: 替换为 `min_length`/`max_length`
- **状态**: 🟡 待更新

### BUG-014: Pydantic弃用警告 - class Config
- **类别**: 代码弃用
- **影响**: 多个文件
- **文件**: 
  - `app/api/audit_logs.py:37`
  - `app/api/permissions.py:60, 77, 96`
  - `app/api/advanced_permissions.py:40, 134`
- **错误**: `Support for class-based 'config' is deprecated`
- **解决方案**: 使用 `ConfigDict`
- **状态**: 🟡 待更新

### BUG-015: 数字签名中间件集成问题
- **类别**: 集成问题
- **影响**: test_digital_signature.py
- **错误**: 中间件测试失败
- **文件**: `app/api/audit_signature_middleware.py`
- **解决方案**: 修复中间件集成
- **状态**: 🟡 待更新

---

## P3 - 低优先级问题

### BUG-016: 测试数据不完整
- **类别**: 测试数据
- **影响**: 多个测试
- **说明**: 部分测试缺少完整的测试数据
- **解决方案**: 完善测试数据fixtures
- **状态**: ⬜ 待处理

### BUG-017: 测试文档不完整
- **类别**: 文档
- **影响**: 测试可维护性
- **说明**: 部分测试缺少注释和说明
- **解决方案**: 完善测试文档
- **状态**: ⬜ 待处理

---

## Bug修复流程

```
1. 确认Bug
   ├─ 复现问题
   └─ 记录详细信息

2. 分析原因
   ├─ 定位代码位置
   └─ 理解问题本质

3. 制定方案
   ├─ 设计修复方案
   └─ 评估影响范围

4. 实施修复
   ├─ 修改代码
   └─ 更新测试

5. 验证修复
   ├─ 运行相关测试
   └─ 确认问题解决

6. 更新状态
   ├─ 更新Bug清单
   └─ 更新测试报告
```

---

## 修复优先级建议

### 立即修复 (P0)
1. BUG-005: 安装redis>=4.2.0
2. BUG-001: 启动Redis或添加mock
3. BUG-002: 设置环境变量
4. BUG-003: 修复TeamMemoryResponse模型
5. BUG-004: 修复TeamActivityLog模型

### 本周修复 (P1)
6. BUG-006: 修复评估框架逻辑
7. BUG-007: 修复异常检测fixture
8. BUG-008: 修复审计日志测试
9. BUG-009: 修复搜索分析逻辑
10. BUG-010: 修复用户画像提取
11. BUG-011: 修复权限过期逻辑
12. BUG-012: 修复批量权限操作

### 下周修复 (P2)
13. BUG-013: 更新Pydantic语法
14. BUG-014: 更新Pydantic配置
15. BUG-015: 修复中间件集成

### 持续改进 (P3)
16. BUG-016: 完善测试数据
17. BUG-017: 完善测试文档

---

## 统计信息

| 类别 | 数量 | 占比 |
|------|------|------|
| 环境依赖 | 93 | 24.0% |
| Pydantic错误 | 25 | 6.4% |
| 业务逻辑 | 30 | 7.7% |
| 代码弃用 | 240 | 61.9% |
| **总计** | **388** | **100%** |

---

## 附录

### A. 测试失败详情
```bash
# 查看详细失败信息
venv/bin/python -m pytest tests/ --tb=long -v 2>&1 | tee test-failures.txt

# 按模块查看
venv/bin/python -m pytest tests/test_team_models.py --tb=short -v
```

### B. 环境配置
```bash
# 快速设置环境
export KEY_ENCRYPTION_SALT=73616c7431323334353637383930313233343536373839303132333435363738
brew services start redis
venv/bin/pip install redis>=4.2.0
```
