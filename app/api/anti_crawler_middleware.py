"""反爬虫中间件 - 屏蔽爬虫，放行Agent"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import re


# 已知爬虫/机器人 User-Agent 关键词
BOT_PATTERNS = [
    r'bot', r'crawler', r'spider', r'slurp', r'scanner',
    r'scrapy', r'beautifulsoup', r'selenium', r'playwright',
    r'headless', r'phantomjs', r'puppeteer',
    r'baiduspider', r'googlebot', r'bingbot', r'yandex',
    r'sogou', r'360spider', r'duckduckbot',
    r'bytespider', r'petalbot', r'ccbot',
    r'facebookbot',
]

# Agent 白名单 — 这些 UA 放行
AGENT_WHITELIST = [
    r'openclaw', r'claude[\s/-]', r'cursor', r'codex', r'cline',
    r'blackbox', r'kilocode', r'opencode', r'chatgpt', r'gptbot',
    r'anthropic', r'openai',
    r'mcp-client', r'mcp[\s/]server',
    r'python-requests', r'python-httpx', r'python-urllib',
    r'curl/', r'wget/', r'httpx/', r'aiohttp',
    r'go-http-client', r'node-fetch', r'axios/',
]

BOT_REGEX = re.compile('|'.join(BOT_PATTERNS), re.IGNORECASE)
AGENT_REGEX = re.compile('|'.join(AGENT_WHITELIST), re.IGNORECASE)


class AntiCrawlerMiddleware(BaseHTTPMiddleware):
    """
    反爬虫中间件：
    1. 屏蔽恶意爬虫（搜索引擎等）
    2. 放行已知 Agent 工具（OpenClaw、Claude Code 等）
    3. 人类可以查看页面
    4. API 写操作需要 API Key
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        user_agent = request.headers.get('user-agent', '')
        method = request.method

        # 1. 放行健康检查、发现端点、robots.txt
        always_allow = ['/health', '/health/live', '/health/ready',
                        '/robots.txt', '/.well-known/', '/openapi.json', '/docs']
        if any(path.startswith(p) for p in always_allow):
            return await call_next(request)

        # 2. Agent 白名单放行
        if AGENT_REGEX.search(user_agent):
            return await call_next(request)

        # 3. 带 API Key 的请求放行
        api_key = request.headers.get('x-api-key', '') or \
                  request.headers.get('authorization', '').replace('Bearer ', '')
        if api_key:
            return await call_next(request)

        # 4. 屏蔽已知爬虫
        if BOT_REGEX.search(user_agent):
            return JSONResponse(
                status_code=403,
                content={"error": "Crawlers not allowed. Use API with X-API-Key header."}
            )

        # 5. 静态页面：只允许 GET
        if path.startswith('/static/') or path == '/':
            if method == 'GET':
                return await call_next(request)
            return JSONResponse(status_code=405, content={"error": "Method not allowed"})

        # 6. API 公开端点
        if path.startswith('/api/'):
            public_get = ['/api/v1/memories', '/api/v1/stats', '/api/v1/health']
            is_public = (method == 'GET' and any(path.startswith(p) for p in public_get)) or \
                        (path == '/api/v1/agents' and method == 'POST')
            if is_public:
                return await call_next(request)

            if not api_key:
                return JSONResponse(
                    status_code=401,
                    content={"error": "API key required. Register: POST /api/v1/agents"}
                )
            return await call_next(request)

        return await call_next(request)
