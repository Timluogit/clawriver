# Qdrant 安装和配置指南

本文档介绍如何在 ClawRiver 项目中安装和配置 Qdrant 向量数据库。

---

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [Docker 安装](#docker-安装)
- [手动安装](#手动安装)
- [配置说明](#配置说明)
- [健康检查](#健康检查)
- [常见问题](#常见问题)

---

## 系统要求

### 最低要求

- **CPU:** 2 核
- **内存:** 2 GB
- **磁盘:** 10 GB 可用空间
- **操作系统:** Linux, macOS, Windows (with WSL2)

### 推荐配置

- **CPU:** 4 核+
- **内存:** 8 GB+
- **磁盘:** 50 GB+ SSD
- **操作系统:** Linux (Ubuntu 20.04+)

---

## 快速开始

### 使用 Docker Compose（推荐）

```bash
# 1. 启动所有服务
docker-compose up -d

# 2. 查看服务状态
docker-compose ps

# 3. 查看 Qdrant 日志
docker-compose logs -f qdrant

# 4. 验证服务
curl http://localhost:6333/health
```

### 仅启动 Qdrant

```bash
# 使用 Docker 直接启动
docker run -d \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/data/qdrant:/qdrant/storage \
  qdrant/qdrant:latest

# 验证服务
curl http://localhost:6333/health
```

---

## Docker 安装

### 完整配置（docker-compose.yml）

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: memory-market-qdrant
    ports:
      - "6333:6333"  # HTTP API
      - "6334:6334"  # gRPC API（可选）
    volumes:
      - ./data/qdrant:/qdrant/storage  # 数据持久化
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
    networks:
      - memory-market-net

  # 其他服务...
  api:
    # ...
    depends_on:
      qdrant:
        condition: service_healthy

networks:
  memory-market-net:
    driver: bridge
```

### 环境变量说明

| 变量 | 默认值 | 说明 |
|-----|-------|------|
| `QDRANT__SERVICE__HTTP_PORT` | 6333 | HTTP API 端口 |
| `QDRANT__SERVICE__GRPC_PORT` | 6334 | gRPC API 端口 |
| `QDRANT__LOG_LEVEL` | INFO | 日志级别（DEBUG/INFO/WARN/ERROR） |
| `QDRANT__SERVICE__MAX_REQUEST_SIZE_MB` | 32 | 最大请求大小（MB） |

---

## 手动安装

### 使用 Docker（非 Compose）

```bash
# 拉取镜像
docker pull qdrant/qdrant:latest

# 运行容器
docker run -d \
  --name memory-market-qdrant \
  -p 6333:6333 \
  -v $(pwd)/data/qdrant:/qdrant/storage \
  --restart unless-stopped \
  qdrant/qdrant:latest
```

### 使用二进制文件

#### Linux

```bash
# 下载最新版本
wget https://github.com/qdrant/qdrant/releases/latest/download/qdrant-aarch64-apple-darwin.tar.gz

# 解压
tar -xzf qdrant-aarch64-apple-darwin.tar.gz

# 运行
./qdrant
```

#### macOS

```bash
# 使用 Homebrew
brew install qdrant

# 运行
qdrant

# 或使用后台运行
qdrant --service-mode &
```

---

## 配置说明

### Application 配置（app/core/config.py）

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Qdrant 配置
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""  # 生产环境建议设置
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_DEVICE: str = "cpu"  # cpu/cuda/mps

    # 向量配置
    VECTOR_DIM: int = 512  # bge-small-zh-v1.5 为 512 维
    VECTOR_DISTANCE: str = "cosine"  # cosine/euclid/dot

    # Collection 配置
    QDRANT_COLLECTION_NAME: str = "memories"

    # 性能配置
    QDRANT_BATCH_SIZE: int = 100  # 批量索引大小
    QDRANT_INDEXING_THRESHOLD: int = 20000  # 索引阈值

    class Config:
        env_file = ".env"
        case_sensitive = True
```

### 环境变量文件（.env）

```bash
# Qdrant 配置
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
EMBEDDING_DEVICE=cpu

# 向量配置
VECTOR_DIM=512
VECTOR_DISTANCE=cosine

# Collection 配置
QDRANT_COLLECTION_NAME=memories

# 性能配置
QDRANT_BATCH_SIZE=100
QDRANT_INDEXING_THRESHOLD=20000
```

---

## 健康检查

### 检查 Qdrant 服务状态

```bash
# 使用 curl
curl http://localhost:6333/health

# 响应示例
# {"status":"ok","version":"1.7.0"}

# 检查 Docker 容器
docker ps | grep qdrant

# 查看 Qdrant 日志
docker logs memory-market-qdrant
```

### 检查 Collection 状态

```bash
# 获取所有 Collections
curl http://localhost:6333/collections

# 响应示例
# {
#   "result": {
#     "collections": [
#       {
#         "name": "memories",
#         "status": "green",
#         "vectors_count": 1000
#       }
#     ]
#   }
# }

# 获取特定 Collection 信息
curl http://localhost:6333/collections/memories
```

### 检查 Application 集成

```python
from app.search.qdrant_engine import get_qdrant_engine

# 创建引擎实例
engine = get_qdrant_engine()

# 健康检查
is_healthy = engine.health_check()
print(f"Qdrant 健康状态: {is_healthy}")

# 获取 Collection 信息
info = engine.get_collection_info()
print(f"Collection 信息: {info}")
```

---

## 性能优化

### HNSW 索引配置

```python
# 在 app/search/qdrant_engine.py 中配置
index_config = {
    "hnsw_config": {
        "m": 16,  # 连接数（影响召回率和内存）
        "ef_construct": 100,  # 构建时的搜索范围（影响构建速度和质量）
    }
}
```

| 参数 | 推荐值 | 说明 |
|-----|-------|------|
| `m` | 16-32 | 连接数，越大召回率越高但内存占用越大 |
| `ef_construct` | 100-200 | 构建时的搜索范围，越大质量越高但构建越慢 |

### 量化配置

```python
# 使用量化减少内存占用
quantization_config = models.ScalarQuantization(
    scalar=models.ScalarQuantizationConfig(
        type=models.ScalarType.INT8,
        quantile=0.99,
        always_ram=False
    )
)
```

### 优化建议

1. **内存优化：** 使用量化（INT8）可减少 75% 内存占用
2. **速度优化：** 增加 `m` 和 `ef_construct` 可提升查询速度
3. **磁盘优化：** 使用 SSD 存储向量数据

---

## 数据持久化

### Docker Volume 配置

```yaml
volumes:
  - ./data/qdrant:/qdrant/storage  # 绑定挂载
```

### Docker Named Volume（推荐用于生产）

```yaml
volumes:
  qdrant-data:
    driver: local

services:
  qdrant:
    # ...
    volumes:
      - qdrant-data:/qdrant/storage

volumes:
  qdrant-data:
```

### 备份和恢复

```bash
# 备份 Qdrant 数据
docker cp memory-market-qdrant:/qdrant/storage ./backup/qdrant-$(date +%Y%m%d)

# 恢复 Qdrant 数据
docker cp ./backup/qdrant-20240101 memory-market-qdrant:/qdrant/storage
docker restart memory-market-qdrant
```

---

## 常见问题

### 问题 1：Qdrant 无法启动

**症状：**
```
Error: Cannot connect to the Docker daemon
```

**解决方案：**

```bash
# 1. 检查 Docker 服务
docker ps

# 2. 启动 Docker
sudo systemctl start docker  # Linux
open -a Docker  # macOS

# 3. 检查端口占用
lsof -i :6333

# 4. 如果端口被占用，修改端口映射
ports:
  - "6334:6333"  # 映射到 6334
```

### 问题 2：连接超时

**症状：**
```
TimeoutError: [Errno 110] Connection timed out
```

**解决方案：**

```bash
# 1. 检查 Qdrant 服务状态
curl http://localhost:6333/health

# 2. 检查防火墙
sudo ufw allow 6333/tcp

# 3. 检查 Docker 网络配置
docker network inspect memory-market-net
```

### 问题 3：内存不足

**症状：**
```
MemoryError: Unable to allocate memory
```

**解决方案：**

1. **启用量化：**
   ```python
   quantization_config = models.ScalarQuantization(
       scalar=models.ScalarQuantizationConfig(
           type=models.ScalarType.INT8
       )
   )
   ```

2. **减少批量大小：**
   ```python
   engine.index_memories(memories, batch_size=50)  # 减少到 50
   ```

3. **增加系统内存：**
   ```bash
   # Docker Desktop 配置更多内存
   # Settings > Resources > Memory > 8GB+
   ```

### 问题 4：向量维度不匹配

**症状：**
```
ValueError: Vector dimension mismatch
```

**解决方案：**

```bash
# 1. 检查模型向量维度
python -c "from sentence_transformers import SentenceTransformer; print(SentenceTransformer('BAAI/bge-small-zh-v1.5').get_sentence_embedding_dimension())"
# 输出：512

# 2. 重新创建 Collection
from app.search.qdrant_engine import get_qdrant_engine
engine = get_qdrant_engine()
engine.create_collection(recreate=True)
```

### 问题 5：搜索结果不准确

**症状：** 搜索结果与查询不相关

**解决方案：**

1. **检查向量化是否完成：**
   ```python
   info = engine.get_collection_info()
   print(f"向量数量: {info['points_count']}")
   ```

2. **重新向量化数据：**
   ```bash
   python vectorize_memories.py --batch-size 100
   ```

3. **调整相似度阈值：**
   ```python
   engine.search(query, min_score=0.3)  # 降低阈值
   ```

---

## 监控和日志

### 查看实时日志

```bash
# Qdrant 日志
docker-compose logs -f qdrant

# API 日志
docker-compose logs -f api
```

### Prometheus 监控（可选）

Qdrant 提供 Prometheus 指标端点：

```bash
# 访问指标端点
curl http://localhost:6333/metrics

# 配置 Prometheus
scrape_configs:
  - job_name: 'qdrant'
    static_configs:
      - targets: ['localhost:6333']
```

---

## 下一步

- [阅读 API 使用文档](./qdrant-api.md)
- [查看向量搜索技术文档](./vector-search.md)
- [运行测试](../test_qdrant.py)

---

**文档版本：** 1.0
**最后更新：** 2024-03-23
**维护者：** OpenClaw AI
