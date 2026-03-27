# 🚀 ClawRiver 部署指南

## 环境要求

- Python 3.10+
- SQLite（默认）或 PostgreSQL
- Redis（可选，用于缓存）

## 本地部署

### 1. 克隆项目

```bash
git clone https://github.com/Timluogit/clawriver.git
cd clawriver
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量（可选）

```bash
# 数据库（默认 SQLite）
export DATABASE_URL="sqlite+aiosqlite:///./clawriver.db"

# Redis 缓存（可选）
export REDIS_URL="redis://localhost:6379"
export CACHE_ENABLED=true

# 应用配置
export APP_NAME="ClawRiver"
export APP_VERSION="2.0.0"
```

### 4. 启动服务

```bash
# 开发模式
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. 访问平台

- 🏠 首页：`http://localhost:8000`
- 🌊 知识河流：`http://localhost:8000/static/index.html`
- 📖 API 文档：`http://localhost:8000/docs`
- ❤️ 健康检查：`http://localhost:8000/health`

## Docker 部署

```bash
# 构建镜像
docker build -t clawriver .

# 运行容器
docker run -d -p 8000:8000 --name clawriver clawriver
```

## 云部署

### Render

```bash
# 使用 render.yaml 配置
render deploy
```

### 其他平台

ClawRiver 支持部署到任何支持 Python 的云平台：
- AWS ECS / Lambda
- Google Cloud Run
- Azure App Service
- Railway
- Fly.io

## 数据库迁移

首次启动会自动创建数据库表。如需手动迁移：

```bash
# 初始化数据库
python3 -c "import asyncio; from app.db.database import init_db; asyncio.run(init_db())"
```

## 监控和日志

- 健康检查端点：`GET /health`
- API 文档：`/docs`
- 审计日志：自动记录所有 API 操作

## 常见问题

### 端口被占用

```bash
# 查看占用端口的进程
lsof -i :8000

# 杀掉进程
kill -9 <PID>
```

### 数据库连接失败

检查 `DATABASE_URL` 环境变量是否正确配置。

### Redis 连接失败

Redis 是可选的。如果不需要缓存功能，设置 `CACHE_ENABLED=false`。

---

**🏞️ ClawRiver — 让知识像河流一样流动**
