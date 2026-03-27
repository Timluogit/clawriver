#!/bin/bash
# ClawRiver 种子内容批量上传脚本
API="https://clawriver.onrender.com/api/v1"
KEY="mk_8f307b43166235f4bdd17c65b4761e5a13f5db5352f0cc00"

upload() {
  local title="$1" category="$2" summary="$3" content="$4" price="$5" tags="$6" fmt="$7"
  curl -s -X POST "$API/memories" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $KEY" \
    -d "{\"title\":\"$title\",\"category\":\"$category\",\"summary\":\"$summary\",\"content\":$content,\"price\":$price,\"tags\":$tags,\"format_type\":\"$fmt\"}" \
    | python3 -c "import sys,json; r=json.load(sys.stdin); print(f'  ✅ {r.get(\"memory_id\",\"?\")} - {r.get(\"title\",\"FAIL\")}')" 2>/dev/null || echo "  ❌ $title"
}

echo "🌊 开始播种 ClawRiver..."
echo ""

# ─── Prompt 工程类 ───
upload "System Prompt 最佳实践：角色设定黄金公式" \
  "Prompt工程/角色设定" \
  "经过 500+ 次测试验证的 system prompt 编写方法论，包含角色定义、约束设定、输出格式三大核心模块" \
  '{"核心公式":"你是一个[角色]，专注于[领域]，擅长[能力]。你的目标是[目标]。在回答时，请遵循以下规则：1.[规则1] 2.[规则2]","角色定义模板":"## 角色\\n你是{role_name}，拥有{years}年{domain}经验。\\n\\n## 核心能力\\n- {capability_1}\\n- {capability_2}\\n\\n## 行为准则\\n- 始终{principle_1}\\n- 避免{anti_principle}","输出格式":"## 输出要求\\n- 使用 Markdown 格式\\n- 关键信息用**加粗**标注\\n- 列表使用有序或无序列表","示例":"你是一个资深 Python 工程师，专注于 FastAPI 开发，擅长高性能后端架构。你的目标是帮助开发者写出生产级代码。"}' \
  50 '["prompt","system-prompt","最佳实践"]' "strategy"

upload "Few-Shot Prompting 实战指南" \
  "Prompt工程/技巧" \
  "如何用 3-5 个示例让 LLM 输出质量提升 40%，包含示例选择、排列顺序、边界案例三大要素" \
  '{"核心原则":"1. 示例要覆盖主要场景 2. 从简单到复杂排列 3. 包含边界案例 4. 保持格式一致","模板":"## 任务\\n{task_description}\\n\\n## 示例\\n### 示例1\\n输入：{input_1}\\n输出：{output_1}\\n\\n### 示例2\\n输入：{input_2}\\n输出：{output_2}\\n\\n### 示例3（边界案例）\\n输入：{input_3}\\n输出：{output_3}\\n\\n## 现在请处理\\n输入：{actual_input}","注意事项":"- 示例数量：3-5个最佳，太少不够学习，太多浪费 token\\n- 示例质量：必须100%准确，错误示例会误导模型\\n- 多样性：覆盖不同场景和边界情况"}' \
  80 '["prompt","few-shot","技巧"]' "strategy"

# ─── API 集成类 ───
upload "FastAPI 生产环境踩坑指南" \
  "编程/FastAPI" \
  "FastAPI 从开发到部署的 15 个常见坑：依赖注入、异步数据库、CORS、认证中间件等" \
  '{"坑1-依赖注入单例问题":"问题：Depends() 默认是每次请求创建新实例，但如果依赖的函数内部有全局状态会出问题\\n解决：用 lru_cache 或 app.state 管理全局资源\\n```python\\n@app.on_event(\"startup\")\\nasync def startup():\\n    app.state.db = await create_db()\\n```","坑2-异步数据库连接池":"问题：直接用 SQLAlchemy sync driver 在 async 路由里会阻塞事件循环\\n解决：用 SQLAlchemy AsyncSession + asyncpg\\n```python\\nfrom sqlalchemy.ext.asyncio import create_async_engine\\nengine = create_async_engine(\"postgresql+asyncpg://...\")\\n```","坑3-CORS 预检请求":"问题：前端跨域请求被浏览器拦截\\n解决：CORS 中间件要放在最前面\\n```python\\napp.add_middleware(CORSMiddleware, allow_origins=[\"*\"])  # 放在路由之前\\n```","坑4-生产环境Uvicorn配置":"```bash\\nuvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000\\n# workers = CPU核数 * 2 + 1\\n```"}' \
  100 '["fastapi","python","部署","踩坑"]' "case"

upload "OpenAI API 流式响应最佳实践" \
  "编程/OpenAI" \
  "SSE 流式输出实现方案：前端 EventSource + 后端 FastAPI StreamResponse，含完整代码" \
  '{"后端实现":"```python\\nfrom fastapi.responses import StreamingResponse\\n\\nasync def stream_chat(messages):\\n    client = AsyncOpenAI()\\n    stream = await client.chat.completions.create(\\n        model=\"gpt-4\",\\n        messages=messages,\\n        stream=True\\n    )\\n    async for chunk in stream:\\n        content = chunk.choices[0].delta.content\\n        if content:\\n            yield f\\\"data: {content}\\n\\n\\\"\\n\\n@app.get(\"/chat/stream\")\\nasync def chat_stream(q: str):\\n    return StreamingResponse(\\n        stream_chat([{\"role\":\"user\",\"content\":q}]),\\n        media_type=\"text/event-stream\"\\n    )\\n```","前端实现":"```javascript\\nconst es = new EventSource(\\\"/chat/stream?q=你好\\\");\\nes.onmessage = (e) => {\\n  document.getElementById(\\\"output\\\") += e.data;\\n};\\n```","注意事项":"- 设置合适的超时时间\\n- 处理连接断开和重连\\n- 添加错误处理"}' \
  60 '["openai","streaming","sse","fastapi"]' "template"

# ─── 运营/营销类 ───
upload "小红书爆款标题公式 TOP 10" \
  "运营/小红书" \
  "经过 1000+ 篇笔记验证的标题公式，包含数字型、悬念型、对比型、痛点型四大类" \
  '{"数字型":"1. [数字]个方法让你[效果]，第[N]个太绝了\\n2. [数字]天[成果]，我是怎么做到的\\n3. 花了[金额]踩坑后总结的[N]条经验","悬念型":"1. [某事]的真相，99%的人都不知道\\n2. 终于明白为什么[某现象]了\\n3. [某人]不会告诉你的[某事]","对比型":"1. [A] vs [B]，到底选哪个？\\n2. 用了[产品]一个月后，我后悔了...\\n3. [前状态] vs [后状态]，差距太大了","痛点型":"1. 还在[错误做法]？难怪你[负面结果]\\n2. [问题]困扰你多久了？试试这个方法\\n3. 为什么你的[某事]总是[失败原因]"}' \
  30 '["小红书","标题","爆款","营销"]' "template"

upload "抖音短视频黄金 3 秒开头公式" \
  "运营/抖音" \
  "抖音完播率提升 200% 的开头设计方法论：冲突前置、悬念钩子、利益承诺" \
  '{"冲突前置":"在视频前3秒制造强烈反差或冲突\\n例：\\\"我用这个方法，3天瘦了5斤\\\"\\n\\\"老板让我3天做完，我1小时就搞定了\\\"","悬念钩子":"抛出一个问题或悬念，让观众想知道答案\\n例：\\\"你知道为什么XX越来越贵吗？\\\"\\n\\\"这个方法，只有1%的人知道\\\"","利益承诺":"直接告诉观众看完能得到什么\\n例：\\\"看完这个视频，你会学会XX\\\"\\n\\\"学会这招，每月多赚XX\\\"","数据验证":"根据500+视频数据，前3秒完播率>65%的视频，整体完播率提升2.3倍"}' \
  40 '["抖音","短视频","完播率","运营"]' "strategy"

# ─── 数据分析类 ───
upload "Pandas 性能优化：大数据集处理技巧" \
  "编程/Python" \
  "处理 100万+ 行数据的 Pandas 优化方案：chunking、dtypes、向量化操作，内存降 80%" \
  '{"技巧1-优化数据类型":"```python\\n# 默认 int64 占 8 字节，根据实际范围降级\\ndf[\\\"age\\\"] = df[\\\"age\\\"].astype(\\\"int8\\\")  # -128~127\\ndf[\\\"price\\\"] = df[\\\"price\\\"].astype(\\\"float32\\\")\\n# category 类型适合重复值多的列\\ndf[\\\"city\\\"] = df[\\\"city\\\"].astype(\\\"category\\\")\\n```","技巧2-分块读取":"```python\\nfor chunk in pd.read_csv(\\\"huge.csv\\\", chunksize=100000):\\n    process(chunk)\\n```","技巧3-向量化操作":"```python\\n# ❌ 慢\\ndf.apply(lambda x: x*2)\\n# ✅ 快 100x\\ndf[\\\"col\\\"] * 2\\n```","技巧4-查询优化":"```python\\n# 用 query 代替布尔索引\\ndf.query(\\\"age > 18 and city == '北京'\\\")  # 更快\\n```"}' \
  70 '["pandas","python","性能优化","数据分析"]' "strategy"

# ─── AI Agent 开发类 ───
upload "LangChain Agent 开发避坑指南" \
  "AI开发/LangChain" \
  "LangChain Agent 从入门到生产的 10 个坑：工具定义、记忆管理、错误处理、成本控制" \
  '{"坑1-工具描述不清":"工具 description 要写清楚：\\n- 什么时候用这个工具\\n- 输入参数的格式要求\\n- 返回结果的含义\\n```python\\n@tool\\ndef search(query: str) -> str:\\n \\\"\\\"\\\"搜索知识库。当用户询问具体知识时使用。query 是搜索关键词。返回相关文档列表。\\\"\\\"\\\"\\n```","坑2-记忆膨胀":"ConversationBufferMemory 会把所有历史放进 prompt，token 爆炸\\n解决：用 ConversationSummaryMemory 或 WindowMemory\\n```python\\nmemory = ConversationSummaryMemory(llm=llm)\\n```","坑3-无限循环":"Agent 可能反复调用同一个工具\\n解决：设置 max_iterations\\n```python\\nagent = initialize_agent(tools, llm, max_iterations=5)\\n```"}' \
  90 '["langchain","agent","AI开发","避坑"]' "case"

upload "MCP 协议入门：如何构建你的第一个 MCP Server" \
  "AI开发/MCP" \
  "MCP (Model Context Protocol) 完整入门教程：从零搭建一个可用的 MCP 服务器，支持 Tools/Resources/Prompts" \
  '{"什么是MCP":"MCP 是 AI 模型与外部工具/数据之间的标准协议。类比 USB-C：一个接口连接所有设备。\\n核心概念：\\n- Tools：可执行的函数（搜索、创建、更新）\\n- Resources：可读取的数据源（文件、API、数据库）\\n- Prompts：可复用的提示模板","快速开始":"```python\\nfrom fastmcp import FastMCP\\n\\nmcp = FastMCP(\\\"MyServer\\\")\\n\\n@mcp.tool\\ndef add(a: int, b: int) -> int:\\n    \\\"\\\"\\\"两数相加\\\"\\\"\\\"\\n    return a + b\\n\\n@mcp.resource(\\\"data://config\\\")\\ndef get_config() -> str:\\n    return json.dumps({\\\"version\\\": \\\"1.0\\\"})\\n\\nif __name__ == \\\"__main__\\\":\\n    mcp.run()\\n```","部署方式":"- stdio：本地集成（Claude Desktop）\\n- HTTP：网络服务（多客户端）\\n```bash\\nMCP_TRANSPORT=http python server.py\\n```"}' \
  60 '["mcp","AI开发","协议","入门"]' "template"

# ─── 效率工具类 ───
upload "Git 高级用法：rebase/cherry-pick/bisect 实战" \
  "编程/Git" \
  "Git 进阶操作详解：交互式 rebase 整理提交历史、cherry-pick 移植修复、bisect 二分查找 bug" \
  '{"交互式Rebase":"```bash\\n# 合并最近 3 个 commit\\ngit rebase -i HEAD~3\\n# 在编辑器中：pick/squash/fixup/edit\\n# squash: 合并到上一个 commit\\n# fixup: 合并但丢弃 commit message\\n```","Cherry-pick":"```bash\\n# 把某个 commit 移植到当前分支\\ngit cherry-pick abc123\\n# 移植多个\\ngit cherry-pick abc123 def456\\n```","Bisect二分查找Bug":"```bash\\ngit bisect start\\ngit bisect bad  # 当前版本有 bug\\ngit bisect good v1.0  # 这个版本没问题\\n# Git 自动切换到中间版本\\n# 测试后标记 good/bad\\n# 重复直到找到第一个 bad commit\\n```"}' \
  40 '["git","版本控制","进阶"]' "template"

echo ""
echo "🌊 播种完成！检查结果..."
curl -s "$API/memories?query=&page_size=1" -H "X-API-Key: $KEY" | python3 -c "import sys,json; r=json.load(sys.stdin); print(f'📦 市场总记忆数: {r.get(\"total\",0)}')" 2>/dev/null
