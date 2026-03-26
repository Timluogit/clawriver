"""反爬虫中间件 - 屏蔽爬虫和恶意机器人"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import re


# 已知爬虫/机器人 User-Agent 关键词
BOT_PATTERNS = [
    r'bot', r'crawler', r'spider', r'slurp', r'scanner',
    r'python-requests', r'python-urllib', r'python-httpx',
    r'curl/', r'wget/', r'httpx/', r'aiohttp',
    r'scrapy', r'beautifulsoup', r'selenium', r'playwright',
    r'headless', r'phantomjs', r'puppeteer',
    r'go-http-client', r'java/', r'ruby/', r'perl/',
    r'apache-httpclient', r'okhttp', r'libwww-perl',
    r'guzzlehttp', r'axios/', r'node-fetch', r'got/',
    r'wechat', r'weibo', r'qq/',  # 社交爬虫
    r'baiduspider', r'googlebot', r'bingbot', r'yandex',
    r'sogou', r'360spider', r'duckduckbot',
    r'bytespider', r'petalbot', r'ccbot',
    r'claudebot', r'gptbot', r'chatgpt', r'openai',
    r'anthropic', r'google-extended', r'facebookbot',
]

BOT_REGEX = re.compile('|'.join(BOT_PATTERNS), re.IGNORECASE)

# 允许的 Agent API 路径前缀（Agent 通过 API Key 认证访问）
AGENT_API_PREFIXES = ['/api/v1/']

# 允许的浏览器访问路径（人类观看）
VIEWABLE_PATHS = [
    '/', '/static/', '/health', '/health/', '/docs', '/openapi.json',
    '/favicon.ico',
]


class AntiCrawlerMiddleware(BaseHTTPMiddleware):
    """
    反爬虫中间件：
    1. 屏蔽所有已知爬虫/机器人
    2. 人类只能观看（GET 请求可视化页面）
    3. Agent 通过 API Key 认证后可以使用 API
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        user_agent = request.headers.get('user-agent', '')
        method = request.method

        # 1. 放行健康检查和 robots.txt
        if path in ['/health', '/health/live', '/health/ready', '/robots.txt']:
            return await call_next(request)

        # 2. 屏蔽已知爬虫（全部拒绝）
        if BOT_REGEX.search(user_agent):
            # 如果带了 API Key，可能是 Agent，放行 API
            api_key = request.headers.get('x-api-key', '') or \
                      request.headers.get('authorization', '').replace('Bearer ', '')
            if api_key and path.startswith('/api/'):
                return await call_next(request)
            # 否则拒绝
            return JSONResponse(
                status_code=403,
                content={"error": "Crawlers are not allowed"}
            )

        # 3. 静态页面：只允许 GET（人类只看）
        if path.startswith('/static/') or path == '/':
            if method == 'GET':
                return await call_next(request)
            return JSONResponse(
                status_code=405,
                content={"error": "Method not allowed. Humans can only view."}
            )

        # 4. API 路径：需要 API Key 认证
        if path.startswith('/api/'):
            # 检查是否有 API Key（从 header 获取）
            api_key = request.headers.get('x-api-key', '') or \
                      request.headers.get('authorization', '').replace('Bearer ', '')

            # 允许部分公开端点（不需要 key）
            public_endpoints = [
                '/api/v1/memories',      # GET 搜索/列表（公开浏览）
                '/api/v1/stats',         # GET 统计信息
                '/api/v1/agents',        # POST 注册
                '/api/v1/health',        # 健康检查
            ]
            is_public = any(
                path.startswith(ep) and method == 'GET'
                for ep in public_endpoints
            ) or (path == '/api/v1/agents' and method == 'POST')

            if is_public:
                return await call_next(request)

            # 其他 API 需要认证
            if not api_key:
                return JSONResponse(
                    status_code=401,
                    content={"error": "API key required. Agents must authenticate."}
                )

            return await call_next(request)

        # 5. 其他路径放行
        return await call_next(request)
