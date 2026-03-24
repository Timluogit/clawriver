# 搜索排序优化实现文档

## 概述

本次优化为 ClawRiver 的搜索功能添加了综合评分排序系统，同时保持向后兼容性。

## 实现位置

- **核心逻辑**: `app/services/memory_service.py` 中的 `search_memories` 函数
- **API 路由**: `app/api/routes.py` 中的 `search_memories_endpoint` 函数

## 综合评分公式

```
综合评分 =
    评分 × 0.3 +
    购买次数 × 0.2 +
    验证分数 × 0.25 +
    最近更新 × 0.15 +
    收藏次数 × 0.1
```

### 各维度归一化方法

#### 1. 评分 (权重 30%)
- **归一化方式**: `avg_score / 5.0`
- **范围**: 0-1
- **说明**: 将0-5分的评分归一化到0-1范围

#### 2. 购买次数 (权重 20%)
- **归一化方式**: `log10(purchase_count + 1) / log10(100)`
- **范围**: 0-1
- **说明**:
  - 使用对数归一化，避免热门记忆完全垄断
  - 假设100次购买为参考最大值
  - +1 避免log(0)问题

#### 3. 验证分数 (权重 25%)
- **归一化方式**: `COALESCE(verification_score, 0.5)`
- **范围**: 0-1
- **说明**:
  - 已验证的记忆使用实际验证分数(0-1)
  - 未验证的记忆使用中性分数0.5

#### 4. 时间衰减 (权重 15%)
- **计算方式**:
  ```sql
  days_old = julianday(now()) - julianday(created_at)
  time_decay =
      CASE
          WHEN days_old <= 7 THEN 1.0          -- 7天内满分
          WHEN days_old <= 30 THEN 1.0 - (days_old - 7) / 23 * 0.5  -- 30天衰减到0.5
          ELSE 0.5                              -- 30天后保持0.5
      END
  ```
- **说明**:
  - 新记忆(7天内)获得满分
  - 7-30天线性衰减
  - 30天后保持基础分数0.5

#### 5. 收藏次数 (权重 10%)
- **归一化方式**: `log10(favorite_count + 1) / log10(50)`
- **范围**: 0-1
- **说明**:
  - 使用对数归一化
  - 假设50次收藏为参考最大值

### 文本匹配度加权

当有搜索关键词时，标题匹配的记忆额外获得 **0.2分** 加成：

```python
if query:
    title_match_bonus = case(
        (Memory.title.ilike(f"%{query}%"), 0.2),
        else_=0.0
    )
    composite_score = composite_score + title_match_bonus
```

## API 使用方法

### 请求参数

```http
GET /api/memories?sort_by=relevance&page=1&page_size=10
```

### sort_by 参数选项

| 值 | 说明 | 排序方式 |
|---|---|---|
| `relevance` | 综合评分（默认） | 按综合评分倒序 |
| `created_at` | 创建时间 | 按创建时间倒序 |
| `purchase_count` | 购买次数 | 按购买次数倒序 |
| `price` | 价格 | 按价格升序 |

### 示例请求

```bash
# 综合评分排序（默认）
curl "http://localhost:8000/api/memories?sort_by=relevance"

# 按创建时间排序
curl "http://localhost:8000/api/memories?sort_by=created_at"

# 搜索 + 综合评分
curl "http://localhost:8000/api/memories?query=agent&sort_by=relevance"

# 按价格排序
curl "http://localhost:8000/api/memories?sort_by=price"
```

## 技术实现细节

### SQLAlchemy 查询

使用 SQLAlchemy 的 `case` 和 `func` 构建复杂排序表达式：

```python
from sqlalchemy import case, func, desc

# 综合评分表达式
composite_score = (
    score_normalized * 0.3 +
    purchase_normalized * 0.2 +
    verification_normalized * 0.25 +
    time_decay * 0.15 +
    favorite_normalized * 0.1
)

# 应用排序
stmt = stmt.order_by(desc(composite_score))
```

### 数据库兼容性

- **SQLite**: 使用 `julianday()` 计算时间差
- **PostgreSQL**: 可使用 `EXTRACT(EPOCH FROM ...)` 替代
- **MySQL**: 可使用 `DATEDIFF()` 替代

当前实现针对 SQLite，如需切换数据库需调整时间衰减计算部分。

## 性能优化考虑

1. **避免复杂子查询**: 所有计算在 SELECT/ORDER BY 层级完成
2. **利用索引**: 确保 `is_active`, `created_at` 等字段有索引
3. **分页优先**: 先应用筛选，再排序，最后分页
4. **对数归一化**: 减少极端值对排序的影响

## 向后兼容性

- **默认行为**: `sort_by="relevance"` 使用新的综合评分
- **保持兼容**: 仍可通过 `sort_by="created_at"` 获得原来的时间排序
- **可选参数**: 不传 `sort_by` 时使用综合评分（默认）

## 测试建议

### 测试用例

1. **综合评分排序**: 验证各维度权重是否正确
2. **时间衰减**: 创建不同时间的记忆，验证衰减曲线
3. **文本匹配**: 测试有/无搜索关键词的排序差异
4. **边界情况**: 无评分、无购买、新记忆等
5. **性能测试**: 大数据量下的查询性能

### 测试脚本

参考 `test_search_sorting.py` 文件。

## 未来优化方向

1. **机器学习排序**: 基于用户行为训练个性化排序模型
2. **动态权重**: 根据用户类型/场景调整权重
3. **缓存优化**: 对热门查询缓存排序结果
4. **A/B测试**: 测试不同权重配置的效果
5. **多数据库支持**: 适配 PostgreSQL/MySQL 的时间函数

## 变更日志

- **2026-03-22**: 初始实现综合评分排序系统
  - 添加 5 维度评分公式
  - 实现文本匹配度加权
  - 支持 4 种排序方式
  - 保持向后兼容性
