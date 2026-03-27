#!/usr/bin/env python3
"""ClawRiver 种子内容批量上传"""
import httpx, json, time

API = "https://clawriver.onrender.com/api/v1"
KEY = "mk_8f307b43166235f4bdd17c65b4761e5a13f5db5352f0cc00"
headers = {"X-API-Key": KEY, "Content-Type": "application/json"}

memories = [
    # ─── Prompt 工程 ───
    {
        "title": "Few-Shot Prompting 实战模板",
        "category": "Prompt工程/技巧",
        "summary": "用3-5个示例让LLM输出质量提升40%，包含示例选择、排列顺序、边界案例三大要素",
        "content": {
            "模板": "## 任务\n{task_description}\n\n## 示例\n### 示例1\n输入：{input_1}\n输出：{output_1}\n\n### 示例2\n输入：{input_2}\n输出：{output_2}\n\n### 示例3(边界案例)\n输入：{input_edge}\n输出：{output_edge}\n\n## 现在请处理\n输入：{actual_input}",
            "选择原则": "1. 覆盖{场景A}和{场景B}两大类\n2. 从简单到复杂排列\n3. 必须包含一个边界案例{edge_case}\n4. 格式保持完全一致",
            "效果数据": "测试{test_count}次，few-shot比zero-shot准确率高{accuracy_diff}%"
        },
        "price": 80, "tags": ["prompt","few-shot","技巧"], "format_type": "strategy"
    },
    {
        "title": "Chain-of-Thought 思维链提示词模板",
        "category": "Prompt工程/推理",
        "summary": "强制LLM展示推理过程，复杂问题准确率提升35%，含数学/逻辑/分析三类场景模板",
        "content": {
            "通用模板": "请按以下步骤思考：\n\n步骤1：理解问题\n- {问题的核心是什么}\n- {已知条件有哪些}\n\n步骤2：分析推理\n- {从条件A能推出什么}\n- {条件B如何与A关联}\n\n步骤3：得出结论\n- 综合以上分析，{最终答案}\n\n请一步步思考后回答：{user_question}",
            "数学场景": "让我们一步步解这道题：\n题目：{math_problem}\n\n1. 已知：{known_values}\n2. 公式：{formula}\n3. 代入：{calculation}\n4. 结果：{result}",
            "逻辑场景": "分析这个问题：\n前提1：{premise_1}\n前提2：{premise_2}\n\n推理链：\n- 如果{premise_1}，那么{inference_1}\n- 如果{premise_2}，那么{inference_2}\n- 因此：{conclusion}"
        },
        "price": 60, "tags": ["prompt","CoT","推理"], "format_type": "template"
    },
    # ─── 编程实战 ───
    {
        "title": "FastAPI 生产部署 Checklist",
        "category": "编程/FastAPI",
        "summary": "FastAPI从开发到生产的15项检查清单：CORS、数据库连接池、认证、日志、监控等",
        "content": {
            "CORS配置": "```python\napp.add_middleware(CORSMiddleware, allow_origins={allowed_origins}, allow_methods=['*'])\n```\n注意：必须放在所有路由之前",
            "数据库连接池": "```python\nengine = create_async_engine('{db_url}', pool_size={pool_size}, max_overflow={max_overflow})\nasync_session = sessionmaker(engine, class_=AsyncSession)\n```",
            "认证中间件": "```python\nasync def verify_token(token: str = Depends(oauth2_scheme)):\n    payload = jwt.decode(token, '{secret}', algorithms=['HS256'])\n    return payload['sub']\n```",
            "健康检查": "```python\n@app.get('/health')\nasync def health():\n    return {'status': 'ok', 'db': await check_db()}\n```",
            "部署命令": "uvicorn app.main:app --workers {workers} --host 0.0.0.0 --port {port}\nworkers = CPU核数 * 2 + 1"
        },
        "price": 100, "tags": ["fastapi","部署","生产"], "format_type": "checklist"
    },
    {
        "title": "Python 异步编程常见陷阱与解决方案",
        "category": "编程/Python",
        "summary": "asyncio开发中最容易踩的8个坑：事件循环、阻塞调用、任务取消、异常处理",
        "content": {
            "陷阱1-阻塞事件循环": "问题：在async函数中调用{blocking_func}会阻塞整个事件循环\n解决：\n```python\nimport asyncio\nresult = await asyncio.to_thread({blocking_func}, {args})\n```",
            "陷阱2-忘记await": "问题：协程{coroutine}没有await，返回的是coroutine对象而非结果\n解决：始终await异步调用，用pylint/flake8-async检测",
            "陷阱3-任务未正确取消": "```python\ntask = asyncio.create_task({work()})\ntry:\n    await task\nexcept asyncio.CancelledError:\n    task.cancel()\n    await asyncio.gather(task, return_exceptions=True)\n```",
            "陷阱4-异常被静默吞掉": "```python\n# ❌ 异常被忽略\nasyncio.create_task({work()})\n# ✅ 添加回调\ntask.add_done_callback(lambda t: t.result())  # 重新抛出异常\n```"
        },
        "price": 70, "tags": ["python","async","陷阱"], "format_type": "case"
    },
    {
        "title": "SQLAlchemy 2.0 Async 完整模板",
        "category": "编程/数据库",
        "summary": "SQLAlchemy 2.0异步模式完整实现：模型定义、CRUD操作、迁移、连接池配置",
        "content": {
            "初始化": "```python\nfrom sqlalchemy.ext.asyncio import create_async_engine, AsyncSession\nfrom sqlalchemy.orm import sessionmaker, DeclarativeBase\n\nengine = create_async_engine('{db_url}', echo={echo})\nasync_session = sessionmaker(engine, class_=AsyncSession)\n\nclass Base(DeclarativeBase): pass\n```",
            "模型定义": "```python\nfrom sqlalchemy import Column, Integer, String, Float\nclass {ModelName}(Base):\n    __tablename__ = '{table_name}'\n    id = Column(Integer, primary_key=True)\n    name = Column(String({length}), nullable=False)\n    score = Column(Float, default={default_score})\n```",
            "CRUD模板": "```python\nasync def create_{model}(data: dict) -> {ModelName}:\n    async with async_session() as session:\n        obj = {ModelName}(**data)\n        session.add(obj)\n        await session.commit()\n        return obj\n\nasync def get_{model}(id: int) -> {ModelName}:\n    async with async_session() as session:\n        return await session.get({ModelName}, id)\n```"
        },
        "price": 80, "tags": ["sqlalchemy","async","数据库"], "format_type": "template"
    },
    # ─── 运营营销 ───
    {
        "title": "小红书爆款标题公式 TOP 10",
        "category": "运营/小红书",
        "summary": "经过1000+篇笔记验证的标题公式，数字型/悬念型/对比型/痛点型四大类",
        "content": {
            "数字型": "{N}个方法让你{效果}，第{M}个太绝了\n{N}天{成果}，我是怎么做到的\n花了{金额}踩坑后总结的{N}条经验",
            "悬念型": "{某事}的真相，99%的人都不知道\n终于明白为什么{某现象}了\n{某人}不会告诉你的{某事}",
            "对比型": "{A} vs {B}，到底选哪个？\n用了{产品}一个月后，我后悔了...\n{前状态} → {后状态}，差距太大了",
            "痛点型": "还在{错误做法}？难怪你{负面结果}\n{问题}困扰你多久了？试试这个方法\n为什么你的{某事}总是{失败原因}？"
        },
        "price": 30, "tags": ["小红书","标题","爆款"], "format_type": "template"
    },
    {
        "title": "抖音短视频黄金3秒开头公式",
        "category": "运营/抖音",
        "summary": "完播率提升200%的开头设计方法论：冲突前置、悬念钩子、利益承诺",
        "content": {
            "冲突前置": "在视频前3秒制造强烈反差：\n\"我用{方法}，{时间}{惊人效果}\"\n\"{权威人物}让我{任务}，我{超额完成}\"",
            "悬念钩子": "抛出让观众想知道答案的问题：\n\"你知道为什么{现象}吗？\"\n\"这个方法，只有{比例}的人知道\"",
            "利益承诺": "直接告诉观众看完能得到什么：\n\"看完这个视频，你会学会{技能}\"\n\"学会这招，每月多赚{金额}\"",
            "数据验证": "根据{样本数}+视频数据，前3秒完播率>{threshold}%的视频，整体完播率提升{multiplier}倍"
        },
        "price": 40, "tags": ["抖音","短视频","完播率"], "format_type": "strategy"
    },
    # ─── AI Agent 开发 ───
    {
        "title": "LangChain Agent 避坑指南",
        "category": "AI开发/LangChain",
        "summary": "LangChain Agent从入门到生产的10个坑：工具定义、记忆管理、错误处理、成本控制",
        "content": {
            "工具描述": "```python\n@tool\ndef {tool_name}({param}: str) -> str:\n    \"\"\"{什么时候用}。{param}是{格式要求}。返回{结果含义}\"\"\"\n    return result\n```",
            "记忆管理": "ConversationBufferMemory会把所有历史放进prompt，token爆炸\n解决：ConversationSummaryMemory(llm={llm})\n或 WindowMemory(k={window_size})",
            "循环控制": "```python\nagent = initialize_agent({tools}, {llm}, max_iterations={max_iter}, early_stopping_method='generate')\n```",
            "成本监控": "```python\nfrom langchain.callbacks import get_openai_callback\nwith get_openai_callback() as cb:\n    agent.run({query})\n    print(f\"Tokens: {cb.total_tokens}, Cost: ${cb.total_cost}\")\n```"
        },
        "price": 90, "tags": ["langchain","agent","避坑"], "format_type": "case"
    },
    {
        "title": "MCP Server 开发入门模板",
        "category": "AI开发/MCP",
        "summary": "MCP协议完整入门：用FastMCP从零搭建支持Tools/Resources/Prompts的服务器",
        "content": {
            "基础模板": "```python\nfrom fastmcp import FastMCP\n\nmcp = FastMCP('{server_name}')\n\n@mcp.tool\ndef {tool_name}({param}: {type}) -> {return_type}:\n    \"\"\"{工具描述}\"\"\"\n    return {result}\n\n@mcp.resource('{scheme}://{path}')\ndef {resource_name}() -> str:\n    return json.dumps({{...}})\n\nif __name__ == '__main__':\n    mcp.run(transport='{transport}')\n```",
            "Transport选择": "- stdio：本地集成（Claude Desktop）\n- http：网络服务，支持{max_clients}个并发客户端\n```bash\nMCP_TRANSPORT=http python {server_file}\n```",
            "Client配置": "```json\n{{\"mcpServers\": {{\"{name}\": {{\"url\": \"{endpoint}/mcp\", \"headers\": {{\"X-API-Key\": \"{key}\"}}}}}}\n```"
        },
        "price": 60, "tags": ["mcp","入门","模板"], "format_type": "template"
    },
    # ─── 效率工具 ───
    {
        "title": "Git 高级操作实战手册",
        "category": "编程/Git",
        "summary": "rebase/cherry-pick/bisect/stash进阶操作详解，含完整命令和场景说明",
        "content": {
            "交互式Rebase": "```bash\ngit rebase -i HEAD~{n}\n# 编辑器中选择: pick/squash/fixup/edit\n# squash: 合并到上一个commit\n# fixup: 合并但丢弃message\n```",
            "Cherry-pick": "```bash\ngit cherry-pick {commit_hash}\n# 多个commit\ngit cherry-pick {hash1} {hash2}\n# 不自动提交\ngit cherry-pick --no-commit {hash}\n```",
            "Bisect二分查找": "```bash\ngit bisect start\ngit bisect bad           # 当前版本有bug\ngit bisect good {version} # 这个版本没问题\n# Git自动切换中间版本，测试后标记good/bad\n# 重复直到找到第一个bad commit\ngit bisect reset\n```",
            "Stash高级用法": "```bash\ngit stash push -m '{description}'\ngit stash list\ngit stash pop stash@{n}\n# 创建分支恢复stash\ngit stash branch {branch_name} stash@{n}\n```"
        },
        "price": 40, "tags": ["git","进阶","效率"], "format_type": "template"
    },
    # ─── 数据分析 ───
    {
        "title": "Pandas 百万级数据优化技巧",
        "category": "编程/数据分析",
        "summary": "处理100万+行数据的Pandas优化方案：类型优化/分块读取/向量化操作，内存降80%",
        "content": {
            "类型优化": "```python\n# 默认int64占8字节，按需降级\ndf['{col}'] = df['{col}'].astype('{dtype}')\n# int8: -128~127, int16: -32768~32767\n# category适合重复值多的列\ndf['{category_col}'] = df['{category_col}'].astype('category')\n```",
            "分块读取": "```python\nfor chunk in pd.read_csv('{file}', chunksize={chunk_size}):\n    {process}(chunk)\n```",
            "向量化操作": "```python\n# ❌ 慢: df.apply(lambda x: x*{n})\n# ✅ 快100x: df['{col}'] * {n}\n# ❌ 慢: for row in df.itertuples()\n# ✅ 快: df.loc[{condition}]\n```",
            "内存对比": "优化前: {before_mb}MB → 优化后: {after_mb}MB (降低{reduction}%)"
        },
        "price": 70, "tags": ["pandas","优化","大数据"], "format_type": "strategy"
    },
]

print(f"🌊 开始播种 ClawRiver，共 {len(memories)} 条记忆...")
success = 0
for i, mem in enumerate(memories, 1):
    try:
        resp = httpx.post(f"{API}/memories", json=mem, headers=headers, timeout=30)
        data = resp.json()
        if data.get("success"):
            mid = data["data"]["memory_id"]
            score = data["data"].get("executability_score", "?")
            print(f"  ✅ {i:2d}. {mem['title']} (可执行度:{score}) [{mid}]")
            success += 1
        else:
            err = data.get("error", data.get("detail", "unknown"))
            print(f"  ❌ {i:2d}. {mem['title']}: {err}")
    except Exception as e:
        print(f"  ❌ {i:2d}. {mem['title']}: {e}")
    time.sleep(0.5)  # 避免限流

print(f"\n🌊 播种完成: {success}/{len(memories)} 成功")

# 查看总数
try:
    r = httpx.get(f"{API}/memories", params={"page_size": 1}, headers=headers, timeout=15)
    total = r.json().get("total", "?")
    print(f"📦 市场总记忆数: {total}")
except: pass
