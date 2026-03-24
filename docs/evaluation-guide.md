# Agent知识之河 - 评估框架使用指南

## 概述

评估框架提供类似 LangSmith 的能力，支持对记忆搜索系统进行全面质量评估。

### 核心能力

| 能力 | 说明 |
|------|------|
| 评估指标 | 准确率、精确率、召回率、F1、MRR、NDCG |
| 测试数据集 | 用例管理、自动生成、导入导出 |
| 评估执行 | 并行执行、结果收集、历史管理 |
| 评估报告 | Markdown/JSON/HTML 报告、可视化、对比分析 |

---

## 快速开始

### 1. 创建测试数据集

```bash
# 通过 API
curl -X POST http://localhost:8000/api/eval/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "搜索质量评估",
    "description": "评估记忆搜索的准确性和相关性",
    "test_cases": [
      {
        "query": "Python编程最佳实践",
        "expected_ids": ["mem_001", "mem_002"],
        "category": "tech"
      },
      {
        "query": "如何优化数据库查询",
        "expected_keywords": ["索引", "优化", "SQL"],
        "category": "tech"
      }
    ]
  }'
```

### 2. 运行评估

```bash
curl -X POST http://localhost:8000/api/eval/run \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "<your_dataset_id>",
    "run_name": "baseline_eval",
    "k": 10,
    "parallel": 4
  }'
```

### 3. 获取结果

```bash
# JSON 结果
curl http://localhost:8000/api/eval/results/<result_id>

# Markdown 报告
curl http://localhost:8000/api/eval/results/<result_id>/report?format=markdown

# HTML 报告
curl http://localhost:8000/api/eval/results/<result_id>/report?format=html
```

### 4. 对比结果

```bash
curl "http://localhost:8000/api/eval/compare?ids=result1,result2"
```

---

## 评估指标详解

### 准确率 (Accuracy)
- **公式:** `|predicted ∩ expected| / |predicted ∪ expected|`
- **用途:** 衡量预测结果与期望结果的重合度
- **范围:** [0, 1]，越高越好

### 精确率 (Precision)
- **公式:** `|predicted ∩ expected| / |predicted|`
- **用途:** 衡量返回结果中正确结果的比例
- **场景:** 当"误报"代价高时关注此指标

### 召回率 (Recall)
- **公式:** `|predicted ∩ expected| / |expected|`
- **用途:** 衡量应返回的结果中实际被返回的比例
- **场景:** 当"漏报"代价高时关注此指标

### F1 分数
- **公式:** `2 × Precision × Recall / (Precision + Recall)`
- **用途:** 精确率和召回率的调和平均数

### MRR (Mean Reciprocal Rank)
- **公式:** `1 / rank_of_first_relevant_result`
- **用途:** 衡量第一个正确结果出现的位置
- **场景:** 搜索引擎等需要排名的场景

### NDCG (Normalized Discounted Cumulative Gain)
- **公式:** `DCG / IDCG`
- **用途:** 考虑排序位置的综合指标
- **场景:** 推荐系统、搜索引擎

---

## API 参考

### 数据集管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/eval/datasets` | 列出所有数据集 |
| POST | `/api/eval/datasets` | 创建数据集 |
| GET | `/api/eval/datasets/{id}` | 获取数据集详情 |
| DELETE | `/api/eval/datasets/{id}` | 删除数据集 |
| POST | `/api/eval/datasets/{id}/cases` | 添加测试用例 |

### 评估运行

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/eval/run` | 运行评估 |
| GET | `/api/eval/results` | 列出评估结果 |
| GET | `/api/eval/results/{id}` | 获取评估结果 |
| GET | `/api/eval/results/{id}/report` | 获取评估报告 |
| GET | `/api/eval/compare` | 对比评估结果 |

### 请求体示例

**创建数据集:**
```json
{
  "name": "搜索质量v1",
  "description": "第一版搜索质量评估",
  "test_cases": [
    {
      "query": "Python异步编程",
      "expected_ids": ["mem_001"],
      "expected_keywords": ["async", "await"],
      "category": "tech",
      "tags": ["python", "async"]
    }
  ]
}
```

**运行评估:**
```json
{
  "dataset_id": "abc123",
  "run_name": "v2.0基准测试",
  "k": 10,
  "parallel": 4,
  "categories": ["tech"],
  "config": {"model": "bge-small-zh"}
}
```

---

## 编程接口

### Python SDK 示例

```python
from app.eval.metrics import EvaluationMetrics
from app.eval.datasets import DatasetManager, TestCase
from app.eval.runner import EvaluationRunner
from app.eval.report import EvaluationReport

