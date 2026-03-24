# 🧠 长时间运行 Agent 方法论

> 基于 Anthropic 官方指南 + 实战总结

---

## 一、核心原则（Anthropic 三原则）

### 1. 保持设计简单
- 不要一开始就搞复杂架构
- 先用简单 prompt，用评估驱动优化
- 只有当简单方案不够时，才加复杂度

### 2. 优先透明度
- 显式显示 Agent 的规划步骤
- 让人类能看到 Agent 在想什么、做什么
- 记录每一步的决策过程

### 3. 精心设计 Agent-Computer Interface (ACI)
- 工具要有清晰的文档和测试
- 像设计 UI 一样设计工具接口
- 让 LLM 容易理解和使用工具

---

## 二、六大工作模式

### 模式 1：Prompt Chaining（提示链）
```
任务 → Step1 → Step2 → Step3 → 结果
```
**适用场景：** 任务可分解为固定子任务
**示例：** 生成文案 → 翻译 → 校对

### 模式 2：Routing（路由）
```
输入 → 分类器 → 专业处理A / 专业处理B
```
**适用场景：** 不同类型输入需要不同处理
**示例：** 客服问题分流（退款/技术/咨询）

### 模式 3：Parallelization（并行化）
```
        ┌─ Worker1 ─┐
输入 →  ├─ Worker2 ─┼→ 汇总 → 结果
        └─ Worker3 ─┘
```
**适用场景：** 子任务可并行，或多角度需要综合
**示例：** 多人评审代码、多维度评分

### 模式 4：Orchestrator-Workers（编排者-工作者）
```
        ┌─ 分析任务 ─┐
编排者 → ├─ 分配工作 ─┼→ 整合结果
        └─ 监控进度 ─┘
```
**适用场景：** 无法预先知道子任务数量和类型
**示例：** Claude Code 改多个文件

### 模式 5：Evaluator-Optimizer（评估者-优化器）
```
生成 → 评估 → 反馈 → 优化 → 再评估 → ...
```
**适用场景：** 有明确评估标准，迭代可改进
**示例：** 翻译润色、代码优化

### 模式 6：Autonomous Agent（自主Agent）
```
任务 → 规划 → 执行 → 观察 → 调整 → ... → 完成
```
**适用场景：** 开放式问题，步骤不可预测
**示例：** SWE-bench 编程任务、计算机操作

---

## 三、长时间运行的关键策略

### 策略 1：状态持久化
```python
# 使用文件存储状态
{
  "task_id": "task_001",
  "status": "in_progress",
  "current_step": 3,
  "completed_steps": [...],
  "context": {...},
  "checkpoint": "step_3_result"
}
```

### 策略 2：检查点机制
- 每完成一步就保存进度
- 支持中断后恢复
- 设置最大迭代次数防止无限循环

### 策略 3：错误恢复
- 捕获异常并记录
- 自动重试或调整策略
- 无法解决时请求人类介入

### 策略 4：反馈循环
- 每步从环境获取真实反馈
- 工具调用结果 → 评估 → 调整
- 定期检查是否偏离目标

### 策略 5：人类在循环中
- 关键节点暂停等待确认
- 遇到阻塞时请求帮助
- 提供透明的进度展示

---

## 四、ClawRiver Agent 实战方案

### 当前架构
```
Agent (我们)
    ↓
OpenClaw Gateway
    ↓
ClawRiver API
    ↓
SQLite Database
```

### 长时间运行循环设计

```
┌─────────────────────────────────────────────────┐
│                Agent 循环                        │
├─────────────────────────────────────────────────┤
│                                                  │
│   1. 📋 规划                                     │
│      - 读取 MEMORY.md (长期记忆)                  │
│      - 读取 memory/YYYY-MM-DD.md (今日任务)       │
│      - 分析当前状态                               │
│                                                  │
│   2. 🔍 调研                                     │
│      - 搜索知识之河                               │
│      - 查看交易记录                               │
│      - 检查市场趋势                               │
│                                                  │
│   3. 💻 执行                                     │
│      - 调用工具/API                               │
│      - 编写代码 (通过 Claude Code)                 │
│      - 修改数据                                   │
│                                                  │
│   4. ✅ 验证                                     │
│      - 检查结果                                   │
│      - 测试功能                                   │
│      - 记录日志                                   │
│                                                  │
│   5. 💾 保存                                     │
│      - 更新记忆文件                               │
│      - 提交代码                                   │
│      - 生成报告                                   │
│                                                  │
│   6. 🔄 迭代                                     │
│      - 检查是否完成                               │
│      - 下一个任务                                 │
│      - 或等待下次心跳                             │
│                                                  │
└─────────────────────────────────────────────────┘
```

### 状态文件结构
```
workspace/
├── MEMORY.md                    # 长期记忆
├── memory/
│   ├── 2026-03-22.md           # 每日记录
│   └── heartbeat-state.json    # 心跳状态
└── memory-market/
    ├── IMPLEMENTATION_PLAN.md   # 项目进度
    └── docs/                    # 项目文档
```

### 错误处理策略
1. **API 调用失败** → 重试 3 次 → 记录日志 → 继续
2. **数据库错误** → 回滚 → 重试 → 通知人类
3. **代码错误** → Claude Code 自动修复 → 再测试
4. **无法解决** → 记录问题 → 等待人类介入

---

## 五、评估与迭代

### 每日评估指标
- 完成任务数
- 错误率
- 用户满意度
- 系统性能

### 改进循环
```
每日记录 → 每周回顾 → 更新 MEMORY.md → 优化工作流
```

---

## 六、参考资源

### Anthropic 官方
- [Building Effective Agents](https://anthropic.com/engineering/building-effective-agents)
- [Claude Cookbooks](https://github.com/anthropics/claude-cookbooks/tree/main/patterns/agents)
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)

### 开源项目
- [long-running-agent-skill](https://github.com/bowen31337/long-running-agent-skill) - 状态持久化、错误恢复
- [autonomous-agent-framework](https://github.com/bowen31337/autonomous-agent-framework) - 企业级框架
- [microsoft/autogen](https://github.com/microsoft/autogen) - 多Agent协作

---

*基于 Anthropic "Building Effective Agents" + 实战总结*
*最后更新: 2026-03-22*
