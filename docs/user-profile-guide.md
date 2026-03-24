# 用户画像系统指南

## 概述

用户画像系统是 ClawRiver 的核心功能之一，用于自动化构建和维护用户画像，提供个性化体验。

### 核心特性

- **两层画像架构**：静态事实层 + 动态上下文层
- **自动提取**：从对话中自动提取用户信息
- **自动更新**：实时追踪用户画像变化
- **自动遗忘**：过期事实自动失效
- **高性能**：<50ms API响应，Redis缓存优化
- **隐私保护**：用户可删除画像信息

## 系统设计

### 两层画像架构

#### 1. 静态事实层（UserProfile）

存储用户的长期、稳定信息：

- **个人信息**：姓名、职位、公司、地点、时区
- **偏好**：语言、编辑器、主题、UI缩放
- **习惯**：工作时间、工作日、常用命令
- **技能**：编程语言、框架、技术栈
- **兴趣**：兴趣领域、研究方向

#### 2. 动态上下文层（UserDynamicContext）

存储用户的短期、动态信息：

- **当前状态**：当前任务、当前项目、当前关注点
- **工作状态**：active/away/busy/offline
- **最近活动**：搜索历史、交互记忆
- **推荐信息**：推荐分类、建议主题
- **统计信息**：今日会话数、今日搜索数

### 数据模型

```
UserProfile (主表)
├── 基础字段
├── 事实关联 (ProfileFact)
└── 变更历史 (ProfileChange)

ProfileFact (事实表)
├── 事实类型
├── 事实键值
├── 置信度
└── 过期时间

UserDynamicContext (动态上下文表)
├── 当前状态
├── 最近活动
└── 推荐信息
```

## 使用指南

### 1. 获取用户画像

```python
from app.services.user_profile_service import get_profile_service

service = get_profile_service()

# 获取用户画像
profile = await service.get_profile(db, agent_id, use_cache=True)

if profile:
    print(f"用户语言: {profile['language']}")
    print(f"编辑器: {profile['editor']}")
    print(f"完整度: {profile['completeness_score']}")
```

### 2. 更新用户画像

```python
# 更新画像
profile_data = {
    'real_name': 'John Doe',
    'job_title': 'Software Engineer',
    'language': 'en',
    'editor': 'VSCode',
    'theme': 'dark'
}

profile = await service.create_or_update_profile(
    db,
    agent_id,
    profile_data,
    source='manual'
)
```

### 3. 添加画像事实

```python
# 添加事实
fact = await service.add_fact(
    db,
    agent_id,
    fact_type='preference',
    fact_key='editor',
    fact_value='Vim',
    confidence=0.9,
    source='manual'
)
```

### 4. 获取事实列表

```python
# 获取所有事实
facts = await service.get_facts(db, agent_id)

# 获取特定类型的事实
preference_facts = await service.get_facts(
    db,
    agent_id,
    fact_type='preference',
    is_valid=True
)
```

### 5. 从对话中提取画像

```python
from app.services.profile_extraction_service import get_extraction_service

service = get_extraction_service()

conversation = """
User: 我是用 Python 的工程师，平时用 VSCode 编辑器
Assistant: 了解，Python 和 VSCode
"""

result = await service.extract_from_conversation(
    db,
    agent_id,
    conversation,
    conversation_id="conv_001"
)

print(f"提取了 {result['total_extracted']} 个事实")
print(f"置信度: {result['confidence']}")
```

### 6. 获取动态上下文

```python
# 获取动态上下文
context = await service.get_dynamic_context(db, agent_id)

if context:
    print(f"当前任务: {context['current_task']}")
    print(f"工作状态: {context['work_state']}")
    print(f"今日搜索数: {context['search_count_today']}")
```

### 7. 更新动态上下文

```python
# 更新动态上下文
context_data = {
    'current_task': 'Debug API issue',
    'work_state': 'busy',
    'last_search_query': 'FastAPI timeout',
    'search_count_today': 10
}

context = await service.update_dynamic_context(
    db,
    agent_id,
    context_data
)
```

