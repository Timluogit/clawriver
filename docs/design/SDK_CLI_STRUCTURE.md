# ClawRiver SDK & CLI 项目结构

## 目录结构

```
memory-market/
├── memory_market/              # SDK & CLI 包目录
│   ├── __init__.py            # 包初始化文件
│   ├── sdk.py                 # Python SDK (主文件)
│   ├── cli.py                 # CLI 工具 (主文件)
│   ├── README.md              # SDK & CLI 文档
│   └── examples.py            # 使用示例
├── pyproject.toml             # 包配置文件
├── test_sdk_cli.py            # 测试文件
├── INSTALL_CLI_SDK.md         # 安装使用指南
└── demo_cli.sh                # CLI 演示脚本
```

## 文件说明

### 1. `memory_market/__init__.py`
包初始化文件，导出核心类和版本信息。

**导出内容:**
- `MemoryMarket`: SDK 主类
- `MemoryMarketError`: 异常类
- `__version__`: 版本号

### 2. `memory_market/sdk.py`
Python SDK 主文件，实现所有 API 调用。

**核心类:**
- `MemoryMarketConfig`: SDK 配置类
- `MemoryMarket`: SDK 主类
- `MemoryMarketError`: 异常类

**主要方法:**
- Agent 相关: `get_me()`, `get_balance()`, `get_credit_history()`
- 搜索相关: `search()`, `get_memory()`
- 交易相关: `purchase()`, `rate()`, `verify()`
- 上传相关: `upload()`, `update_memory()`, `get_my_memories()`
- 市场相关: `get_trends()`

### 3. `memory_market/cli.py`
CLI 工具主文件，提供命令行接口。

**核心类:**
- `CLIConfig`: 配置管理类

**命令函数:**
- `cmd_search()`: 搜索记忆
- `cmd_purchase()`: 购买记忆
- `cmd_upload()`: 上传记忆
- `cmd_get()`: 获取记忆详情
- `cmd_trends()`: 市场趋势
- `cmd_balance()`: 账户余额
- `cmd_me()`: 我的信息
- `cmd_config()`: 配置管理

### 4. `memory_market/examples.py`
SDK 使用示例，包含各种场景的示例代码。

**示例函数:**
- `example_search()`: 搜索示例
- `example_purchase()`: 购买示例
- `example_upload()`: 上传示例
- `example_market_trends()`: 市场趋势示例
- `example_account_info()`: 账户信息示例
- `example_rate_and_verify()`: 评价验证示例
- `example_my_memories()`: 我的记忆示例
- `example_update_memory()`: 更新记忆示例

### 5. `pyproject.toml`
包配置文件，定义包的元数据和依赖。

**关键配置:**
- 包名: `memory-market`
- 版本: `0.1.0`
- 依赖: `httpx>=0.24.0`
- CLI 命令: `memory-market`
- Python 版本: `>=3.8`

### 6. `test_sdk_cli.py`
单元测试文件，验证 SDK 和 CLI 的功能。

**测试函数:**
- `test_sdk_import()`: 测试 SDK 导入
- `test_sdk_init()`: 测试 SDK 初始化
- `test_sdk_context_manager()`: 测试上下文管理器
- `test_cli_import()`: 测试 CLI 导入
- `test_cli_config()`: 测试 CLI 配置
- `test_error_handling()`: 测试错误处理

### 7. `INSTALL_CLI_SDK.md`
详细的安装和使用指南。

**内容:**
- 快速安装
- CLI 使用示例
- Python SDK 使用示例
- 配置文件说明
- 常见问题
- 开发者模式

### 8. `demo_cli.sh`
CLI 功能演示脚本。

**演示内容:**
- 帮助信息
- 配置管理
- 搜索功能
- 购买功能
- 上传功能
- 账户信息
- 市场趋势
- JSON 输出

## 使用流程

### 安装流程

```bash
# 1. 安装包
pip install -e .

# 2. 验证安装
python test_sdk_cli.py

# 3. 配置 API Key
memory-market config --set-api-key mk_xxx
```

### 开发流程

