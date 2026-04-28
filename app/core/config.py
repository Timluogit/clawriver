"""应用配置（简化版）- 从 100+ 项减少到 20 项"""
import os
from typing import Optional

class Settings:
    # 应用
    APP_NAME: str = "ClawRiver"
    APP_VERSION: str = "2.0.1"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # 数据库
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/clawriver.db")
    
    # CORS
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else []
    ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()]
    
    # 搜索
    SEARCH_RESULTS_LIMIT: int = 20
    SEARCH_SCORE_WEIGHT_RELEVANCE: float = 0.40
    SEARCH_SCORE_WEIGHT_QUALITY: float = 0.25
    SEARCH_SCORE_WEIGHT_POPULARITY: float = 0.20
    SEARCH_SCORE_WEIGHT_RECENCY: float = 0.15
    
    # 积分
    INITIAL_CREDITS: int = 1000
    SELLER_SHARE_RATE: float = 1.0  # 卖家获得100%（平台不收费）
    PLATFORM_FEE_RATE: float = 0.0  # 平台佣金0%
    
    # 限流
    RATE_LIMIT_ANONYMOUS: int = 30    # 匿名每分钟 30 次
    RATE_LIMIT_AUTHENTICATED: int = 100  # 已认证每分钟 100 次
    
    # Embedding（可选）
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # JWT（向后兼容，非必需）
    JWT_SECRET: Optional[str] = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

settings = Settings()
