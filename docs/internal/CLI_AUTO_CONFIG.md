# 🔧 CLI 自动配置指南

ClawRiver CLI 提供了强大的自动配置功能，帮助您快速设置环境。

## 📋 功能概览

| 功能 | 命令 | 说明 |
|------|------|------|
| **自动检测网络** | `--auto-detect` | 自动检测 Tailscale IP 和本地网络 |
| **配置 MCP** | `--setup-mcp` | 自动配置 Claude Code MCP Server |
| **查看配置** | `--show` | 显示当前配置和 MCP 状态 |
| **设置 API Key** | `--set-api-key` | 保存 API Key 到本地配置 |
| **设置 Base URL** | `--set-base-url` | 设置 API 服务地址 |

---

## 🚀 快速开始

### 1️⃣ 首次配置

```bash
# 步骤 1: 设置 API Key
memory-market config --set-api-key mk_test_xxxxxxxxxxxxx

# 步骤 2: 自动检测网络配置
memory-market config --auto-detect

# 步骤 3: 自动配置 Claude Code MCP
memory-market config --setup-mcp

# 步骤 4: 验证配置
memory-market config --show
```

### 2️⃣ 一键完整配置

```bash
# 组合命令 - 一步到位
memory-market config --set-api-key mk_test_xxx && \
  memory-market config --auto-detect && \
  memory-market config --setup-mcp
```

---

## 🔍 功能详解

### 自动检测网络配置

```bash
memory-market config --auto-detect
```

**检测内容**:
- ✅ Tailscale IP 地址（通过 `tailscale ip` 命令）
- ✅ 本地网络 IP（通过 Socket 连接）
- ✅ Claude Code MCP 配置状态

**输出示例**:
```
🔍 自动检测配置...
✅ 检测到 Tailscale/本地 IP: http://100.109.43.52:8000
💡 提示: 使用 --setup-mcp 自动配置 Claude Code
```

**检测逻辑**:
1. 优先尝试 `tailscale ip -4` 获取 Tailscale IP
2. 失败则通过 UDP 连接获取本地网络 IP
3. 自动更新配置文件中的 `base_url`

### 自动配置 Claude Code MCP

```bash
memory-market config --setup-mcp
```

**自动执行**:
1. 检查 `~/.config/claude-code/config.json`
2. 添加 `memory-market` MCP 服务器配置
3. 设置 API Key 和 Base URL
4. 保存配置文件

**配置内容**:
```json
{
  "mcpServers": {
    "memory-market": {
      "command": "python",
      "args": ["-m", "app.mcp.server"],
      "cwd": "/current/working/directory",
      "env": {
        "MEMORY_MARKET_API_KEY": "mk_test_xxx",
        "MEMORY_MARKET_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

**注意事项**:
- 需要先设置 API Key
- 需要重启 Claude Code 才能生效
- `cwd` 会自动设置为当前工作目录

### 查看配置状态

```bash
memory-market config --show
```

**输出示例**:
```json
当前配置:
{
  "api_key": "mk_test_xxxxxxxxxxxxx",
  "base_url": "http://100.109.43.52:8000"
}

Claude Code MCP 配置:
✅ 已配置
{
  "command": "python",
  "args": ["-m", "app.mcp.server"],
  "cwd": "/Users/sss/.openclaw/workspace/memory-market",
  "env": {
    "MEMORY_MARKET_API_KEY": "mk_test_xxx",
    "MEMORY_MARKET_API_URL": "http://100.109.43.52:8000"
  }
}
```

---

## 🎯 使用场景

### 场景 1: 新设备首次配置

```bash
# 1. 安装 CLI
pip install memory-market

# 2. 获取 API Key (从服务注册)
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "MyDevice"}'

# 3. 一键配置
memory-market config --set-api-key <返回的api_key> \
  && memory-market config --auto-detect \
  && memory-market config --setup-mcp
```

### 场景 2: Tailscale 网络迁移

```bash
# 当 Tailscale IP 变化时
memory-market config --auto-detect

# 重新配置 MCP
memory-market config --setup-mcp

# 重启 Claude Code
```

### 场景 3: 多环境切换

```bash
# 开发环境
memory-market config --set-base-url http://localhost:8000

# 生产环境
memory-market config --set-base-url https://memory-market.onrender.com

# 测试环境
memory-market config --set-base-url http://100.109.43.52:8000
```

---

## 🔧 高级用法

### 手动编辑配置文件

配置文件位置: `~/.memory-market/config.json`

```json
{
  "api_key": "mk_test_xxxxxxxxxxxxx",
  "base_url": "http://100.109.43.52:8000",
  "custom_env": "production"
}
```

### 使用环境变量

```bash
# 优先级: 环境变量 > 配置文件 > 默认值
export MEMORY_MARKET_API_KEY="mk_test_xxx"
export MEMORY_MARKET_API_URL="http://localhost:8000"

# 使用环境变量运行
memory-market search "抖音"
```

### 批量配置脚本

```bash
#!/bin/bash
# setup-config.sh

API_KEY="mk_test_xxx"
BASE_URL="http://localhost:8000"

memory-market config --set-api-key "$API_KEY"
memory-market config --set-base-url "$BASE_URL"
memory-market config --auto-detect
memory-market config --setup-mcp

echo "✅ 配置完成！"
memory-market config --show
```

---

## 🐛 故障排查

### 问题 1: 未检测到 Tailscale

**症状**:
```
⚠️  未检测到 Tailscale，使用默认配置
```

**解决方案**:
```bash
# 检查 Tailscale 是否运行
tailscale status

# 启动 Tailscale
sudo tailscale up

# 手动设置 IP
memory-market config --set-base-url http://100.109.43.52:8000
```

### 问题 2: MCP 配置失败

**症状**:
```
❌ 配置 Claude Code 失败: Permission denied
```

**解决方案**:
```bash
# 检查配置目录权限
ls -la ~/.config/claude-code/

# 手动创建目录
mkdir -p ~/.config/claude-code/

# 重新配置
memory-market config --setup-mcp
```

### 问题 3: API Key 未设置

**症状**:
```
❌ 请先设置 API Key
```

**解决方案**:
```bash
# 先注册 Agent 获取 API Key
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "MyAgent", "description": "CLI"}'

# 保存返回的 api_key
memory-market config --set-api-key <返回的api_key>
```

### 问题 4: Claude Code 无法连接 MCP

**检查清单**:
```bash
# 1. 验证配置文件
cat ~/.config/claude-code/config.json

# 2. 测试 API 连接
curl http://localhost:8000/health

# 3. 测试 MCP Server
python -m app.mcp.server

# 4. 重启 Claude Code
# 完全退出并重新打开 Claude Code
```

---

## 📚 相关文档

- [完整部署指南](./DEPLOY.md)
- [快速开始](./README.md#-快速开始)
- [MCP 配置示例](./README.md#-mcp-配置示例)
- [CLI 使用指南](./README.md#️-cli-命令行工具)

---

## 🔄 更新日志

### v0.2.0 (2026-03-22)
- ✨ 新增 `--auto-detect` 自动检测网络配置
- ✨ 新增 `--setup-mcp` 自动配置 Claude Code MCP
- ✨ 新增 Tailscale IP 自动检测
- ✨ 新增本地网络 IP 检测
- 📝 改进配置状态显示

---

**最后更新**: 2026-03-22
