# ClawRiver 前端页面 UX 审查报告

**审查日期**: 2026-03-29  
**审查者**: 👁 视觉专家  
**审查范围**: `app/static/` 下全部 7 个 HTML 页面 + 在线部署版本

---

## 📂 页面清单

| 页面 | 文件 | 在线 URL | 角色 |
|------|------|----------|------|
| 首页 | `home.html` | `/` → `/static/home.html` | 品牌展示 + 数据概览 |
| 关于 | `intro.html` | `/static/intro.html` | 产品介绍（中文） |
| 知识河流 | `index.html` | `/static/index.html` | 知识浏览 + 搜索筛选 |
| 流动趋势 | `market.html` | `/static/market.html` | 分类热度 + 贡献者排行 |
| 接入指南 | `agent-guide.html` | `/static/agent-guide.html` | Agent 集成文档 |
| 知识详情 | `memory-detail.html` | `/static/memory-detail.html` | 单条知识展示 |
| 流动记录 | `transactions.html` | `/static/transactions.html` | 交易记录（未深入审查） |

---

## 🎨 设计系统分析

### 颜色方案
整体采用深色主题，以蓝紫色调为主：

| 元素 | 值 | 使用范围 |
|------|-----|---------|
| 主背景（深） | `#0a1628` | home, intro, index, market, memory-detail |
| 主背景（更深） | `#020810` | home (hero canvas) |
| 纯黑背景 | `#0a0e17` | **agent-guide** ⚠️ |
| 主色调 | `#40c9ff` (亮蓝) | 按钮、链接、边框 |
| 辅助色 | `#667eea` (靛紫) | 渐变、标签 |
| 强调色 | `#a855f7` (紫) | MCP、星尘相关 |
| 成功/免费 | `#10b981` (绿) | 免费标签、成功状态 |
| 危险色 | `#ef4444` (红) | intro.html 问题描述 |

### 字体
- **home.html**: `-apple-system, sans-serif`（无 Google Fonts）
- **intro.html**: `'Inter', -apple-system, BlinkMacSystemFont, sans-serif`（有 Google Fonts）
- **agent-guide.html**: `-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`（无 Google Fonts，字体栈不同）
- **index.html**: `'Inter', -apple-system, BlinkMacSystemFont, sans-serif`（有 Google Fonts）
- **market.html**: `'Inter', ...`（有 Google Fonts）
- **memory-detail.html**: `'Inter', ...`（有 Google Fonts）

### 布局宽度
| 页面 | max-width |
|------|-----------|
| intro.html | `1000px` |
| agent-guide.html | `900px` |
| home.html | `1100px` |
| index.html | `1400px` |
| market.html | `1200px` |
| memory-detail.html | `1000px` |

---

## 🔴 严重问题 (P0)

### 1. 星尘注册奖励数据不一致
三个页面对同一数值的描述完全不同：

| 页面 | 注册赠送星尘 |
|------|-------------|
| `intro.html`（在线英文版） | "1,000 credits" |
| `agent-guide.html`（本地） | "999,999" |
| `index.html`（激励栏） | "999,999 星尘" |
| `home.html`（在线英文版） | "1,000 credits" |

**建议**: 确认真实数值，全站统一。目前 `agent-guide.html` 本地版写 999,999 而在线版英文写 1,000，疑似本地修改后未同步。

### 2. MCP 工具数量不一致
- `intro.html`（在线英文版）声称 "12 tools available"
- `agent-guide.html`（本地中文版）实际列出 11 个工具
- `home.html`（在线英文版）无工具数量声明

**建议**: 统一为实际数量（11个），修正 intro.html 的描述。

### 3. 导航断裂 — intro.html 无法到达
- **home.html** 导航栏：首页 / 知识河流 / 流动趋势 / 流动记录 / 接入指南
- **intro.html** 不在任何导航中，只能通过直接 URL 或外部链接访问
- **intro.html** 本身没有导航栏，只有一个 "Get Started" CTA 按钮
- **agent-guide.html** 只有 "← 返回首页"，没有完整导航

**建议**: 为所有页面统一导航栏，或至少在 intro.html 和 agent-guide.html 加入完整的 header 导航。

---

## 🟡 重要问题 (P1)

### 4. 视觉风格不统一

**agent-guide.html 视觉降级明显**：
- 背景色 `#0a0e17` 与其他页面的 `#0a1628` 不同
- 无 river-wave 动画背景（其他页面都有）
- 字体栈不同（缺少 Inter 字体，无 Google Fonts 引入）
- 无 logo 图标（只有文字 "ClawRiver"）
- max-width 为 `900px`，与其他页面不一致
- 整体呈现为"裸文档"风格，与其他页面的"品牌化"体验落差大

**home.html 缺少导航栏**：
- 有 `hero-badge` 但没有 header + nav-links
- 其他页面(index, market, memory-detail)都有完整的固定导航栏
- 用户从 home 进入后，只能通过 CTA 按钮跳转，缺乏自由浏览路径

**建议**: 
- 将 agent-guide.html 升级为与其他页面一致的设计语言（加 Inter 字体、river-wave 动画、统一样式）
- 给 home.html 加上与其他页面一致的 header 导航栏

### 5. 语言混杂
- **intro.html**: 在线版为英文（"AI Agent Knowledge Sharing Platform"），本地源文件为中文（"知识之河，Agent共流"）
- **home.html**: 在线版为英文（"Stop reinventing the wheel"），本地源文件为中文
- **agent-guide.html**: 纯中文
- **index.html / market.html / memory-detail.html**: 纯中文

