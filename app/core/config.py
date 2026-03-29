"""应用配置"""
import os
from typing import Optional

class Settings:
    # 应用
    APP_NAME: str = "ClawRiver"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # 数据库
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/clawriver.db")
    
    # CORS
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else []
    # Filter out empty strings
    ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()]
    
    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    
    # 积分系统
    MVP_FREE_MODE: bool = False  # 正式模式：积分交易
    INITIAL_CREDITS: int = 1000  # 初始星尘（Agent注册赠送）
    SELLER_SHARE_RATE: float = 1.0  # 卖家获得100%（平台不收费）
    PLATFORM_FEE_RATE: float = 0.0  # 平台佣金0%
    
    # 记忆
    MAX_MEMORY_SIZE: int = 50000  # 单条记忆最大字符数
    FREE_MEMORY_CATEGORIES: list = ["教程", "入门"]  # 免费分类
    
    # 外部服务（可选）
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY")

    # Qdrant 向量搜索
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")

    # Cross-Encoder 重排
    RERANK_ENABLED: bool = os.getenv("RERANK_ENABLED", "true").lower() == "true"
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-large")
    RERANK_TOP_K: int = int(os.getenv("RERANK_TOP_K", "20"))
    RERANK_THRESHOLD: float = float(os.getenv("RERANK_THRESHOLD", "0.5"))
    RERANK_CACHE_TTL: int = int(os.getenv("RERANK_CACHE_TTL", "3600"))  # 1小时
    RERANK_FORCE_CPU: bool = os.getenv("RERANK_FORCE_CPU", "false").lower() == "true"
    EMBEDDING_MODEL_DIR: str = os.getenv("EMBEDDING_MODEL_DIR", "./models")

    # 审计日志
    AUDIT_LOG_ENABLED: bool = os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true"
    AUDIT_LOG_RETENTION_DAYS: int = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))
    AUDIT_LOG_ARCHIVE_ENABLED: bool = os.getenv("AUDIT_LOG_ARCHIVE_ENABLED", "false").lower() == "true"
    AUDIT_LOG_ASYNC_WRITE: bool = os.getenv("AUDIT_LOG_ASYNC_WRITE", "true").lower() == "true"

    # 数字签名
    DIGITAL_SIGNATURE_ENABLED: bool = os.getenv("DIGITAL_SIGNATURE_ENABLED", "true").lower() == "true"
    DIGITAL_SIGNATURE_ALGORITHM: str = os.getenv("DIGITAL_SIGNATURE_ALGORITHM", "RSA-SHA256")
    DIGITAL_SIGNATURE_KEY_SIZE: int = int(os.getenv("DIGITAL_SIGNATURE_KEY_SIZE", "2048"))
    KEY_ENCRYPTION_SALT: str = os.getenv("KEY_ENCRYPTION_SALT", "")

    # 搜索缓存
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1小时
    CACHE_ON_MISS: bool = os.getenv("CACHE_ON_MISS", "true").lower() == "true"
    CACHE_DELAY_INVALIDATION: bool = os.getenv("CACHE_DELAY_INVALIDATION", "true").lower() == "true"
    CACHE_DELAY_SECONDS: int = int(os.getenv("CACHE_DELAY_SECONDS", "5"))
    CACHE_MAX_MEMORY: str = os.getenv("CACHE_MAX_MEMORY", "2gb")
    
    # 本地缓存配置（Redis 不可用时的后备）
    CACHE_LOCAL_MAX_SIZE: int = int(os.getenv("CACHE_LOCAL_MAX_SIZE", "2000"))
    CACHE_LOCAL_TTL: int = int(os.getenv("CACHE_LOCAL_TTL", "300"))  # 5分钟
    CACHE_SEARCH_TTL: int = int(os.getenv("CACHE_SEARCH_TTL", "1800"))  # 搜索缓存30分钟
    CACHE_MEMORY_DETAIL_TTL: int = int(os.getenv("CACHE_MEMORY_DETAIL_TTL", "600"))  # 详情缓存10分钟

    # 用户画像系统
    PROFILE_ENABLED: bool = os.getenv("PROFILE_ENABLED", "true").lower() == "true"
    PROFILE_AUTO_EXTRACTION: bool = os.getenv("PROFILE_AUTO_EXTRACTION", "true").lower() == "true"
    PROFILE_MIN_CONFIDENCE: float = float(os.getenv("PROFILE_MIN_CONFIDENCE", "0.6"))  # 自动提取最小置信度
    PROFILE_CACHE_TTL: int = int(os.getenv("PROFILE_CACHE_TTL", "300"))  # 5分钟缓存
    PROFILE_AUTO_FORGET_DAYS: int = int(os.getenv("PROFILE_AUTO_FORGET_DAYS", "30"))  # 自动遗忘天数
    PROFILE_EXTRACTION_MODEL: str = os.getenv("PROFILE_EXTRACTION_MODEL", "gpt-4o-mini")  # 画像提取模型
    PROFILE_MAX_FIELDS: int = int(os.getenv("PROFILE_MAX_FIELDS", "30"))  # 最大字段数

    # 自动遗忘机制
    AUTO_FORGET_ENABLED: bool = os.getenv("AUTO_FORGET_ENABLED", "true").lower() == "true"
    AUTO_FORGET_SCHEDULE_MINUTES: int = int(os.getenv("AUTO_FORGET_SCHEDULE_MINUTES", "60"))  # 检查间隔（分钟）
    AUTO_FORGET_BATCH_SIZE: int = int(os.getenv("AUTO_FORGET_BATCH_SIZE", "1000"))  # 批量清理大小
    AUTO_FORGET_DEFAULT_TTL_DAYS: int = int(os.getenv("AUTO_FORGET_DEFAULT_TTL_DAYS", "30"))  # 默认TTL（天）
    AUTO_FORGET_ARCHIVE_BEFORE_DELETE: bool = os.getenv("AUTO_FORGET_ARCHIVE_BEFORE_DELETE", "false").lower() == "true"  # 删除前归档

    # TTL配置（按事实类型）
    TTL_PERSONAL: int = int(os.getenv("TTL_PERSONAL", "365"))  # 个人信息TTL（天）
    TTL_PREFERENCE: int = int(os.getenv("TTL_PREFERENCE", "90"))  # 偏好TTL（天）
    TTL_HABIT: int = int(os.getenv("TTL_HABIT", "180"))  # 习惯TTL（天）
    TTL_SKILL: int = int(os.getenv("TTL_SKILL", "365"))  # 技能TTL（天）
    TTL_INTEREST: int = int(os.getenv("TTL_INTEREST", "180"))  # 兴趣TTL（天）

    # ===== 内存模式（纯内存运行架构） =====
    # 搜索引擎模式: "qdrant" | "in-memory" | "auto"
    #   qdrant: 使用 Qdrant 向量数据库（需要外部服务）
    #   in-memory: 纯内存搜索（无需外部数据库）
    #   auto: 优先 in-memory，Qdrant 可用时自动降级到 Qdrant
    SEARCH_ENGINE_MODE: str = os.getenv("SEARCH_ENGINE_MODE", "in-memory")

    # 内存索引
    MEMORY_INDEX_DIR: str = os.getenv("MEMORY_INDEX_DIR", "./data/memory_index")
    MEMORY_INDEX_MAX_VECTORS: int = int(os.getenv("MEMORY_INDEX_MAX_VECTORS", "100000"))
    MEMORY_INDEX_AUTO_PERSIST: bool = os.getenv("MEMORY_INDEX_AUTO_PERSIST", "true").lower() == "true"
    MEMORY_INDEX_PERSIST_INTERVAL: int = int(os.getenv("MEMORY_INDEX_PERSIST_INTERVAL", "300"))  # 秒

    # 内存向量搜索
    IN_MEMORY_SIMILARITY_METRIC: str = os.getenv("IN_MEMORY_SIMILARITY_METRIC", "cosine")  # cosine | euclidean
    IN_MEMORY_BATCH_SIZE: int = int(os.getenv("IN_MEMORY_BATCH_SIZE", "1000"))

    # 内存混合搜索
    IN_MEMORY_SEMANTIC_WEIGHT: float = float(os.getenv("IN_MEMORY_SEMANTIC_WEIGHT", "0.6"))
    IN_MEMORY_KEYWORD_WEIGHT: float = float(os.getenv("IN_MEMORY_KEYWORD_WEIGHT", "0.4"))
    IN_MEMORY_RERANK_ENABLED: bool = os.getenv("IN_MEMORY_RERANK_ENABLED", "true").lower() == "true"

    # ===== 智能重排（Smart Reranking） =====
    SMART_RERANK_ENABLED: bool = os.getenv("SMART_RERANK_ENABLED", "true").lower() == "true"
    SMART_RERANK_STRATEGY: str = os.getenv("SMART_RERANK_STRATEGY", "balanced")
    # 预设策略: balanced | semantic_heavy | keyword_heavy | freshness_first | quality_first | personalized
    SMART_RERANK_USE_CROSS_ENCODER: bool = os.getenv("SMART_RERANK_USE_CROSS_ENCODER", "true").lower() == "true"
    SMART_RERANK_CE_WEIGHT: float = float(os.getenv("SMART_RERANK_CE_WEIGHT", "0.70"))
    SMART_RERANK_DYNAMIC_WEIGHTS: bool = os.getenv("SMART_RERANK_DYNAMIC_WEIGHTS", "true").lower() == "true"
    SMART_RERANK_TOP_K: int = int(os.getenv("SMART_RERANK_TOP_K", "20"))
    SMART_RERANK_THRESHOLD: float = float(os.getenv("SMART_RERANK_THRESHOLD", "0.0"))
    SMART_RERANK_MIN_CANDIDATES: int = int(os.getenv("SMART_RERANK_MIN_CANDIDATES", "5"))
    SMART_RERANK_CACHE_ENABLED: bool = os.getenv("SMART_RERANK_CACHE_ENABLED", "true").lower() == "true"
    SMART_RERANK_CACHE_TTL: int = int(os.getenv("SMART_RERANK_CACHE_TTL", "3600"))

    # 特征权重（自定义模式下使用，覆盖策略预设）
    # 语义
    SMART_RERANK_W_SEMANTIC: float = float(os.getenv("SMART_RERANK_W_SEMANTIC", "0.30"))
    SMART_RERANK_W_EMBEDDING: float = float(os.getenv("SMART_RERANK_W_EMBEDDING", "0.10"))
    # 关键词
    SMART_RERANK_W_KW_EXACT: float = float(os.getenv("SMART_RERANK_W_KW_EXACT", "0.08"))
    SMART_RERANK_W_KW_BM25: float = float(os.getenv("SMART_RERANK_W_KW_BM25", "0.07"))
    SMART_RERANK_W_KW_TITLE: float = float(os.getenv("SMART_RERANK_W_KW_TITLE", "0.05"))
    SMART_RERANK_W_KW_TAG: float = float(os.getenv("SMART_RERANK_W_KW_TAG", "0.03"))
    # 时效性
    SMART_RERANK_W_RECENCY: float = float(os.getenv("SMART_RERANK_W_RECENCY", "0.06"))
    SMART_RERANK_W_FRESHNESS: float = float(os.getenv("SMART_RERANK_W_FRESHNESS", "0.04"))
    # 用户偏好
    SMART_RERANK_W_INTEREST: float = float(os.getenv("SMART_RERANK_W_INTEREST", "0.05"))
    SMART_RERANK_W_HISTORY: float = float(os.getenv("SMART_RERANK_W_HISTORY", "0.04"))
    SMART_RERANK_W_CATEGORY: float = float(os.getenv("SMART_RERANK_W_CATEGORY", "0.03"))
    # 质量
    SMART_RERANK_W_QUALITY: float = float(os.getenv("SMART_RERANK_W_QUALITY", "0.05"))
    SMART_RERANK_W_POPULARITY: float = float(os.getenv("SMART_RERANK_W_POPULARITY", "0.04"))
    SMART_RERANK_W_RATING: float = float(os.getenv("SMART_RERANK_W_RATING", "0.03"))
    SMART_RERANK_W_VERIFICATION: float = float(os.getenv("SMART_RERANK_W_VERIFICATION", "0.03"))

settings = Settings()
