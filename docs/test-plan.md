# 📋 ClawRiver - 完整测试方案

> **版本**: v2.0  
> **日期**: 2026-03-23  
> **覆盖**: P0-P4 全部23个功能模块  
> **当前状态**: 416 passed / 110 failed / 93 errors / 2 skipped (共621个测试)

---

## 1. 测试目标

### 1.1 总体目标
- 确保所有23个功能模块正常工作
- 修复当前110个失败和93个错误的测试
- 验证性能指标达标
- 产出完整的测试报告和Bug清单

### 1.2 质量指标
| 指标 | 目标 | 当前值 |
|------|------|--------|
| 单元测试通过率 | ≥ 95% | 67.2% |
| 集成测试通过率 | ≥ 90% | - |
| 性能测试达标率 | 100% | - |
| Bug修复率 | 100% | - |

---

## 2. 测试范围

### 2.1 P0-P2 基础功能（13个模块）
| # | 模块 | 测试文件 | 测试数 | 状态 |
|---|------|---------|--------|------|
| 1 | 记忆存储和检索 | test_api.py, test_services.py | ~50 | 🔄 |
| 2 | 向量搜索 | test_qdrant_client.py | ~30 | 🔄 |
| 3 | 混合搜索 | test_search_integration.py | ~25 | 🔄 |
| 4 | 团队协作 | test_team_*.py | ~90 | ❌ |
| 5 | 市场交易 | test_api.py | ~20 | 🔄 |
| 6 | 监控系统 | test_monitoring.py | ~25 | 🔄 |
| 7 | 审计日志 | test_audit_logs.py | ~30 | ❌ |
| 8 | 搜索分析 | test_search_analytics.py | ~15 | ❌ |
| 9 | MCP工具 | test_mcp_tools.py | ~80 | 🔄 |
| 10 | 搜索缓存 | test_search_cache.py | ~20 | ❌ |
| 11 | 数字签名 | test_digital_signature*.py | ~40 | ❌ |
| 12 | 异常检测 | test_anomaly_detection.py | ~40 | ❌ |
| 13 | Cross-Encoder重排 | test_cross_encoder.py | ~30 | 🔄 |

### 2.2 P3 高级功能（6个模块）
| # | 模块 | 测试文件 | 测试数 | 状态 |
|---|------|---------|--------|------|
| 14 | 用户画像系统 | test_user_profiles.py | ~15 | ❌ |
| 15 | 自动遗忘机制 | test_auto_forget.py | ~30 | 🔄 |
| 16 | 外部数据源集成 | test_external_sources.py | ~50 | 🔄 |
| 17 | MCP服务器 | test_mcp_server.py | ~40 | 🔄 |
| 18 | 多Agent并行推理 | test_multi_agent.py | ~40 | 🔄 |
| 19 | 内存运行架构 | test_in_memory.py | ~60 | 🔄 |

### 2.3 P4 企业功能（4个模块）
| # | 模块 | 测试文件 | 测试数 | 状态 |
|---|------|---------|--------|------|
| 20 | 评估框架 | test_evaluation.py | ~40 | 🔄 |
| 21 | 细粒度权限 | test_advanced_permissions*.py | ~80 | 🔄 |
| 22 | 高可用部署 | docker-compose*.yml | 手动测试 | - |
| 23 | 智能重排 | test_smart_reranking.py | ~50 | 🔄 |

---

## 3. 测试环境

### 3.1 硬件环境
- **主机**: sss的Mac mini (macOS Darwin 25.3.0, arm64)
- **Python**: 3.14.3 (虚拟环境: `venv/`)
- **包管理**: pip

### 3.2 依赖服务
| 服务 | 状态 | 用途 |
|------|------|------|
| SQLite (内存) | ✅ 可用 | 测试数据库 |
| Redis | ❌ 未启动 | 搜索缓存 |
| Qdrant | ❌ 未启动 | 向量搜索 |

### 3.3 必需环境变量
```bash
KEY_ENCRYPTION_SALT=<hex_salt>  # 必需，64字符hex
```

### 3.4 Python 依赖
```bash
cd /Users/sss/.openclaw/workspace/memory-market
venv/bin/pip install -r requirements.txt
```

---

## 4. 测试工具

| 工具 | 版本 | 用途 |
|------|------|------|
| pytest | 9.0.2 | 测试框架 |
| pytest-asyncio | 最新 | 异步测试支持 |
| httpx | 最新 | API测试客户端 |
| coverage | 最新 | 代码覆盖率 |
| redis | 7.3.0 | Redis客户端 |

---

## 5. 测试流程

### 5.1 五阶段测试流程

```
阶段1: 单元测试 → 阶段2: 集成测试 → 阶段3: 性能测试 → 阶段4: 端到端测试 → 阶段5: Bug修复
```

### 5.2 详细流程