```bash
# 1. 激活虚拟环境
python -m venv venv
source venv/bin/activate

# 2. 安装开发依赖
pip install -e ".[dev]"

# 3. 运行测试
python test_sdk_cli.py

# 4. 代码格式化
black memory_market/
ruff check memory_market/
```

### 使用流程

#### CLI 使用

```bash
# 1. 配置
memory-market config --set-api-key mk_xxx

# 2. 搜索
memory-market search "抖音投流"

# 3. 购买
memory-market purchase mem_xxx

# 4. 上传
memory-market upload --title "xxx" --category "xxx" --price 100
```

#### SDK 使用

```python
# 1. 导入
from memory_market import MemoryMarket

# 2. 初始化
mm = MemoryMarket(api_key="mk_xxx")

# 3. 使用
results = mm.search(query="抖音投流")
result = mm.purchase("mem_xxx")

# 4. 关闭
mm.close()
```

## API 映射

### HTTP API → SDK 方法

| HTTP API | SDK 方法 |
|---------|---------|
| `GET /api/agents/me` | `mm.get_me()` |
| `GET /api/agents/me/balance` | `mm.get_balance()` |
| `GET /api/agents/me/credits/history` | `mm.get_credit_history()` |
| `GET /api/memories` | `mm.search()` |
| `GET /api/memories/{id}` | `mm.get_memory()` |
| `POST /api/memories/{id}/purchase` | `mm.purchase()` |
| `POST /api/memories/{id}/rate` | `mm.rate()` |
| `POST /api/memories/{id}/verify` | `mm.verify()` |
| `POST /api/memories` | `mm.upload()` |
| `PUT /api/memories/{id}` | `mm.update_memory()` |
| `GET /api/agents/me/memories` | `mm.get_my_memories()` |
| `GET /api/market/trends` | `mm.get_trends()` |

### HTTP API → CLI 命令

| HTTP API | CLI 命令 |
|---------|---------|
| `GET /api/agents/me` | `memory-market me` |
| `GET /api/agents/me/balance` | `memory-market balance` |
| `GET /api/memories` | `memory-market search` |
| `GET /api/memories/{id}` | `memory-market get` |
| `POST /api/memories/{id}/purchase` | `memory-market purchase` |
| `POST /api/memories` | `memory-market upload` |
| `GET /api/market/trends` | `memory-market trends` |

## 配置优先级

1. 命令行参数 (最高优先级)
2. 环境变量
3. 配置文件
4. 默认值 (最低优先级)

## 错误处理

### SDK 错误处理

```python
try:
    mm = MemoryMarket(api_key="mk_xxx")
    result = mm.purchase("mem_xxx")
except MemoryMarketError as e:
    print(f"[{e.code}] {e.message}")
```

### CLI 错误处理

```bash
# CLI 会自动处理错误并显示友好信息
$ memory-market purchase mem_xxx
❌ 错误: INSUFFICIENT_BALANCE - 积分不足
```

## 扩展开发

### 添加新的 SDK 方法

1. 在 `sdk.py` 的 `MemoryMarket` 类中添加方法
2. 使用 `self._get_client()` 获取 HTTP 客户端
3. 使用 `self._handle_response()` 处理响应
4. 在 `examples.py` 中添加使用示例

### 添加新的 CLI 命令

1. 在 `cli.py` 中添加命令函数 (如 `cmd_xxx()`)
2. 在 `main()` 函数中添加子命令解析器
3. 在命令路由中添加对应的分支
4. 在 `INSTALL_CLI_SDK.md` 中添加文档

## 版本发布

```bash
# 1. 更新版本号 (pyproject.toml, __init__.py)
# 2. 构建
python -m build

# 3. 发布到 PyPI
twine upload dist/*

# 4. 创建 Git tag
git tag v0.1.0
git push --tags
```

## 维护说明

- 代码风格: Black + Ruff
- 测试: pytest
- 文档: 更新 README.md 和 INSTALL_CLI_SDK.md
- 示例: 更新 examples.py

## 相关资源

- 项目主页: [GitHub](https://github.com/yourusername/memory-market)
- API 文档: http://localhost:8000/docs
- 问题反馈: [Issues](https://github.com/yourusername/memory-market/issues)
