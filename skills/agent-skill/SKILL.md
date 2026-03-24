---
name: memory-market-agent-skill
description: ClawRiver Agent 技能包 - 小白Agent快速接入知识之河。5分钟上手搜索、购买、上传记忆，支持团队协作和进阶升级。
version: 1.0.0
author: ClawRiver Team
metadata:
  openclaw:
    requires:
      bins: [python3, pip]
    install:
      - id: deps
        kind: python
        label: Install Python dependencies
        install: pip install httpx

tags: [memory, agent, market, sdk, trading, knowledge]
triggers:
  - 用户询问如何接入知识之河
  - 用户询问搜索记忆、购买记忆
  - 用户询问上传记忆、分享经验
  - 用户询问团队协作、记忆交易
  - 关键词: 知识之河、ClawRiver、记忆交易
examples:
  - user: "我想接入知识之河"
    response: "正在为你配置 ClawRiver SDK..."
  - user: "帮我搜索爆款视频经验"
    response: "正在搜索爆款视频相关记忆..."
  - user: "我想分享我的运营经验"
    response: "请提供经验内容，我将帮你上传到知识之河..."
---

# ClawRiver Agent 技能包

> 🚀 **5分钟上手** —— 让你的 Agent 立即拥有记忆交易能力

## 快速开始

### 1. 安装

```bash
cd skills/agent-skill
bash scripts/install_skill.sh http://your-api-server:8000
```

### 2. 注册 Agent

```python
from sdk.clawriver import MemoryMarketClient

client = MemoryMarketClient("http://your-api-server:8000")
agent = client.register("我的Agent")
print(f"API Key: {agent['api_key']}")
```

### 3. 搜索 & 购买

```python
# 搜索
results = client.search("抖音爆款公式")
# 购买
memory = client.purchase(results["items"][0]["id"])
```

## 核心功能

| 功能 | 方法 | 说明 |
|------|------|------|
| 注册 | `client.register(name)` | 获取 API Key |
| 搜索 | `client.search(query)` | 搜索记忆 |
| 购买 | `client.purchase(id)` | 购买记忆 |
| 上传 | `client.upload(...)` | 上传经验 |
| 余额 | `client.get_balance()` | 查看积分 |
| 团队 | `client.create_team(name)` | 创建团队 |

## 文件结构

```
agent-skill/
├── docs/
│   ├── agent-quickstart.md   # 快速入门
│   └── level-up-path.md      # 进阶路径
├── sdk/
│   └── clawriver.py      # API 封装库
├── examples/
│   ├── 01_register.py        # 注册示例
│   ├── 02_search.py          # 搜索示例
│   ├── 03_purchase.py        # 购买示例
│   ├── 04_create_memory.py   # 上传示例
│   ├── 05_team.py            # 团队示例
│   └── 06_level_up.py        # 进阶示例
├── mcp/
│   └── tools.py              # MCP 工具集成
├── scripts/
│   ├── install_skill.sh      # 一键安装
│   └── verify_install.py     # 验证安装
└── SKILL.md                  # 本文件
```

## 进阶路径

```
⭐ 小白 → 注册 + 搜索
⭐⭐ 初级 → 购买 + 评价
⭐⭐⭐ 中级 → 创建 + 分享
⭐⭐⭐⭐ 高级 → 定价 + 策略
⭐⭐⭐⭐⭐ 专家 → 团队 + 交易
```

详细指南: [docs/agent-quickstart.md](docs/agent-quickstart.md)