**建议**: 明确目标用户语言。如果主要面向中文 Agent 开发者，统一为中文；如果面向国际，做完整 i18n。目前的中英混杂会给用户困惑。

### 6. 页面间数据展示方式差异大
同一个"星尘系统"在三个页面有三种呈现：
- **intro.html**: 纯文本段落，英文
- **agent-guide.html**: emoji 列表 + 简要说明
- **index.html**: 横向激励栏 + 按钮

**建议**: 设计统一的"星尘系统"组件，在各页面复用。

### 7. 无搜索结果空状态引导
`index.html` 的搜索过滤功能完善（分类、平台、关键词），但当无结果时只显示 "🌊 暂无匹配的知识"，没有引导用户如何调整搜索或贡献新知识的提示。

**建议**: 空状态增加引导，例如："暂无匹配知识，试试其他关键词？或 [成为首个贡献者]"

---

## 🟢 次要问题 (P2)

### 8. 缺少 favicon
所有页面均未引入 favicon，浏览器标签页显示默认图标。

**建议**: 添加 `/static/favicon.ico` 或 SVG favicon。

### 9. 无外部 CSS/JS 文件
所有样式和脚本全部内联在 HTML 中，每个页面 ~3-5KB 的重复 CSS。虽然对小项目可接受，但不利于维护和缓存。

**建议**: 抽取公共样式为 `/static/css/common.css`，导航栏组件化。

### 10. agent-guide.html MCP 工具列表表格语义缺失
工具列表用 `div` + `span` 模拟表格（`TOOL search_memories 搜索知识`），可读性差且无语义。

**建议**: 使用 `<table>` 或 `<dl>` 标签，或至少用 grid 布局对齐。

### 11. home.html 统计数据硬编码 fallback
```javascript
catch (e) {
    document.getElementById('memories').textContent = '470';
    document.getElementById('categories').textContent = '43';
    ...
}
```
API 失败时显示硬编码的过时数据，用户可能误以为是真实数据。

**建议**: 显示 "数据加载失败" 或灰色占位符，不要用可能过时的假数据。

### 12. robots meta 不一致
| 页面 | robots 设置 |
|------|------------|
| home.html | `noindex, nofollow, noarchive` |
| intro.html | `noindex, nofollow` |
| agent-guide.html | `noindex, nofollow` |
| index.html | `noindex, nofollow, noarchive` |
| market.html | `noindex, nofollow, noarchive` |
| memory-detail.html | `noindex, nofollow, noarchive` |

**建议**: 统一设置。如果是公开内容希望被搜索引擎索引，应该移除 noindex；如果只想对 Agent 开放，保持 noindex 但统一格式。

### 13. 无 loading skeleton / 骨架屏
所有数据驱动区域（统计数据、知识列表、分类标签、Agent 列表）在加载时只显示纯文字"加载中..."，体验粗糙。

**建议**: 实现 CSS 骨架屏（skeleton screens），与页面风格一致的蓝色脉冲动画占位。

---

## ✅ 做得好的地方

1. **暗色主题统一方向正确** — 深蓝背景 + 蓝紫渐变的配色方案专业且有科技感
2. **响应式设计到位** — 所有页面都有 `@media` 断点处理，移动端体验有考虑
3. **home.html 的 canvas 粒子动画** — 视觉吸引力强，品牌辨识度高
4. **index.html 的筛选功能** — 分类 + 平台 + 关键词 + 热门/全部 tab，交互完善
5. **知识卡片信息密度恰当** — 标题、作者、分类、评分、可执行度、汲取次数，一目了然
6. **agent-guide.html 的端点展示** — 用 method badge (GET/POST) + 路径 + 描述的格式清晰易读
7. **HTML 转义** — 所有动态内容都使用 `esc()` 函数防 XSS，安全意识好
8. **intro.html 的问题/方案对比** — 红绿对比的 grid 布局，信息传达高效

---

## 📋 改进建议优先级排序

### 🔴 立即修复
1. **统一星尘数值** — 确认真实数据，全站同步（30分钟）
2. **修正 MCP 工具数量** — intro.html 改为 11（5分钟）
3. **修复硬编码 fallback 数据** — home.html 移除假数据（10分钟）

### 🟡 本周完成
4. **统一导航栏组件** — 所有页面使用相同的 header + nav-links（2小时）
5. **升级 agent-guide.html 视觉** — 加 Inter 字体、统一样式（1-2小时）
6. **统一语言** — 确定中/英，全站一致（视范围）
7. **添加搜索空状态引导**（30分钟）

### 🟢 下个迭代
8. **抽取公共 CSS** 为外部文件
9. **添加 favicon**
10. **实现骨架屏加载态**
11. **统一 robots meta**
12. **Agent-guide 工具列表语义化**

---

## 📊 页面评分

| 页面 | 结构 | 视觉 | 导航 | 一致性 | 综合 |
|------|------|------|------|--------|------|
| home.html | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | **B+** |
| intro.html | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | **B** |
| index.html | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **A-** |
| market.html | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **A-** |
| agent-guide.html | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | **B** |
| memory-detail.html | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **A-** |

**综合评价**: 功能完整性好，信息架构清晰，主要问题集中在**跨页面一致性**和**数据准确性**上。修复 P0 问题后可达到 A 级水平。
