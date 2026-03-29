# A-MEM (Agentic Memory) Implementation Plan

## Architecture Overview

A-MEM 是一个自进化记忆系统，灵感来自 Zettelkasten 笔记方法。每条记忆都是一个结构化笔记，系统在新记忆加入时自动建立关联并"进化"已有记忆。

## 核心数据流

```
新交互内容
    │
    ▼
┌─────────────┐
│ NoteBuilder │ ── LLM 提取 keywords, tags, context_desc
│             │ ── sentence-transformers 生成 embedding
└─────┬───────┘
      │ AgenticMemory
      ▼
┌──────────────────┐
│ LinkGenerator    │ ── 余弦相似度 top-k 候选
│                  │ ── LLM 确认链接关系
└─────┬────────────┘
      │ linked_ids
      ▼
┌──────────────────┐
│ MemoryEvolver    │ ── LLM 分析新记忆对旧记忆的影响
│                  │ ── 更新旧记忆的 context_desc/keywords/tags
└─────┬────────────┘
      │ updated memories
      ▼
┌──────────────────┐
│ AmevEngine       │ ── 存储 + 索引
│                  │ ── 提供 search() 接口
└──────────────────┘
```

## 模块划分

| 文件 | 职责 |
|------|------|
| `amev_schema.py` | 数据模型 (AgenticMemory, LLMClient ABC) |
| `llm_client.py` | LLM 抽象基类 + Mock 实现 |
| `note_builder.py` | 笔记构建：LLM 提取元数据 + 嵌入 |
| `link_generator.py` | 链接生成：相似度检索 + LLM 确认 |
| `memory_evolver.py` | 记忆进化：LLM 分析影响 + 更新旧记忆 |
| `amev_engine.py` | 主引擎：串联所有组件 |
| `test_amev.py` | 单元测试（Mock LLM，不依赖真实 API） |

## 技术选型

- **嵌入模型**: sentence-transformers / all-MiniLM-L6-v2 (384维)
- **LLM 抽象**: Protocol class + Mock 实现，便于测试
- **相似度**: numpy 余弦相似度
- **ID 生成**: uuid4
- **测试**: pytest + unittest.mock

## 设计决策

1. **LLMClient 使用 Protocol 而非 ABC** — 更 Pythonic，duck typing 兼容
2. **embedding 作为 np.ndarray 存储** — 便于相似度计算
3. **LinkGenerator 两阶段** — 先粗筛(向量相似度)，再精筛(LLM确认)，平衡效率与质量
4. **MemoryEvolver 返回更新列表** — 不直接修改，由 Engine 决定是否应用
5. **search() 包含关联扩展** — 检索结果的直接链接记忆也加入，提升召回率
