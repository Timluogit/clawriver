# ClawRiver 截图目录

此目录用于存放 ClawRiver 的功能截图和演示视频。

This directory contains screenshots and demo videos for ClawRiver features.

## 目录结构

```
screenshots/
├── web/                    # Web 界面截图
│   ├── home.png           # 首页
│   ├── search.png         # 搜索结果
│   ├── detail.png         # 记忆详情
│   └── dashboard.png      # 用户中心
│
├── cli/                    # CLI 工具截图
│   ├── search.png         # 搜索演示
│   ├── purchase.png       # 购买演示
│   └── upload.png         # 上传演示
│
├── mcp/                    # MCP 集成截图
│   ├── claude-code.png    # Claude Code 集成
│   └── cursor.png         # Cursor 集成
│
├── api/                    # API 文档截图
│   └── swagger.png        # Swagger UI
│
└── videos/                 # 演示视频
    └── demo-video.mp4     # 功能演示视频
```

## 贡献指南

欢迎贡献更好的截图！

### 截图要求

- **分辨率**: 1920x1080 或更高
- **格式**: PNG（截图）或 MP4（视频）
- **语言**: 中文或英文界面
- **隐私**: 隐藏敏感信息（API Key、个人数据等）

### 快速截图工具

**macOS:**
```bash
# 全屏截图
Cmd + Shift + 3

# 选择区域截图
Cmd + Shift + 4

# 录屏（带声音）
Cmd + Shift + 5
```

**Linux (gnome-screenshot):**
```bash
# 安装
sudo apt install gnome-screenshot

# 截图
gnome-screenshot -a -f screenshot.png
```

**Windows:**
```
# 截图工具
Win + Shift + S

# 录屏
Win + G
```

### 提交截图

1. 将截图放入对应的子目录
2. 更新 `../SCREENSHOTS.md` 中的占位说明
3. 提交 Pull Request

## 相关文档

- [截图说明文档](../SCREENSHOTS.md)
- [README.md](../../README.md)
- [贡献指南](../../CONTRIBUTING.md)
