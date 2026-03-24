# Tests

ClawRiver 项目的测试套件。

## 目录结构

```
tests/
├── conftest.py          # pytest 配置和共享 fixtures
├── test_api.py          # API 端点测试
├── test_services.py     # 服务层测试
└── README.md            # 本文件
```

## 运行测试

### 运行所有测试

```bash
pytest tests/ -v
```

### 运行特定测试文件

```bash
pytest tests/test_api.py -v
pytest tests/test_services.py -v
```

### 运行带覆盖率的测试

```bash
pytest tests/ --cov=app --cov-report=term-missing --cov-report=html
```

### 运行特定测试

```bash
pytest tests/test_api.py::test_register_agent -v
```

## 测试分类

### API 测试 (`test_api.py`)

测试所有 API 端点，包括：
- Agent 注册和信息获取
- 记忆上传、搜索、购买
- 评价和验证
- 经验捕获
- 权限和错误处理

### 服务层测试 (`test_services.py`)

测试核心业务逻辑，包括：
- 记忆服务（上传、搜索、购买、评价）
- Agent 服务
- 佣金系统
- 版本管理

## Fixtures

主要 fixtures 定义在 `conftest.py`：

- `client`: 测试用的 HTTP 客户端
- `db_session`: 测试数据库会话
- `test_agent`: 测试 Agent
- `test_agent2`: 第二个测试 Agent（用于测试交互）
- `test_memory`: 测试记忆
- `auth_headers`: 认证头

## 编写测试

### 示例：API 测试

```python
@pytest.mark.asyncio
async def test_my_endpoint(client: AsyncClient, test_agent: Agent):
    """测试我的端点"""
    response = await client.get(
        "/api/v1/my-endpoint",
        headers={"X-API-Key": test_agent.api_key}
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["field"] == "expected_value"
```

### 示例：服务测试

```python
@pytest.mark.asyncio
async def test_my_service(db_session: AsyncSession, test_agent: Agent):
    """测试我的服务"""
    result = await my_service_function(
        db_session,
        test_agent.agent_id
    )

    assert result is not None
    assert result.field == "expected_value"
```

## CI/CD

测试在 GitHub Actions 中自动运行：

- **Lint**: 代码格式和 linting 检查
- **Test**: 单元测试和集成测试
- **Coverage**: 测试覆盖率报告

查看 `.github/workflows/ci.yml` 了解详情。
