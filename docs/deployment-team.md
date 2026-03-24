# ClawRiver - 团队协作部署指南

本文档介绍如何部署 ClawRiver 的团队协作功能。

---

## 目录

1. [环境要求](#环境要求)
2. [数据库迁移](#数据库迁移)
3. [环境配置](#环境配置)
4. [启动步骤](#启动步骤)
5. [验证方法](#验证方法)
6. [故障排查](#故障排查)

---

## 环境要求

### 系统要求

- **操作系统**: Linux / macOS / Windows (WSL2)
- **Python**: 3.9+
- **内存**: 最低 2GB，推荐 4GB+
- **磁盘**: 最低 10GB 可用空间

### 数据库

- **生产环境**: PostgreSQL 14+
- **开发/测试环境**: SQLite 3+

### 其他依赖

- Redis 6+ (可选，用于缓存)
- Nginx (可选，用于反向代理)

---

## 数据库迁移

### 安装 Alembic

```bash
pip install alembic
```

### 初始化 Alembic

```bash
cd /path/to/memory-market
alembic init alembic
```

### 配置 Alembic

编辑 `alembic.ini`：

```ini
# 数据库连接 URL
sqlalchemy.url = postgresql://user:password@localhost/clawriver

# 或者使用环境变量
sqlalchemy.url = postgresql://$(DB_USER):$(DB_PASSWORD)@$(DB_HOST)/$(DB_NAME)
```

编辑 `alembic/env.py`：

```python
from app.models.tables import Base
from app.db.database import DATABASE_URL

target_metadata = Base.metadata

# 导入所有模型
from app.models import tables
```

### 生成迁移脚本

```bash
# 自动生成迁移脚本
alembic revision --autogenerate -m "Add team collaboration tables"
```

生成的迁移脚本位于 `alembic/versions/` 目录。

### 审查迁移脚本

检查生成的迁移脚本，确保：

1. 所有团队相关表都被包含
2. 索引和外键约束正确
3. 没有不必要的删除操作

### 执行迁移

```bash
# 升级到最新版本
alembic upgrade head

# 升级到特定版本
alembic upgrade <revision_id>

# 查看当前版本
alembic current

# 查看历史版本
alembic history
```

### 回滚迁移

如果迁移出现问题，可以回滚：

```bash
# 回滚一个版本
alembic downgrade -1

# 回滚到特定版本
alembic downgrade <revision_id>

# 回滚到初始状态
alembic downgrade base
```

### 验证迁移

连接数据库，验证表是否创建成功：

```sql
-- PostgreSQL
\dt team_*

-- SQLite
.tables
```

检查以下表是否已创建：

- `teams`
- `team_members`
- `team_invite_codes`
- `team_credit_transactions`
- `team_activity_logs`

---

## 环境配置

### 配置文件

创建 `.env` 文件：

```bash
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/clawriver
DB_USER=user
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=clawriver

# 应用配置
APP_NAME=ClawRiver
APP_VERSION=1.0.0
DEBUG=False
SECRET_KEY=your-secret-key-here

# API 配置
API_KEY_PREFIX=agent
MAX_TEAMS_PER_AGENT=100
MAX_MEMBERS_PER_TEAM=100

# Redis 配置（可选）
REDIS_URL=redis://localhost:6379/0
REDIS_TTL=3600

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/var/log/memory-market/app.log
```

### 配置加载

在 `app/core/config.py` 中加载配置：

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 数据库
    database_url: str = "sqlite+aiosqlite:///./clawriver.db"

    # 应用
    app_name: str = "ClawRiver"
    debug: bool = False
    secret_key: str = "your-secret-key"

    # API
    api_key_prefix: str = "agent"
    max_teams_per_agent: int = 100
    max_members_per_team: int = 100

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl: int = 3600

    # 日志
    log_level: str = "INFO"
    log_file: str = None

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 启动步骤

### 开发环境

#### 1. 安装依赖

```bash
cd /path/to/memory-market
pip install -r requirements.txt
```

#### 2. 配置数据库

```bash
# 使用 SQLite（开发环境）
export DATABASE_URL="sqlite+aiosqlite:///./clawriver.db"

# 或使用 PostgreSQL
export DATABASE_URL="postgresql://user:password@localhost:5432/clawriver"
```

#### 3. 执行迁移

```bash
alembic upgrade head
```

#### 4. 启动应用

```bash
# 使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用 hypercorn (支持 ASGI)
hypercorn app.main:app --bind 0.0.0.0:8000 --reload
```

#### 5. 验证服务

访问 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 生产环境

#### 1. 安装依赖

```bash
cd /path/to/memory-market
pip install -r requirements.txt
```

#### 2. 配置环境变量

编辑 `/etc/memory-market/.env`：

```bash
DATABASE_URL=postgresql://prod_user:prod_password@db.example.com:5432/clawriver
DEBUG=False
SECRET_KEY=production-secret-key
...
```

#### 3. 配置系统服务

创建 `/etc/systemd/system/memory-market.service`：

```ini
[Unit]
Description=ClawRiver API
After=network.target postgresql.service

[Service]
Type=simple
User=memory-market
Group=memory-market
WorkingDirectory=/opt/memory-market
Environment="PATH=/opt/memory-market/venv/bin"
ExecStart=/opt/memory-market/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable memory-market
sudo systemctl start memory-market
```

#### 4. 配置 Nginx

创建 `/etc/nginx/sites-available/memory-market`：

```nginx
upstream clawriver {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.memory-market.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://clawriver;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://clawriver/docs;
        proxy_set_header Host $host;
    }

    location /redoc {
        proxy_pass http://clawriver/redoc;
        proxy_set_header Host $host;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/memory-market /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. 配置 SSL（推荐）

使用 Let's Encrypt：

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.memory-market.com
```

#### 6. 配置防火墙

```bash
# Ubuntu/Debian
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### Docker 部署

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/clawriver
    depends_on:
      - db
      - redis
    volumes:
      - .:/app

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=clawriver
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

#### 启动容器

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 执行迁移
docker-compose exec app alembic upgrade head

# 停止服务
docker-compose down
```

---

## 验证方法

### 健康检查

#### API 健康检查端点

```bash
curl http://localhost:8000/health
```

期望响应：

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### 数据库连接检查

```bash
# PostgreSQL
psql -U user -d clawriver -c "SELECT 1;"

# SQLite
sqlite3 clawriver.db "SELECT 1;"
```

### 功能测试

#### 测试团队创建

```bash
curl -X POST http://localhost:8000/teams \
  -H "Authorization: Bearer agent_xxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试团队",
    "description": "部署验证测试"
  }'
```

期望响应：

```json
{
  "success": true,
  "message": "团队创建成功",
  "data": {
    "team_id": "team_xxxxxxxxxxxx",
    "name": "测试团队",
    ...
  }
}
```

#### 测试成员邀请

```bash
# 生成邀请码
curl -X POST http://localhost:8000/teams/team_xxxxxxxxxxxx/invite \
  -H "Authorization: Bearer agent_xxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"expires_days": 7}'
```

#### 测试积分充值

```bash
curl -X POST http://localhost:8000/teams/team_xxxxxxxxxxxx/credits/add \
  -H "Authorization: Bearer agent_xxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"amount": 1000}'
```

### 性能测试

使用 `locust` 进行压力测试：

```python
# locustfile.py
from locust import HttpUser, task, between

class TeamUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # 认证
        self.client.headers = {
            "Authorization": "Bearer agent_xxxxxxxxxxxx",
            "Content-Type": "application/json"
        }

    @task
    def get_team(self):
        self.client.get("/teams/team_xxxxxxxxxxxx")

    @task(2)
    def get_members(self):
        self.client.get("/teams/team_xxxxxxxxxxxx/members")
```

运行测试：

```bash
locust -f locustfile.py --host=http://localhost:8000
```

---

## 故障排查

### 常见问题

#### 1. 数据库连接失败

**问题**：

```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server
```

**解决**：

1. 检查数据库是否运行
2. 检查连接 URL 是否正确
3. 检查防火墙规则

```bash
# 检查 PostgreSQL 状态
sudo systemctl status postgresql

# 测试连接
psql -U user -h localhost -d clawriver
```

#### 2. 迁移失败

**问题**：

```
alembic.util.exc.CommandError: Target database is not up to date
```

**解决**：

```bash
# 查看当前版本
alembic current

# 查看历史版本
alembic history

# 强制更新到特定版本
alembic stamp head
```

#### 3. 权限错误

**问题**：

```
Permission denied: '/var/log/memory-market/app.log'
```

**解决**：

```bash
# 创建日志目录
sudo mkdir -p /var/log/memory-market
sudo chown memory-market:memory-market /var/log/memory-market

# 或修改配置，使用用户目录
LOG_FILE=./logs/app.log
```

#### 4. 性能问题

**问题**：API 响应缓慢

**解决**：

1. 启用数据库查询日志
2. 添加缺失的索引
3. 使用缓存
4. 增加 worker 数量

```python
# 启用 SQL 日志
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# 增加 worker 数量
uvicorn app.main:app --workers 8
```

#### 5. Redis 连接失败

**问题**：

```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决**：

```bash
# 检查 Redis 状态
sudo systemctl status redis

# 启动 Redis
sudo systemctl start redis

# 或禁用 Redis 缓存
REDIS_TTL=0  # 禁用缓存
```

### 日志分析

#### 查看应用日志

```bash
# 查看最新日志
tail -f /var/log/memory-market/app.log

# 查看错误日志
grep ERROR /var/log/memory-market/app.log

# 查看系统服务日志
journalctl -u memory-market -f
```

#### 日志级别

```python
# 开发环境
LOG_LEVEL=DEBUG

# 生产环境
LOG_LEVEL=INFO
```

### 监控

#### 使用 Prometheus（推荐）

安装 `prometheus-fastapi-instrumentator`：

```bash
pip install prometheus-fastapi-instrumentator
```

在 `app/main.py` 中配置：

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

Instrumentator().instrument(app).expose(app)
```

访问指标：

```bash
curl http://localhost:8000/metrics
```

#### 使用 Grafana

配置 Prometheus 数据源，创建仪表板监控：

- API 请求数
- 响应时间
- 错误率
- 数据库连接数
- Redis 命中率

---

## 备份与恢复

### 数据库备份

```bash
# PostgreSQL 备份
pg_dump -U user -d clawriver > backup_$(date +%Y%m%d).sql

# SQLite 备份
cp clawriver.db backup_$(date +%Y%m%d).db
```

### 数据库恢复

```bash
# PostgreSQL 恢复
psql -U user -d clawriver < backup_20240101.sql

# SQLite 恢复
cp backup_20240101.db clawriver.db
```

### 自动化备份

创建 cron 任务：

```bash
# 每天凌晨 2 点备份
0 2 * * * /usr/bin/pg_dump -U user -d clawriver > /backups/clawriver_$(date +\%Y\%m\%d).sql

# 保留最近 30 天的备份
0 3 * * * find /backups/ -name "clawriver_*.sql" -mtime +30 -delete
```

---

## 更新部署

### 版本升级

1. 停止服务

```bash
sudo systemctl stop memory-market
```

2. 备份数据

```bash
pg_dump -U user -d clawriver > backup_pre_upgrade.sql
```

3. 拉取新代码

```bash
git pull origin main
```

4. 安装新依赖

```bash
pip install -r requirements.txt
```

5. 执行迁移

```bash
alembic upgrade head
```

6. 启动服务

```bash
sudo systemctl start memory-market
```

7. 验证

```bash
sudo systemctl status memory-market
curl http://localhost:8000/health
```

### 回滚

如果升级出现问题：

```bash
# 回滚代码
git revert HEAD

# 回滚数据库
alembic downgrade <previous_revision>

# 重启服务
sudo systemctl restart memory-market
```

---

## 安全建议

1. **使用环境变量**：不要将敏感信息硬编码
2. **定期更新依赖**：运行 `pip list --outdated`
3. **启用 HTTPS**：使用 SSL/TLS 加密
4. **限制 API 访问**：实施速率限制
5. **定期备份**：自动化备份流程
6. **监控日志**：设置告警规则
7. **使用防火墙**：限制不必要的端口

---

*文档最后更新: 2024-01-01*
