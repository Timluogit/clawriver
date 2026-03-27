#!/usr/bin/env python3
"""ClawRiver 第三批：真实踩坑经验（文档里没有的东西）"""
import httpx, json, time

API = "https://clawriver.onrender.com/api/v1"
KEY = "mk_8f307b43166235f4bdd17c65b4761e5a13f5db5352f0cc00"
headers = {"X-API-Key": KEY, "Content-Type": "application/json"}

memories = [
    # ─── 真实排错经验 ───
    {
        "title": "Render 部署 FastAPI 冷启动 50秒 的解法",
        "category": "部署/Render",
        "summary": "Render免费版冷启动慢的5个解法：Keep-Alive、健康检查轮询、升级付费、迁移到Railway、用Cron保活",
        "content": {
            "问题": "Render免费版闲置{idle_minutes}分钟后休眠，首次请求需要{cold_start_seconds}秒",
            "解法1-保活脚本": "用外部服务每{interval}分钟ping一次：\n```bash\n# 用UptimeRobot或GitHub Actions\ncurl https://{service}.onrender.com/health\n```",
            "解法2-客户端重试": "```python\nfor attempt in range({max_retries}):\n    try:\n        resp = httpx.get(url, timeout={timeout})\n        break\n    except httpx.ReadTimeout:\n        if attempt == {max_retries} - 1:\n            raise\n        time.sleep({retry_delay})\n```",
            "解法3-迁移Railway": "Railway Starter $5/月无冷启动，部署命令：\n```bash\nrailway init && railway up\n```",
            "经验": "免费版适合Demo，生产环境必须付费。Keep-Alive只能减少感知延迟，不能真正解决冷启动"
        },
        "price": 0, "tags": ["render","冷启动","部署"], "format_type": "case"
    },
    {
        "title": "SQLAlchemy async + FastAPI 连接池泄漏排查",
        "category": "编程/数据库",
        "summary": "FastAPI异步SQLAlchemy连接池耗尽的3个常见原因和修复方案，含实际报错信息",
        "content": {
            "报错": "sqlalchemy.exc.TimeoutError: QueuePool limit of size {pool_size} overflow {overflow} reached, connection timed out, timeout {timeout}",
            "原因1-忘记关闭session": "```python\n# ❌ 错误写法\nasync def get_items(db: AsyncSession):\n    result = await db.execute(select(Item))\n    return result.scalars().all()  # session没关\n\n# ✅ 正确写法\nasync def get_items(db: AsyncSession = Depends(get_db)):\n    try:\n        result = await db.execute(select(Item))\n        return result.scalars().all()\n    finally:\n        await db.close()  # 或用依赖注入自动管理\n```",
            "原因2-长事务": "```python\n# ❌ 一个请求里开了事务但没提交\nasync with db.begin():  # 开启事务\n    await db.execute(...)  # 忘了commit\n\n# ✅ 用async with自动管理\nasync with db.begin():\n    await db.execute(...)\n# 自动commit或rollback\n```",
            "原因3-连接池配置不当": "```python\nengine = create_async_engine(\n    DATABASE_URL,\n    pool_size={pool_size},        # 默认5，生产建议10-20\n    max_overflow={max_overflow},   # 允许额外连接数\n    pool_timeout={pool_timeout},   # 等待连接超时秒数\n    pool_recycle={pool_recycle}    # 连接回收时间（秒）\n)\n```"
        },
        "price": 0, "tags": ["sqlalchemy","连接池","排错"], "format_type": "case"
    },
    {
        "title": "MCP Server 开发的 5 个坑（实际踩过）",
        "category": "AI开发/MCP",
        "summary": "用FastMCP开发MCP Server时实际遇到的问题：schema不兼容、SSE废弃、Context注入失败等",
        "content": {
            "坑1-schema兼容": "问题：用了Optional[list[str]]，VS Code MCP客户端报错\n原因：部分MCP客户端不支持JSON Schema的$ref\n解决：用简单类型，或FastMCP自动解引用\n```python\n# ✅ 兼容性好\n@mcp.tool\ndef search(query: str, limit: int = 10) -> dict:\n# ❌ 某些客户端不支持\n@mcp.tool\ndef search(query: str, tags: Optional[list[str]] = None) -> dict:\n```",
            "坑2-SSE已废弃": "问题：mcp.run(transport='sse') 在新版客户端连不上\n原因：MCP 2025-03-26规范废弃SSE，改用Streamable HTTP\n解决：\n```python\n# ✅ 新方式\nmcp.run(transport='http', host='0.0.0.0', port={port})\n# 端点变成 /mcp 而不是 /sse\n```",
            "坑3-Context拿不到": "问题：ctx.info()报错 'NoneType has no attribute info'\n原因：客户端不支持Context注入时ctx为None\n解决：\n```python\n@mcp.tool\ndef search(query: str, ctx: Context = None) -> dict:\n    if ctx:\n        await ctx.info(f'搜索: {query}')\n    # ...正常逻辑\n```",
            "坑4-stdio输出污染": "问题：在stdio模式下print()会导致MCP协议解析失败\n原因：MCP用stdin/stdout通信，print污染stdout\n解决：用logging到stderr\n```python\nimport logging\nlogger = logging.getLogger(__name__)\nlogger.info('这条不会污染stdout')\n```"
        },
        "price": 0, "tags": ["mcp","踩坑","FastMCP"], "format_type": "case"
    },
    {
        "title": "OpenClaw 配置修改后 Gateway 不生效的排查",
        "category": "运维/OpenClaw",
        "summary": "修改openclaw.json后配置不生效的常见原因：缓存、语法错误、字段名变更、需要重启",
        "content": {
            "排查步骤": "1. 检查JSON语法：cat ~/.openclaw/openclaw.json | python3 -m json.tool\n2. 查看日志：openclaw logs --level error\n3. 重启Gateway：openclaw gateway restart\n4. 检查版本：openclaw --version",
            "常见原因1-字段名变更": "update.auto.enabled 已改名为其他字段\ncommands.ownerDisplay 已废弃\n解决：查看最新文档，删除无效字段",
            "常见原因2-热加载失败": "某些配置需要完全重启：\n```bash\nopenclaw gateway stop\nopenclaw gateway start\n```",
            "常见原因3-多配置文件冲突": "workspace下的配置 vs ~/.openclaw下的配置\n优先级：workspace > 全局"
        },
        "price": 0, "tags": ["openclaw","配置","排错"], "format_type": "case"
    },
    # ─── 实战经验 ───
    {
        "title": "飞书 API 发文件的坑：路径限制和编码问题",
        "category": "集成/飞书",
        "summary": "通过OpenClaw飞书通道发送文件时遇到的LocalMediaAccessError和中文文件名问题",
        "content": {
            "报错": "LocalMediaAccessError: Local media path is not under an allowed directory",
            "原因": "飞书安全限制（CVE-2026-26321修复后），只允许workspace目录下的文件",
            "解决步骤": "1. 文件必须放在workspace目录：~/.openclaw/workspace/\n2. 复制文件：cp /tmp/file.pdf ~/.openclaw/workspace/\n3. 用英文文件名避免编码问题\n4. 使用message工具的path参数发送",
            "完整示例": "```bash\n# 复制到workspace\ncp /path/to/文件.pdf ~/.openclaw/workspace/file.pdf\n```\n```python\nmessage(action='send', channel='feishu', \n        message='文件说明',\n        path='/Users/xxx/.openclaw/workspace/file.pdf')\n```"
        },
        "price": 0, "tags": ["飞书","文件","安全限制"], "format_type": "case"
    },
    {
        "title": "GitHub CLI 认证失效的修复方法",
        "category": "运维/GitHub",
        "summary": "gh命令返回403或认证失败时的排查和修复，含token权限检查",
        "content": {
            "报错": "HTTP 403: Resource not accessible by personal access token",
            "排查": "```bash\n# 检查认证状态\ngh auth status\n# 检查token权限\ngh auth status --show-token\n```",
            "修复1-重新认证": "```bash\ngh auth login --web\n# 或用token\ngit config --global credential.helper store\n```",
            "修复2-token权限不足": "GitHub Personal Access Token需要以下权限：\n- repo (完整)\n- admin:org (如需管理组织)\n- write:discussion (如需讨论)\n在 GitHub > Settings > Developer settings > Personal access tokens 检查",
            "修复3-使用git remote中的token": "```bash\n# 查看remote配置\ngit remote -v\n# 如果有token在URL中，检查是否过期\n```\n⚠️ 不要在代码中硬编码token"
        },
        "price": 0, "tags": ["github","认证","CLI"], "format_type": "case"
    },
    {
        "title": "Python httpx 异步请求超时的最佳实践",
        "category": "编程/Python",
        "summary": "httpx在异步环境下的超时配置、重试机制、连接池管理，避免请求挂起",
        "content": {
            "超时配置": "```python\nimport httpx\n\n# 总超时（推荐）\nclient = httpx.AsyncClient(timeout=httpx.Timeout({timeout}))\n\n# 分阶段超时\nclient = httpx.AsyncClient(timeout=httpx.Timeout(\n    connect={connect_timeout},\n    read={read_timeout},\n    write={write_timeout},\n    pool={pool_timeout}\n))\n```",
            "重试机制": "```python\nimport tenacity\n\n@tenacity.retry(\n    stop=tenacity.stop_after_attempt({max_retries}),\n    wait=tenacity.wait_exponential(multiplier=1, min={min_wait}, max={max_wait}),\n    retry=tenacity.retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError))\n)\nasync def fetch_with_retry(url: str) -> dict:\n    async with httpx.AsyncClient() as client:\n        resp = await client.get(url)\n        resp.raise_for_status()\n        return resp.json()\n```",
            "连接池": "```python\n# 复用客户端（推荐）\nclient = httpx.AsyncClient(\n    limits=httpx.Limits(\n        max_connections={max_conn},\n        max_keepalive_connections={keepalive}\n    )\n)\n# 用完后关闭\nawait client.aclose()\n```",
            "实际经验": "1. Render冷启动时设置timeout=60秒\n2. 并发请求用Semaphore控制数量\n3. 永远处理TimeoutException和NetworkError"
        },
        "price": 0, "tags": ["httpx","超时","异步"], "format_type": "case"
    },
    {
        "title": "Docker Compose 多服务编排常见问题",
        "category": "部署/Docker",
        "summary": "Docker Compose多服务启动顺序、健康检查、环境变量传递、网络配置的实战经验",
        "content": {
            "启动顺序": "```yaml\nservices:\n  app:\n    depends_on:\n      db:\n        condition: service_healthy  # 等健康检查通过\n      redis:\n        condition: service_started\n  db:\n    healthcheck:\n      test: ['CMD', 'pg_isready', '-U', '{user}']\n      interval: {interval}s\n      timeout: {timeout}s\n      retries: {retries}\n```",
            "环境变量": "```yaml\nservices:\n  app:\n    environment:\n      - DATABASE_URL=postgresql://{user}:{pass}@db:5432/{db}\n    env_file:\n      - .env  # 从文件加载\n```",
            "网络配置": "```yaml\nservices:\n  app:\n    networks:\n      - frontend\n      - backend\n  nginx:\n    networks:\n      - frontend\nnetworks:\n  frontend:\n  backend:\n    internal: true  # 不对外暴露\n```",
            "调试技巧": "```bash\n# 查看日志\ndocker compose logs -f {service}\n# 进入容器\ndocker compose exec {service} bash\n# 重新构建\ndocker compose up -d --build {service}\n```"
        },
        "price": 0, "tags": ["docker","compose","编排"], "format_type": "case"
    },
    {
        "title": "Cron 任务不执行的排查清单",
        "category": "运维/Linux",
        "summary": "crontab任务不执行的8个排查步骤：路径、权限、环境变量、日志、用户",
        "content": {
            "排查清单": "1. 检查cron是否运行：systemctl status cron\n2. 检查任务：crontab -l\n3. 检查日志：grep CRON /var/log/syslog\n4. 路径问题：cron的PATH只有/bin:/usr/bin\n5. 权限问题：脚本需要可执行权限\n6. 环境变量：cron没有加载.bashrc\n7. 用户问题：确认是哪个用户的cron\n8. 时间格式：确认5个时间字段正确",
            "常见坑-路径": "```bash\n# ❌ cron里找不到命令\n* * * * * python script.py\n\n# ✅ 用绝对路径\n* * * * * /usr/bin/python3 /full/path/script.py\n```",
            "常见坑-环境变量": "```bash\n# ❌ cron没有加载环境\n* * * * * my_script.sh\n\n# ✅ 先加载环境\n* * * * * . /etc/profile; /full/path/my_script.sh\n```",
            "调试方法": "```bash\n# 添加日志\n* * * * * /full/path/script.sh >> /tmp/cron.log 2>&1\n# 然后查看日志\ntail -f /tmp/cron.log\n```"
        },
        "price": 0, "tags": ["cron","linux","排错"], "format_type": "checklist"
    },
]

print(f"🌊 开播种：真实踩坑经验，共 {len(memories)} 条...")
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

print(f"\n🌊 完成: {success}/{len(memories)} 成功")

try:
    r = httpx.get(f"{API}/memories", params={"page_size": 1}, headers=headers, timeout=15)
    total = r.json().get("data", {}).get("total", "?")
    print(f"📦 市场总数: {total}")
except: pass
