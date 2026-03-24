# 外部数据源集成指南

## 概述

Agent知识之河支持集成多种外部数据源，实现跨平台数据同步和统一搜索。目前已支持 **6种数据源**，覆盖主流云存储、邮件、笔记和代码托管平台。

## 支持的数据源

| 数据源 | 类型标识 | 主要功能 | Webhook |
|--------|----------|----------|---------|
| Google Drive | `google_drive` | 文件列表/下载/搜索 | Google Workspace Events |
| Gmail | `gmail` | 邮件列表/搜索/附件 | Google Cloud Pub/Sub |
| Notion | `notion` | 页面/数据库查询 | Web Endpoint |
| OneDrive | `onedrive` | 文件列表/下载/搜索 | Microsoft Graph 订阅 |
| GitHub | `github` | 代码列表/搜索/仓库 | GitHub Webhooks |
| 本地文件夹 | `local_folder` | 文件遍历/变更检测 | N/A (轮询) |

---

## 快速开始

### 1. 连接数据源

```bash
# 连接本地文件夹
curl -X POST http://localhost:8000/api/external-sources/connect \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "local_folder",
    "config": {
      "path": "/path/to/folder",
      "max_file_size": 52428800
    }
  }'

# 连接 Google Drive
curl -X POST http://localhost:8000/api/external-sources/connect \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "google_drive",
    "config": {
      "access_token": "ya29.xxx",
      "refresh_token": "1//xxx",
      "client_id": "xxx.apps.googleusercontent.com",
      "client_secret": "xxx"
    }
  }'

# 连接 GitHub
curl -X POST http://localhost:8000/api/external-sources/connect \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "github",
    "config": {
      "access_token": "ghp_xxx",
      "repositories": ["owner/repo1", "owner/repo2"]
    }
  }'
```

### 2. 同步数据

```bash
# 同步指定数据源
curl -X POST http://localhost:8000/api/external-sources/{source_id}/sync

# 强制同步
curl -X POST "http://localhost:8000/api/external-sources/{source_id}/sync?force=true"
```

### 3. 浏览文件

```bash
# 列出文件
curl http://localhost:8000/api/external-sources/{source_id}/files

# 带参数
curl "http://localhost:8000/api/external-sources/{source_id}/files?folder_id=xxx&limit=50"
```

### 4. 断开连接

```bash
curl -X DELETE http://localhost:8000/api/external-sources/{source_id}/disconnect
```

---

## API 端点

### `POST /api/external-sources/connect`
连接新的外部数据源。

**请求体：**
```json
{
  "source_type": "google_drive | gmail | notion | onedrive | github | local_folder",
  "config": { ... },
  "source_id": "optional-custom-id"
}
```

**响应：**
```json
{
  "success": true,
  "message": "Successfully connected to google_drive",
  "source_id": "google_drive_1711180800",
  "source_type": "google_drive",
  "status": "connected"
}
```

### `POST /api/external-sources/{source_id}/sync`
手动触发数据同步。

**参数：**
- `force` (bool): 强制同步，即使正在进行中

### `GET /api/external-sources/{source_id}/files`
列出数据源中的文件。

**参数：**
- `folder_id` (string): 文件夹ID（可选）
- `limit` (int): 返回数量限制，默认100

### `GET /api/external-sources/{source_id}/status`
获取数据源连接状态。

### `GET /api/external-sources`
列出所有已连接的数据源。

### `DELETE /api/external-sources/{source_id}/disconnect`
断开数据源连接。

### `POST /api/external-sources/{source_id}/webhook`
接收数据源的Webhook事件。

---

## 数据源配置

### Google Drive

```json
{
  "access_token": "OAuth2 access token",
  "refresh_token": "OAuth2 refresh token",
  "client_id": "Google Cloud Console client ID",
  "client_secret": "Google Cloud Console client secret"
}
```

**权限要求：** `https://www.googleapis.com/auth/drive.readonly`

### Gmail

```json
{
  "access_token": "OAuth2 access token",
  "refresh_token": "OAuth2 refresh token",
  "client_id": "Google Cloud Console client ID",
  "client_secret": "Google Cloud Console client secret"
}
```

**权限要求：** `https://www.googleapis.com/auth/gmail.readonly`

### Notion

```json
{
  "access_token": "Notion integration token"
}
```

**设置步骤：**
1. 访问 https://www.notion.so/my-integrations
2. 创建新集成
3. 获取 Internal Integration Token
4. 在需要同步的页面中添加集成连接

### OneDrive

```json
{
  "access_token": "Microsoft Graph access token",
  "refresh_token": "OAuth2 refresh token",
  "client_id": "Azure AD app client ID",
  "client_secret": "Azure AD app client secret",
  "tenant_id": "Azure AD tenant ID (默认: common)"
}
```

