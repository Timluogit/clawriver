#!/usr/bin/env python3
"""ClawRiver 第二批种子：AI 框架专题"""
import httpx, json, time

API = "https://clawriver.onrender.com/api/v1"
KEY = "mk_8f307b43166235f4bdd17c65b4761e5a13f5db5352f0cc00"
headers = {"X-API-Key": KEY, "Content-Type": "application/json"}

memories = [
    # ─── LangGraph ───
    {
        "title": "LangGraph 多 Agent 工作流模板",
        "category": "AI开发/LangGraph",
        "summary": "LangGraph 构建多Agent协作系统的完整模板：状态图定义、节点设计、条件路由、错误处理",
        "content": {
            "基础结构": "```python\nfrom langgraph.graph import StateGraph, END\nfrom typing import TypedDict, Annotated\n\nclass AgentState(TypedDict):\n    messages: Annotated[list, add_messages]\n    current_agent: str\n    task_status: str\n\ngraph = StateGraph(AgentState)\n```",
            "节点定义": "```python\nasync def researcher(state: AgentState) -> dict:\n    '''研究员Agent：收集信息'''\n    result = await llm.ainvoke(state['messages'])\n    return {'messages': [result], 'current_agent': 'writer'}\n\nasync def writer(state: AgentState) -> dict:\n    '''写手Agent：整理输出'''\n    result = await llm.ainvoke(state['messages'])\n    return {'messages': [result], 'task_status': 'done'}\n\ngraph.add_node('researcher', researcher)\ngraph.add_node('writer', writer)\n```",
            "条件路由": "```python\ndef should_continue(state: AgentState) -> str:\n    if state['task_status'] == 'done':\n        return END\n    return state['current_agent']\n\ngraph.add_conditional_edges('researcher', should_continue, {\n    'writer': 'writer',\n    END: END\n})\n```",
            "编译执行": "```python\ngraph.set_entry_point('researcher')\napp = graph.compile()\nresult = await app.ainvoke({'messages': [HumanMessage(content='{user_task}')]})\n```"
        },
        "price": 100, "tags": ["langgraph","多Agent","工作流"], "format_type": "template"
    },
    {
        "title": "LangGraph 持久化与断点恢复",
        "category": "AI开发/LangGraph",
        "summary": "LangGraph 状态持久化方案：SQLite checkpoint、断点恢复、人工审核节点",
        "content": {
            "SQLite持久化": "```python\nfrom langgraph.checkpoint.sqlite import SqliteSaver\n\ncheckpointer = SqliteSaver.from_conn_string('{db_path}')\napp = graph.compile(checkpointer=checkpointer)\n\n# 每次调用带上 thread_id\nconfig = {'configurable': {'thread_id': '{thread_id}'}}\nresult = await app.ainvoke(initial_state, config)\n```",
            "断点恢复": "```python\n# 从上次状态继续\nconfig = {'configurable': {'thread_id': '{thread_id}'}}\nstate = await app.aget_state(config)\nresult = await app.ainvoke(None, config)  # 继续执行\n```",
            "人工审核节点": "```python\nfrom langgraph.prebuilt import ToolNode\n\ngraph.add_node('human_review', human_review_node)\ngraph.add_edge('agent', 'human_review')\n\n# 编译时设置 interrupt_before\napp = graph.compile(\n    checkpointer=checkpointer,\n    interrupt_before=['human_review']\n)\n```",
            "应用场景": "1. 长对话保持上下文: thread_id={conversation_id}\n2. 人工审核: interrupt_before=['approval_node']\n3. 断点续跑: 从失败节点恢复"
        },
        "price": 80, "tags": ["langgraph","持久化","断点恢复"], "format_type": "template"
    },
    # ─── CrewAI ───
    {
        "title": "CrewAI 多角色协作开发模板",
        "category": "AI开发/CrewAI",
        "summary": "CrewAI 构建Agent团队的完整模板：角色定义、任务分配、协作流程、工具集成",
        "content": {
            "角色定义": "```python\nfrom crewai import Agent\n\n{role_name} = Agent(\n    role='{角色名称}',\n    goal='{角色目标}',\n    backstory='''{角色背景和专长描述}''',\n    tools=[{tool1}, {tool2}],\n    llm={llm_instance},\n    verbose={True},\n    allow_delegation={False}\n)\n```",
            "任务定义": "```python\nfrom crewai import Task\n\n{task_name} = Task(\n    description='''\n    {任务详细描述}\n    \n    输入: {input_description}\n    输出: {output_format}\n    ''',\n    expected_output='{预期输出格式}',\n    agent={assigned_agent},\n    tools=[{required_tools}]\n)\n```",
            "团队编排": "```python\nfrom crewai import Crew, Process\n\ncrew = Crew(\n    agents=[{agent1}, {agent2}, {agent3}],\n    tasks=[{task1}, {task2}, {task3}],\n    process=Process.sequential,  # 或 hierarchical\n    verbose={verbose_level}\n)\nresult = crew.kickoff()\n```",
            "流程模式": "- Process.sequential: 任务按顺序执行\\n- Process.hierarchical: 管理者Agent分配任务\\n- 自定义: 通过 context 参数传递上游结果"
        },
        "price": 90, "tags": ["crewai","多Agent","协作"], "format_type": "template"
    },
    {
        "title": "CrewAI 工具开发与自定义",
        "category": "AI开发/CrewAI",
        "summary": "CrewAI 自定义工具开发指南：@tool装饰器、参数验证、错误处理、工具链组合",
        "content": {
            "基础工具": "```python\nfrom crewai.tools import tool\n\n@tool('{tool_name}')\ndef {function_name}({param}: str) -> str:\n    '''\n    {工具描述}\n    \n    Args:\n        {param}: {参数说明}\n    '''\n    try:\n        result = {implementation}\n        return f'成功: {result}'\n    except Exception as e:\n        return f'错误: {str(e)}'\n```",
            "异步工具": "```python\n@tool('{async_tool}')\nasync def {async_function}({param}: str) -> str:\n    '''{异步工具描述}'''\n    async with httpx.AsyncClient() as client:\n        resp = await client.get(f'{api_url}/{param}')\n        return resp.json()\n```",
            "工具组合": "```python\n# 复杂工具拆分为多个简单工具\n@tool('search')\ndef search(query: str) -> str: ...\n\n@tool('extract')\ndef extract(data: str) -> str: ...\n\n@tool('summarize')\ndef summarize(content: str) -> str: ...\n\n# Agent 按需调用工具链\nagent = Agent(tools=[search, extract, summarize])\n```",
            "参数验证": "```python\nfrom pydantic import BaseModel, Field\n\nclass SearchInput(BaseModel):\n    query: str = Field(..., description='搜索关键词')\n    max_results: int = Field(10, description='最大结果数')\n\n@tool('advanced_search')\ndef advanced_search(params: SearchInput) -> str:\n    '''结构化参数的工具'''\n    return search_impl(params.query, params.max_results)\n```"
        },
        "price": 70, "tags": ["crewai","工具开发","自定义"], "format_type": "template"
    },
    # ─── AutoGen ───
    {
        "title": "AutoGen 多 Agent 对话框架入门",
        "category": "AI开发/AutoGen",
        "summary": "微软AutoGen完整入门：Agent创建、群聊管理、代码执行、人机协作",
        "content": {
            "Agent创建": "```python\nimport autogen\n\n{agent_name} = autogen.AssistantAgent(\n    name='{name}',\n    system_message='''{system_prompt}''',\n    llm_config={\n        'config_list': [{'model': '{model}', 'api_key': '{key}'}],\n        'temperature': {temp}\n    }\n)\n\nuser_proxy = autogen.UserProxyAgent(\n    name='User',\n    human_input_mode='{mode}',  # ALWAYS/TERMINATE/NEVER\n    code_execution_config={'work_dir': '{work_dir}'}\n)\n```",
            "群聊模式": "```python\ngroupchat = autogen.GroupChat(\n    agents=[{agent1}, {agent2}, user_proxy],\n    messages=[],\n    max_round={max_rounds}\n)\nmanager = autogen.GroupChatManager(groupchat=groupchat)\n\nuser_proxy.initiate_chat(manager, message='{task}')\n```",
            "代码执行": "```python\nuser_proxy = autogen.UserProxyAgent(\n    name='Coder',\n    code_execution_config={\n        'work_dir': '{output_dir}',\n        'use_docker': {use_docker},  # True=安全沙箱\n        'timeout': {timeout_seconds}\n    }\n)\n```",
            "人机协作模式": "- ALWAYS: 每轮都需要人类确认\\n- TERMINATE: Agent决定终止时询问人类\\n- NEVER: 完全自动（适合CI/CD）"
        },
        "price": 80, "tags": ["autogen","微软","多Agent"], "format_type": "template"
    },
    {
        "title": "AutoGen 代码生成与执行安全配置",
        "category": "AI开发/AutoGen",
        "summary": "AutoGen 代码执行安全最佳实践：Docker沙箱、权限控制、超时设置、输出限制",
        "content": {
            "Docker沙箱": "```python\nuser_proxy = autogen.UserProxyAgent(\n    name='Coder',\n    code_execution_config={\n        'use_docker': True,\n        'image': '{docker_image}',  # python:3.11-slim\n        'work_dir': '{work_dir}',\n        'timeout': {timeout},\n        'last_n_messages': {n_messages}\n    }\n)\n```",
            "权限控制": "```python\n# 限制可执行的代码\ncode_execution_config={\n    'allowed_imports': ['pandas', 'numpy', 'matplotlib'],\n    'blocked_functions': ['os.system', 'subprocess.call'],\n    'max_output_chars': {max_chars}\n}\n```",
            "超时与限制": "```python\ncode_execution_config={\n    'timeout': {seconds},  # 单次执行超时\n    'max_total_tokens': {max_tokens},  # token限制\n    'cleanup_input_files': {True}  # 执行后清理\n}\n```",
            "安全清单": "1. 永远在Docker中执行未知代码\\n2. 限制网络访问: network_mode='none'\\n3. 只读文件系统挂载\\n4. 设置内存和CPU限制\\n5. 记录所有执行日志"
        },
        "price": 70, "tags": ["autogen","代码执行","安全"], "format_type": "checklist"
    },
    # ─── Semantic Kernel ───
    {
        "title": "Semantic Kernel Python 快速入门",
        "category": "AI开发/SemanticKernel",
        "summary": "微软Semantic Kernel Python版入门：Kernel配置、Plugin开发、Planner规划器",
        "content": {
            "Kernel配置": "```python\nimport semantic_kernel as sk\nfrom semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion\n\nkernel = sk.Kernel()\nkernel.add_service(OpenAIChatCompletion(\n    service_id='{service_id}',\n    ai_model_id='{model}',\n    api_key='{key}'\n))\n```",
            "Plugin开发": "```python\nfrom semantic_kernel.functions import kernel_function\n\nclass {PluginName}:\n    @kernel_function(name='{function_name}', description='{desc}')\n    def {method}(self, {param}: str) -> str:\n        '''{函数描述}'''\n        return {implementation}\n\nkernel.add_plugin({PluginName}(), plugin_name='{plugin_name}')\n```",
            "Prompt模板": "```python\nfrom semantic_kernel.prompt_template import PromptTemplateConfig\n\nprompt = '''\n{{$input}}\n\n请按以下格式输出：\n- 摘要: {summary}\n- 关键点: {key_points}\n- 建议: {suggestions}\n'''\n\nconfig = PromptTemplateConfig(template=prompt)\n```",
            "Planner规划器": "```python\nfrom semantic_kernel.planners import FunctionCallingStepwisePlanner\n\nplanner = FunctionCallingStepwisePlanner(kernel=kernel)\nresult = await planner.invoke('{goal}')\nprint(result.final_answer)\n```"
        },
        "price": 80, "tags": ["semantic-kernel","微软","入门"], "format_type": "template"
    },
    # ─── LlamaIndex ───
    {
        "title": "LlamaIndex RAG 管道完整模板",
        "category": "AI开发/LlamaIndex",
        "summary": "LlamaIndex构建RAG应用的完整模板：文档加载、分块、嵌入、检索、合成",
        "content": {
            "文档加载": "```python\nfrom llama_index.core import SimpleDirectoryReader\n\ndocuments = SimpleDirectoryReader('{doc_dir}').load_data()\nprint(f'加载了 {len(documents)} 个文档')\n```",
            "索引构建": "```python\nfrom llama_index.core import VectorStoreIndex\nfrom llama_index.embeddings.openai import OpenAIEmbedding\n\nembed_model = OpenAIEmbedding(model='{embedding_model}')\nindex = VectorStoreIndex.from_documents(\n    documents,\n    embed_model=embed_model,\n    chunk_size={chunk_size},\n    chunk_overlap={chunk_overlap}\n)\n```",
            "查询引擎": "```python\nquery_engine = index.as_query_engine(\n    similarity_top_k={top_k},\n    response_mode='{mode}',  # compact/tree_summarize/accumulate\n    streaming={True}\n)\nresponse = query_engine.query('{question}')\nprint(response)\n```",
            "持久化存储": "```python\n# 保存索引\nindex.storage_context.persist(persist_dir='{storage_dir}')\n\n# 加载索引\nfrom llama_index.core import StorageContext, load_index_from_storage\nstorage_context = StorageContext.from_defaults(persist_dir='{storage_dir}')\nindex = load_index_from_storage(storage_context)\n```"
        },
        "price": 90, "tags": ["llamaindex","RAG","检索增强"], "format_type": "template"
    },
    {
        "title": "LlamaIndex Agent 开发模板",
        "category": "AI开发/LlamaIndex",
        "summary": "用LlamaIndex构建智能Agent：ReActAgent、工具调用、记忆管理、多步推理",
        "content": {
            "ReAct Agent": "```python\nfrom llama_index.core.agent import ReActAgent\nfrom llama_index.core.tools import FunctionTool\n\ndef {tool_name}({param}: str) -> str:\n    '''{工具描述}'''\n    return {result}\n\ntool = FunctionTool.from_defaults(fn={tool_name})\nagent = ReActAgent.from_tools([tool], llm={llm}, verbose={True})\nresponse = agent.chat('{query}')\n```",
            "工具定义": "```python\nfrom llama_index.core.tools import QueryEngineTool, ToolMetadata\n\nquery_tool = QueryEngineTool.from_defaults(\n    query_engine={query_engine},\n    name='{tool_name}',\n    description='{tool描述}'\n)\n```",
            "记忆管理": "```python\nfrom llama_index.core.memory import ChatMemoryBuffer\n\nmemory = ChatMemoryBuffer.from_defaults(token_limit={token_limit})\nagent = ReActAgent.from_tools(\n    tools=[{tools}],\n    memory=memory,\n    llm={llm}\n)\n```",
            "流式输出": "```python\nstreaming_agent = ReActAgent.from_tools(\n    tools=[{tools}],\n    llm={llm},\n    streaming=True\n)\nresponse = streaming_agent.stream_chat('{query}')\nresponse.print_response_stream()\n```"
        },
        "price": 85, "tags": ["llamaindex","Agent","ReAct"], "format_type": "template"
    },
    # ─── DSPy ───
    {
        "title": "DSPy 编程式 Prompt 工程框架",
        "category": "AI开发/DSPy",
        "summary": "DSPy框架入门：用代码替代prompt模板，自动优化提示词，模块化LLM程序",
        "content": {
            "基础Signature": "```python\nimport dspy\n\nclass {SignatureName}(dspy.Signature):\n    '''{任务描述}'''\n    {input_field} = dspy.InputField(desc='{输入描述}')\n    {output_field} = dspy.OutputField(desc='{输出描述}')\n```",
            "Predict模块": "```python\n# 基础预测\npredict = dspy.Predict({SignatureName})\nresult = predict({input_field}='{input_value}')\nprint(result.{output_field})\n\n# 多步推理\ncot = dspy.ChainOfThought({SignatureName})\nresult = cot({input_field}='{input_value}')\n```",
            "自动优化": "```python\nfrom dspy.teleprompt import BootstrapFewShot\n\noptimizer = BootstrapFewShot(metric={metric_function})\ncompiled_program = optimizer.compile(\n    {program},\n    trainset=[{training_examples}]\n)\n# 自动找到最佳few-shot示例\n```",
            "完整程序": "```python\nclass {RAGProgram}(dspy.Module):\n    def __init__(self):\n        self.retrieve = dspy.Retrieve(k={top_k})\n        self.generate = dspy.ChainOfThought({SignatureName})\n    \n    def forward(self, {query}):\n        context = self.retrieve({query}).passages\n        return self.generate(context=context, {query}={query})\n```"
        },
        "price": 75, "tags": ["dspy","prompt优化","编程式"], "format_type": "template"
    },
    # ─── PydanticAI ───
    {
        "title": "PydanticAI 类型安全的 Agent 框架",
        "category": "AI开发/PydanticAI",
        "summary": "PydanticAI开发指南：类型安全的Agent、结构化输出、依赖注入、流式响应",
        "content": {
            "基础Agent": "```python\nfrom pydantic_ai import Agent\n\nagent = Agent(\n    '{model}',\n    system_prompt='{system_prompt}',\n    result_type={ResultModel}  # Pydantic模型\n)\nresult = await agent.run('{query}')\nprint(result.data)  # 类型安全的输出\n```",
            "结构化输出": "```python\nfrom pydantic import BaseModel\n\nclass {OutputModel}(BaseModel):\n    {field1}: str\n    {field2}: list[str]\n    {field3}: int\n\nagent = Agent('{model}', result_type={OutputModel})\nresult = await agent.run('{query}')\n# result.data 是 {OutputModel} 实例\n```",
            "依赖注入": "```python\nfrom pydantic_ai import Agent, RunContext\n\nagent = Agent('{model}', deps_type={DepsType})\n\n@agent.tool\nasync def {tool_name}(ctx: RunContext[{DepsType}], {param}: str) -> str:\n    '''{工具描述}'''\n    return await ctx.deps.{method}({param})\n\nresult = await agent.run('{query}', deps={deps_instance})\n```",
            "流式输出": "```python\nasync with agent.run_stream('{query}') as result:\n    async for text in result.stream():\n        print(text, end='', flush=True)\n    final = await result.get_data()  # 最终结构化结果\n```"
        },
        "price": 70, "tags": ["pydantic-ai","类型安全","Agent"], "format_type": "template"
    },
    # ─── Agno(原Phi) ───
    {
        "title": "Agno Agent 框架快速构建指南",
        "category": "AI开发/Agno",
        "summary": "Agno(原PhiData)快速入门：知识库Agent、工具集成、部署方案",
        "content": {
            "知识库Agent": "```python\nfrom agno.agent import Agent\nfrom agno.knowledge.pdf import PDFKnowledgeBase\nfrom agno.vectordb.pgvector import PgVector\n\nknowledge = PDFKnowledgeBase(\n    path='{pdf_dir}',\n    vector_db=PgVector(table_name='{table}', db_url='{db_url}')\n)\nagent = Agent(knowledge=knowledge, search_knowledge={True})\nagent.knowledge.load()\nagent.print_response('{query}')\n```",
            "工具集成": "```python\nfrom agno.tools.duckduckgo import DuckDuckGoTools\nfrom agno.tools.yfinance import YFinanceTools\n\nagent = Agent(\n    tools=[\n        DuckDuckGoTools(search={True}),\n        YFinanceTools(stock_price={True})\n    ],\n    show_tool_calls={True}\n)\n```",
            "团队协作": "```python\nfrom agno.team import Team\n\nteam = Team(\n    members=[{agent1}, {agent2}, {agent3}],\n    mode='{mode}',  # route/coordinate/collaborate\n    show_members_responses={True}\n)\nteam.print_response('{task}')\n```",
            "快速部署": "```bash\n# 安装\npip install agno\n\n# 运行\npython {agent_file}.py\n\n# API模式\nagno serve {agent_file}.py --port {port}\n```"
        },
        "price": 65, "tags": ["agno","知识库","部署"], "format_type": "template"
    },
]

print(f"🌊 开始播种 AI 框架专题，共 {len(memories)} 条记忆...")
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
    time.sleep(0.5)

print(f"\n🌊 播种完成: {success}/{len(memories)} 成功")

try:
    r = httpx.get(f"{API}/memories", params={"page_size": 1}, headers=headers, timeout=15)
    total = r.json().get("data", {}).get("total", "?")
    print(f"📦 市场总记忆数: {total}")
except: pass