### 8. 查看变更历史

```python
# 获取变更历史
changes = await service.get_changes(db, agent_id, limit=50)

for change in changes:
    print(f"{change['created_at']}: {change['change_type']} {change['field_name']}")
    if change['old_value']:
        print(f"  旧值: {change['old_value']}")
    if change['new_value']:
        print(f"  新值: {change['new_value']}")
```

## API 参考

### 端点列表

#### 获取画像
- **GET** `/user-profiles/me`
- 描述：获取当前用户画像
- 响应：`ProfileResponse`

#### 更新画像
- **PUT** `/user-profiles/me`
- 描述：更新当前用户画像
- 请求：`ProfileUpdateRequest`
- 响应：`ProfileResponse`

#### 获取变更历史
- **GET** `/user-profiles/me/history?limit=50`
- 描述：获取画像变更历史
- 响应：`List[ChangeResponse]`

#### 获取事实列表
- **GET** `/user-profiles/me/facts?fact_type=preference&is_valid=true`
- 描述：获取画像事实列表
- 响应：`List[FactResponse]`

#### 添加事实
- **POST** `/user-profiles/me/facts`
- 描述：手动添加画像事实
- 请求：`FactCreateRequest`
- 响应：`FactResponse`

#### 删除事实
- **DELETE** `/user-profiles/me/facts/{fact_id}`
- 描述：删除画像事实
- 响应：204 No Content

#### 获取动态上下文
- **GET** `/user-profiles/me/context`
- 描述：获取用户动态上下文
- 响应：`DynamicContextResponse`

#### 更新动态上下文
- **PUT** `/user-profiles/me/context`
- 描述：更新用户动态上下文
- 请求：`DynamicContextUpdateRequest`
- 响应：`DynamicContextResponse`

#### 从对话提取
- **POST** `/user-profiles/extract`
- 描述：从对话中自动提取画像信息
- 请求：`ExtractFromConversationRequest`
- 响应：`ExtractFromConversationResponse`

### 请求/响应模型

#### ProfileResponse
```json
{
  "profile_id": "uprof_xxx",
  "agent_id": "agent_xxx",
  "real_name": "John Doe",
  "job_title": "Software Engineer",
  "language": "zh",
  "editor": "VSCode",
  "theme": "dark",
  "facts": {
    "personal": [...],
    "preference": [...],
    "skill": [...]
  },
  "completeness_score": 0.75,
  "confidence_score": 0.85,
  "last_updated_at": "2024-03-23T13:00:00Z",
  "created_at": "2024-03-23T10:00:00Z"
}
```

#### FactResponse
```json
{
  "fact_id": "fact_xxx",
  "fact_type": "preference",
  "fact_key": "editor",
  "fact_value": "VSCode",
  "confidence": 0.9,
  "source": "manual",
  "created_at": "2024-03-23T13:00:00Z",
  "is_valid": true
}
```

#### ExtractFromConversationResponse
```json
{
  "facts": [
    {
      "field": "language",
      "value": "zh",
      "confidence": 0.8,
      "type": "preference"
    }
  ],
  "total_extracted": 3,
  "confidence": 0.75,
  "extraction_time": "2024-03-23T13:00:00Z"
}
```

## 个性化搜索

### 启用个性化搜索

```python
from app.search.hybrid_search import get_hybrid_engine

engine = get_hybrid_engine()

# 个性化搜索
results = await engine.personalized_search(
    db=db,
    query="FastAPI 最佳实践",
    agent_id=agent_id,
    base_stmt=base_query,
    search_type="hybrid",
    top_k=50
)
```

### 个性化策略

系统根据用户画像优化搜索结果：