#### 阶段1: 单元测试（30分钟）
```bash
# 设置环境变量
export KEY_ENCRYPTION_SALT=73616c7431323334353637383930313233343536373839303132333435363738

# 运行所有单元测试
cd /Users/sss/.openclaw/workspace/memory-market
venv/bin/python -m pytest tests/ -v --tb=short -x -m "not integration"

# 分模块运行
venv/bin/python -m pytest tests/test_api.py -v
venv/bin/python -m pytest tests/test_services.py -v
venv/bin/python -m pytest tests/test_in_memory.py -v
venv/bin/python -m pytest tests/test_multi_agent.py -v
venv/bin/python -m pytest tests/test_external_sources.py -v
venv/bin/python -m pytest tests/test_cross_encoder.py -v
venv/bin/python -m pytest tests/test_evaluation.py -v
venv/bin/python -m pytest tests/test_smart_reranking.py -v
venv/bin/python -m pytest tests/test_auto_forget.py -v
venv/bin/python -m pytest tests/test_mcp_server.py -v
```

#### 阶段2: 集成测试（30分钟）
```bash
# 运行集成测试
venv/bin/python -m pytest tests/ -v -k "integration" --tb=short

# 重点关注模块间交互
venv/bin/python -m pytest tests/test_search_integration.py -v
venv/bin/python -m pytest tests/e2e_team_collab.py -v
```

#### 阶段3: 性能测试（30分钟）
```bash
# 运行性能测试脚本
venv/bin/python scripts/performance_test.py

# 运行已有性能测试
venv/bin/python -m pytest tests/performance_team.py -v
```

#### 阶段4: 端到端测试（30分钟）
```bash
# 运行E2E测试
venv/bin/python -m pytest tests/e2e_team_collab.py -v

# 手动测试流程
# 1. 启动服务器: venv/bin/uvicorn app.main:app --reload
# 2. 浏览器访问: http://localhost:8000
# 3. 执行完整业务流程
```

#### 阶段5: Bug修复和优化（60分钟）
```bash
# 1. 分析失败测试
venv/bin/python -m pytest tests/ --tb=long -v 2>&1 | tee test-failures.txt

# 2. 修复代码问题
# 3. 重新验证
venv/bin/python -m pytest tests/ -v --tb=short

# 4. 生成覆盖率报告
venv/bin/python -m pytest tests/ --cov=app --cov-report=html
```

---

## 6. 已知问题分类

### 6.1 环境依赖问题（93 errors）
- **Redis未启动**: 搜索缓存相关测试全部失败
- **环境变量缺失**: `KEY_ENCRYPTION_SALT` 未设置

### 6.2 代码质量问题（110 failures）
- **Pydantic模型验证**: TeamMemoryResponse, TeamActivityLog 缺少字段
- **Pydantic弃用警告**: `min_items`/`max_items` 应改为 `min_length`/`max_length`
- **类配置弃用**: `class Config` 应改为 `ConfigDict`

### 6.3 逻辑错误
- **评估框架**: `failed_cases` 计数错误
- **异常检测**: fixture 设置问题

---

## 7. 测试数据

### 7.1 测试数据文件
- `tests/data/test_memories.json` - 测试记忆数据
- `tests/data/test_users.json` - 测试用户数据
- `tests/data/test_teams.json` - 测试团队数据

### 7.2 数据生成
```bash
# 使用 conftest.py 中的 fixtures 自动生成
# 或手动创建测试数据文件
```

---

## 8. 输出物

| 文档 | 路径 | 内容 |
|------|------|------|
| 测试方案 | `docs/test-plan.md` | 本文档 |
| 测试报告 | `docs/test-report.md` | 测试执行结果 |
| Bug清单 | `docs/bug-list.md` | 所有发现的Bug |
| 性能报告 | `docs/performance-report.md` | 性能测试结果 |
| 优化建议 | `docs/optimization-suggestions.md` | 代码优化建议 |

---

## 9. 时间安排

| 阶段 | 时间 | 产出 |
|------|------|------|
| 阶段1: 单元测试 | 30分钟 | 测试结果、Bug清单 |
| 阶段2: 集成测试 | 30分钟 | 集成测试报告 |
| 阶段3: 性能测试 | 30分钟 | 性能报告 |
| 阶段4: 端到端测试 | 30分钟 | E2E测试报告 |
| 阶段5: Bug修复 | 60分钟 | 修复代码、更新测试 |
| **总计** | **3小时** | 完整测试报告 |

---

## 10. 风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Redis不可用 | 缓存测试失败 | 使用mock或跳过 |
| Qdrant不可用 | 向量搜索测试失败 | 使用内存引擎替代 |
| Python版本兼容 | 部分测试失败 | 检查Python 3.14兼容性 |
| 依赖缺失 | 导入错误 | 完善requirements.txt |

---

## 附录

### A. 快速命令参考
```bash
# 设置环境
cd /Users/sss/.openclaw/workspace/memory-market
export KEY_ENCRYPTION_SALT=73616c7431323334353637383930313233343536373839303132333435363738

# 运行测试
venv/bin/python -m pytest tests/ -v --tb=short -x

# 运行特定测试
venv/bin/python -m pytest tests/test_api.py::test_create_memory -v

# 生成覆盖率
venv/bin/python -m pytest tests/ --cov=app --cov-report=html

# 运行测试脚本
bash scripts/run_tests.sh
```

### B. 测试标记
- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.performance` - 性能测试
- `@pytest.mark.e2e` - 端到端测试