**权限要求：** `Files.Read`

### GitHub

```json
{
  "access_token": "GitHub Personal Access Token",
  "repositories": ["owner/repo1", "owner/repo2"]
}
```

**Token 权限：** `repo` (读取仓库内容)

### 本地文件夹

```json
{
  "path": "/absolute/path/to/folder",
  "ignore_patterns": ["__pycache__", ".git", "node_modules"],
  "max_file_size": 52428800
}
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `path` | string | (必填) | 文件夹绝对路径 |
| `ignore_patterns` | list | 常见忽略项 | 要忽略的目录/文件模式 |
| `max_file_size` | int | 50MB | 最大文件大小（字节） |

---

## 架构设计

### 数据源抽象层

```
SourceAdapter (基类)
├── GoogleDriveAdapter
├── GmailAdapter
├── NotionAdapter
├── OneDriveAdapter
├── GitHubAdapter
└── LocalFolderAdapter
```

所有适配器实现统一接口：

```python
class SourceAdapter:
    async def initialize(self) -> bool
    async def connect(self) -> bool
    async def disconnect(self) -> bool
    async def list_files(self, folder_id, limit) -> List[File]
    async def get_file(self, file_id) -> Optional[File]
    async def download_file(self, file_id) -> bytes
    async def list_documents(self, limit) -> List[Document]
    async def get_document(self, doc_id) -> Optional[Document]
    async def search(self, query, limit) -> List[Document]
    async def get_webhook_url(self) -> str
    async def validate_webhook(self, payload, signature) -> bool
    async def handle_webhook(self, payload) -> List[Document]
```

### 统一数据模型

- **Document**: 统一文档模型，包含标题、内容、类型、元数据
- **File**: 统一文件模型，包含名称、大小、MIME类型、下载链接
- **SourceConnection**: 数据源连接配置和状态

### 文档处理管道

```
原始文件 → DocumentProcessor → 提取文本 → 智能分块 → 向量化
```

支持的处理类型：
- **PDF**: PyPDF2 文本提取
- **图片**: PIL + pytesseract OCR
- **代码**: AST 解析（Python）+ 智能分块
- **文本**: 段落/句子智能分块

---

## 搜索集成

跨所有已连接的数据源进行统一搜索：

```python
from app.search.external_search import search_external_sources

# 搜索所有数据源
response = await search_external_sources(
    query="Python tutorial",
    limit=10,
)

# 搜索指定数据源
response = await search_external_sources(
    query="meeting notes",
    source_ids=["gdrive-1", "notion-2"],
    limit=20,
)
```

搜索特性：
- 关键词匹配（标题/内容/标签/作者）
- 分数排序
- 5分钟结果缓存
- 并行多源搜索

---

## Webhook 实时同步

支持的数据源Webhook机制：

| 数据源 | Webhook机制 | 说明 |
|--------|------------|------|
| Google Drive | Google Workspace Events API | 需要配置 Cloud 项目 |
| Gmail | Google Cloud Pub/Sub | 需要创建 Pub/Sub 主题 |
| Notion | Web Endpoint | 需要注册 webhook URL |
| OneDrive | Microsoft Graph 订阅 | 需要创建 subscription |
| GitHub | Repository Webhooks | 在仓库设置中配置 |
| 本地文件夹 | 轮询变更检测 | 使用 `detect_changes()` |

### 处理Webhook

```bash
curl -X POST http://localhost:8000/api/external-sources/{source_id}/webhook \
  -H "Content-Type: application/json" \
  -d '{"type": "file.updated", "data": {"id": "123"}}'
```

---

## 添加自定义适配器

实现 `SourceAdapter` 基类并注册：

```python
from app.services.external_source_service import (
    SourceAdapter, SourceType, external_source_service
)

class MyCustomAdapter(SourceAdapter):
    async def initialize(self) -> bool:
        # 初始化逻辑
        self._initialized = True
        return True

    async def connect(self) -> bool:
        # 连接逻辑
        return True

    # ... 实现其他方法

# 注册
external_source_service.register_adapter(
    SourceType.CUSTOM,
    MyCustomAdapter
)
```

---

## 故障排查

### 连接失败
- 检查 access_token 是否有效
- 验证权限范围是否正确
- 确认网络连通性

### 同步无数据
- 检查数据源中是否有支持的文件类型
- 确认文件大小未超过限制
- 查看日志获取详细错误信息

### 搜索无结果
- 确认数据源已成功同步
- 检查搜索关键词拼写
- 尝试使用更宽泛的搜索词