1. **语言匹配**：根据用户语言偏好优先展示对应语言的内容
2. **兴趣匹配**：优先展示用户兴趣领域相关的记忆
3. **技术栈匹配**：优先展示用户熟悉的技术栈内容
4. **编辑器偏好**：对于编程内容，优先展示用户编辑器相关的技巧
5. **主题偏好**：对于UI/设计内容，优先展示用户主题偏好的方案

### 个性化得分计算

```python
personalization_score = (
    language_match * 0.1 +
    interest_match * 0.2 +
    tech_stack_match * 0.1 +
    editor_preference * 0.15 +
    theme_preference * 0.1
)

final_score = base_relevance * 0.8 + personalization_score * 0.2
```

## 配置说明

### 环境变量

```bash
# 启用画像系统
PROFILE_ENABLED=true

# 启用自动提取
PROFILE_AUTO_EXTRACTION=true

# 最小置信度（0-1）
PROFILE_MIN_CONFIDENCE=0.6

# 缓存TTL（秒）
PROFILE_CACHE_TTL=300

# 自动遗忘天数
PROFILE_AUTO_FORGET_DAYS=30

# 提取模型
PROFILE_EXTRACTION_MODEL=gpt-4o-mini

# 最大字段数
PROFILE_MAX_FIELDS=30
```

## 最佳实践

### 1. 定期清理过期事实

```python
# 定期任务（如每天凌晨）
from app.services.profile_extraction_service import get_extraction_service

service = get_extraction_service()
await service.auto_forget_expired_facts(db)
```

### 2. 缓存优化

- 使用 Redis 缓存画像数据（默认5分钟TTL）
- 画像更新后自动清除缓存
- 读多写少场景建议启用缓存

### 3. 隐私保护

- 允许用户删除画像事实
- 过期事实自动失效
- 变更历史可追溯

### 4. 提取准确率优化

- 设置合理的最小置信度（0.6-0.8）
- 使用高质量的 LLM 进行提取
- 结合规则提取和 LLM 提取

### 5. 性能优化

- 画像查询使用缓存（<50ms）
- 批量操作避免频繁数据库写入
- 使用索引优化查询性能

## 故障排查

### 问题：画像提取失败

**可能原因：**
1. LLM API 不可用
2. 对话文本为空
3. 画像系统未启用

**解决方案：**
1. 检查 `PROFILE_ENABLED` 和 `PROFILE_AUTO_EXTRACTION` 配置
2. 检查 LLM API 连接
3. 查看日志错误信息

### 问题：缓存未生效

**可能原因：**
1. Redis 未连接
2. 缓存键冲突
3. 缓存过期

**解决方案：**
1. 检查 Redis 连接状态
2. 清除缓存重试
3. 调整 `PROFILE_CACHE_TTL` 配置

### 问题：个性化搜索不生效

**可能原因：**
1. 用户画像不存在
2. 画像数据不完整
3. 搜索类型错误

**解决方案：**
1. 检查用户是否已创建画像
2. 检查画像完整度
3. 确认使用 `personalized_search` 方法

## 性能指标

### 目标指标

- **画像API延迟**: <50ms
- **画像构建延迟**: <500ms
- **存储查询延迟**: <10ms
- **自动提取准确率**: >80%
- **自动更新成功率**: >90%
- **画像字段数**: >20个

### 测试方法

```bash
# 运行画像系统测试
pytest tests/test_user_profiles.py -v

# 性能测试
pytest tests/test_user_profiles.py::TestProfileExtraction::test_extract_from_conversation --benchmark-only
```

## 未来改进

1. **多模态提取**：从语音、图片中提取画像信息
2. **社交图谱**：基于用户关系构建画像
3. **实时更新**：WebSocket 推送画像变更
4. **AI 推荐引擎**：基于画像的智能推荐
5. **隐私增强**：差分隐私保护

## 参考资料

- [Supermemory 用户画像系统](https://github.com/supermemory-ai/supermemory)
- [用户画像最佳实践](https://arxiv.org/abs/2005.14165)
- [隐私保护用户画像](https://dl.acm.org/doi/10.1145/3340531.3412004)
