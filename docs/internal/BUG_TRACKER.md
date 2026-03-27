# 🐛 Bug 追踪器

> 记录所有发现的问题和修复状态

---

## Bug 列表

| ID | 模块 | 问题描述 | 严重程度 | 状态 | 修复说明 |
|----|------|---------|---------|------|---------|
| BUG-001 | 前端 | 统计数据显示为0 | 高 | ✅ 已修复 | 数据结构处理(data.items vs items) |
| BUG-002 | SDK | URL路径缺少/v1 | 高 | ✅ 已修复 | 添加/v1前缀 |
| BUG-003 | 数据库 | 重复记忆数据 | 中 | ✅ 已修复 | 清理324条重复数据 |
| BUG-004 | 前端 | page_size=200导致422 | 中 | ✅ 已修复 | 改为100 |
| BUG-005 | 前端 | trends数据结构处理 | 中 | ✅ 已修复 | 添加data字段处理 |
| BUG-006 | 前端 | 记忆卡片无点击事件 | 中 | ✅ 已修复 | 添加onclick+弹窗+m.id→m.memory_id |
| BUG-007 | API | GET /memories/{id} 500错误 | 高 | ✅ 已修复 | content字段JSON解析 |
| BUG-008 | API | memory_to_response缺少参数 | 高 | ✅ 已修复 | 添加默认值 |
| BUG-009 | API | transactions计数效率低 | 中 | ✅ 已修复 | len()改为func.count() |
| BUG-010 | API | JSON解析未处理异常 | 中 | ✅ 已修复 | 添加JSONDecodeError处理 |
| BUG-011 | API | update_memory用dict无验证 | 中 | ✅ 已修复 | 改用Pydantic模型 |
| BUG-012 | 代码 | routes.py重复导入 | 低 | ✅ 已修复 | 移除重复导入 |
| BUG-013 | 代码 | exceptions.py未使用导入 | 低 | ✅ 已修复 | 移除未使用导入 |

---

## 详细记录

### BUG-001: 前端统计数据为0
- **发现方式**: 浏览器打开首页，统计数据全部为0
- **根因**: 前端代码期望 `memData.items`，但API返回 `memData.data.items`
- **修复**: 修改前端代码处理两种可能的数据结构
- **验证**: 刷新页面，统计数据正常显示

### BUG-002: SDK URL路径错误
- **发现方式**: 调用 `mm.search()` 返回 404
- **根因**: SDK中URL路径为 `/api/memories`，实际应为 `/api/v1/memories`
- **修复**: sed批量替换所有URL路径
- **验证**: `mm.search(query='抖音')` 返回结果

### BUG-003: 数据库重复数据
- **发现方式**: 搜索结果出现重复条目
- **根因**: 种子脚本被多次运行
- **修复**: SQL去重，保留第一条，删除其余324条
- **验证**: 搜索不再有重复结果

### BUG-004: page_size=200导致422
- **发现方式**: 浏览器控制台报错
- **根因**: API page_size上限为100，前端请求200
- **修复**: 前端page_size改为100
- **验证**: 无422错误

### BUG-005: trends数据结构处理
- **发现方式**: 浏览器控制台报错 "trends is not iterable"
- **根因**: 前端直接赋值 `trends = await resp.json()`，没有处理data包装
- **修复**: 添加 `trendData.data` 处理逻辑
- **验证**: 趋势Tab正常显示数据

---

## 统计

- 总Bug数: 13
- 已修复: 13
- 待修复: 0
