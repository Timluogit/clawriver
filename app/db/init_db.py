"""数据库初始化 - 使用SQL直接建表（避免SQLAlchemy超时）"""
from app.db.database import engine
from sqlalchemy import text

CORE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS agents (
    agent_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    api_key VARCHAR(100) UNIQUE NOT NULL,
    credits INTEGER DEFAULT 999999,
    total_earned INTEGER DEFAULT 0,
    total_spent INTEGER DEFAULT 0,
    reputation_score FLOAT DEFAULT 5.0,
    total_sales INTEGER DEFAULT 0,
    total_purchases INTEGER DEFAULT 0,
    memories_uploaded INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memories (
    memory_id VARCHAR(50) PRIMARY KEY,
    seller_agent_id VARCHAR(50) NOT NULL,
    team_id VARCHAR(50),
    team_access_level VARCHAR(20) DEFAULT 'private',
    created_by_agent_id VARCHAR(50),
    title VARCHAR(200) NOT NULL,
    category VARCHAR(200) NOT NULL,
    tags JSONB DEFAULT '[]'::jsonb,
    summary TEXT NOT NULL,
    content JSONB NOT NULL,
    format_type VARCHAR(50) DEFAULT 'template',
    price INTEGER NOT NULL,
    purchase_count INTEGER DEFAULT 0,
    favorite_count INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    score_count INTEGER DEFAULT 0,
    avg_score FLOAT DEFAULT 0.0,
    verification_data JSONB,
    verification_score FLOAT,
    executability_score INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP,
    expiry_time TIMESTAMP,
    ttl_days INTEGER,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mem_seller ON memories(seller_agent_id);
CREATE INDEX IF NOT EXISTS idx_mem_category ON memories(category);

CREATE TABLE IF NOT EXISTS purchases (
    purchase_id VARCHAR(50) PRIMARY KEY,
    buyer_agent_id VARCHAR(50) NOT NULL,
    seller_agent_id VARCHAR(50) NOT NULL,
    memory_id VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,
    seller_income INTEGER NOT NULL,
    platform_fee INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ratings (
    rating_id VARCHAR(50) PRIMARY KEY,
    memory_id VARCHAR(50) NOT NULL,
    buyer_agent_id VARCHAR(50) NOT NULL,
    score INTEGER NOT NULL,
    effectiveness INTEGER,
    comment TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS transactions (
    tx_id VARCHAR(50) PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL,
    tx_type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    related_id VARCHAR(50),
    description TEXT,
    commission INTEGER,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tx_agent ON transactions(agent_id);

CREATE TABLE IF NOT EXISTS verifications (
    verification_id VARCHAR(50) PRIMARY KEY,
    memory_id VARCHAR(50) NOT NULL,
    verifier_agent_id VARCHAR(50) NOT NULL,
    score INTEGER NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memory_versions (
    version_id VARCHAR(50) PRIMARY KEY,
    memory_id VARCHAR(50) NOT NULL,
    version_number INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    category VARCHAR(200) NOT NULL,
    tags JSONB,
    summary TEXT NOT NULL,
    content JSONB NOT NULL,
    format_type VARCHAR(50),
    price INTEGER NOT NULL,
    changelog TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform_stats (
    id SERIAL PRIMARY KEY,
    total_transactions INTEGER DEFAULT 0,
    total_revenue INTEGER DEFAULT 0,
    total_volume INTEGER DEFAULT 0,
    daily_transactions INTEGER DEFAULT 0,
    daily_revenue INTEGER DEFAULT 0,
    daily_volume INTEGER DEFAULT 0,
    date TIMESTAMP
);
"""

async def init_db():
    """初始化数据库 - 直接用SQL创建核心表"""
    async with engine.begin() as conn:
        # 只创建核心表，避免超时
        for stmt in CORE_TABLES_SQL.strip().split(';'):
            stmt = stmt.strip()
            if stmt:
                try:
                    await conn.execute(text(stmt))
                except Exception as e:
                    print(f"⚠️ SQL执行警告: {str(e)[:60]}")
    print("✅ 核心数据库表初始化完成")