# 1. 计算指标
metrics = EvaluationMetrics.evaluate_retrieval(
    predicted_ranked=["mem1", "mem2", "mem3"],
    expected={"mem1", "mem4"},
    k=10
)
print(f"Precision: {metrics['precision'].value:.4f}")
print(f"Recall: {metrics['recall'].value:.4f}")
print(f"F1: {metrics['f1'].value:.4f}")
print(f"MRR: {metrics['mrr'].value:.4f}")
print(f"NDCG: {metrics['ndcg'].value:.4f}")

# 2. 创建数据集
dm = DatasetManager()
ds = dm.create_dataset("my_eval", "我的评估")
ds.add_case(TestCase(
    query="Python教程",
    expected_ids={"mem_001", "mem_002"},
    category="tech"
))

# 3. 运行评估
runner = EvaluationRunner(dm)

async def my_search(query: str):
    # 你的搜索实现
    return [{"id": "mem_001", "content": "..."}]

result = await runner.run(
    dataset_id=ds.id,
    search_func=my_search,
    k=10,
    parallel=4
)

# 4. 生成报告
report = EvaluationReport.to_markdown(result)
print(report)
```

### 自动数据集生成

```python
# 从现有记忆生成测试数据集
memories = [
    {"id": "m1", "content": "Python is great", "category": "tech"},
    {"id": "m2", "content": "Machine learning rocks", "category": "tech"},
]
ds = dm.generate_from_memories(memories, name="auto_eval", num_cases=50)

# 从模板生成合成数据集
templates = [{
    "query_template": "如何{topic}?",
    "topics": ["学习Python", "优化SQL", "调试代码"],
    "keywords": ["方法", "技巧"],
    "category": "tech",
}]
ds = dm.generate_synthetic(templates, name="synthetic", num_cases=20)
```

---

## 报告格式

### Markdown 报告

```
# 评估报告: baseline_eval

- **评估ID:** `abc123`
- **数据集:** 搜索质量评估
- **状态:** completed
- **耗时:** 2.50s
- **测试用例:** 100 (完成: 98, 失败: 2)
- **成功率:** 98.0%

## 聚合指标

| 指标 | 值 | 说明 |
|------|-----|------|
| 准确率 | 0.8500 | - |
| 精确率 | 0.9000 | - |
| 召回率 | 0.8000 | - |
| F1分数 | 0.8470 | - |
| MRR | 0.9500 | - |
| NDCG | 0.8800 | - |

## 指标可视化

  准确率 │████████████████████████████████████░░░░│ 0.8500
  精确率 │████████████████████████████████████████│ 0.9000
  召回率 │██████████████████████████████████░░░░░░│ 0.8000
```

### 对比报告

支持对比多个评估运行的结果，直观展示性能差异。

---

## 最佳实践

### 测试用例设计

1. **覆盖多类别:** 确保测试用例覆盖不同类别（技术、通用、个人等）
2. **边界情况:** 包含空查询、长查询、特殊字符等边界情况
3. **数量充足:** 每个类别至少10-20个用例，确保统计显著性
4. **定期更新:** 随系统迭代更新测试数据集

### 评估频率

- **基准测试:** 每次重大变更后运行
- **回归测试:** 每周运行一次
- **持续监控:** 生产环境建议每日自动运行

### 指标选择

| 场景 | 推荐指标 |
|------|----------|
| 搜索质量 | NDCG, MRR |
| 分类准确性 | F1, Precision, Recall |
| 推荐系统 | NDCG, MRR |
| 总体评估 | 所有指标综合 |

---

## 故障排查

### 常见问题

**Q: 评估运行失败，显示"数据集不存在"**
A: 检查 dataset_id 是否正确，可通过 `GET /api/eval/datasets` 确认

**Q: 所有用例都失败**
A: 检查搜索函数是否正确实现，确认数据库连接正常

**Q: 指标全为0**
A: 检查 expected_ids 或 expected_keywords 是否正确设置

**Q: 评估速度慢**
A: 增加 parallel 参数，或减少测试用例数量

---

## 文件结构

```
app/eval/
├── __init__.py          # 模块导出
├── metrics.py           # 评估指标
├── datasets.py          # 数据集管理
├── runner.py            # 评估执行器
└── report.py            # 报告生成

app/api/
└── evaluation.py        # API 路由

tests/
└── test_evaluation.py   # 单元测试

docs/
└── evaluation-guide.md  # 本文档
```
