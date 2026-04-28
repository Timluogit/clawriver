"""数据库初始化"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# 根据数据库类型配置连接参数
_connect_args = {}
if "postgresql" in settings.DATABASE_URL:
    import ssl as _ssl
    _ctx = _ssl.create_default_context()
    _ctx.check_hostname = False
    _ctx.verify_mode = _ssl.CERT_NONE
    _connect_args = {
        "statement_cache_size": 0,
        "ssl": _ctx,
    }

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=_connect_args,
    pool_pre_ping=True,  # 自动检测断开的连接
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    """依赖注入：获取数据库会话"""
    async with async_session() as session:
        yield session

async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 添加 role 列（如果不存在）
        try:
            from sqlalchemy import text
            await conn.execute(text("ALTER TABLE agents ADD COLUMN role VARCHAR(20) DEFAULT 'user'"))
        except Exception:
            pass
    print("✅ 数据库初始化完成")
