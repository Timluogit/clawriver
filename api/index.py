# Vercel Serverless Function for ClawRiver API
# 这个文件允许将 FastAPI 部署到 Vercel

from app.main import app

# Vercel 需要 ASGI 应用
handler = app
