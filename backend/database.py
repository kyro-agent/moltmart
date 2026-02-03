"""
Database layer for MoltMart
Uses SQLAlchemy with async support for PostgreSQL/SQLite
"""

import os
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, sessionmaker

# Database URL from environment (Railway provides this for PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./moltmart.db")

# Fix for Railway PostgreSQL URLs (they use postgres:// but SQLAlchemy needs postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


# ============ MODELS ============


class AgentDB(Base):
    """Agent stored in database"""

    __tablename__ = "agents"

    id = Column(String, primary_key=True)
    api_key = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    wallet_address = Column(String, nullable=False, index=True)
    description = Column(Text)
    moltx_handle = Column(String)
    github_handle = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    services_count = Column(Integer, default=0)

    # ERC-8004 fields
    has_8004 = Column(Boolean, default=False)
    agent_8004_id = Column(Integer)
    agent_8004_registry = Column(String)
    scan_url = Column(String)


class ServiceDB(Base):
    """Service stored in database"""

    __tablename__ = "services"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    endpoint_url = Column(String)
    price_usdc = Column(Float, nullable=False)
    category = Column(String, nullable=False, index=True)
    provider_name = Column(String, nullable=False)
    provider_wallet = Column(String, nullable=False, index=True)
    secret_token_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    calls_count = Column(Integer, default=0)
    revenue_usdc = Column(Float, default=0.0)


class TransactionDB(Base):
    """Transaction log"""

    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    service_id = Column(String, index=True)
    service_name = Column(String)
    buyer_wallet = Column(String, index=True)
    buyer_name = Column(String)
    seller_wallet = Column(String, index=True)
    price_usdc = Column(Float)
    status = Column(String)  # pending, completed, failed, timeout
    created_at = Column(DateTime, default=datetime.utcnow)
    seller_response_code = Column(Integer)
    error = Column(Text)


class FeedbackDB(Base):
    """Feedback/reputation"""

    __tablename__ = "feedback"

    id = Column(String, primary_key=True)
    service_id = Column(String, index=True)
    agent_id = Column(String, index=True)
    agent_name = Column(String)
    rating = Column(Integer)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============ DATABASE OPERATIONS ============


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_agent_by_api_key(api_key: str) -> AgentDB | None:
    """Get agent by API key"""
    async with async_session() as session:
        result = await session.execute(select(AgentDB).where(AgentDB.api_key == api_key))
        return result.scalar_one_or_none()


async def get_agent_by_wallet(wallet: str) -> AgentDB | None:
    """Get agent by wallet address"""
    async with async_session() as session:
        result = await session.execute(select(AgentDB).where(AgentDB.wallet_address == wallet.lower()))
        return result.scalar_one_or_none()


async def get_agent_by_id(agent_id: str) -> AgentDB | None:
    """Get agent by ID"""
    async with async_session() as session:
        result = await session.execute(select(AgentDB).where(AgentDB.id == agent_id))
        return result.scalar_one_or_none()


async def create_agent(agent: AgentDB) -> AgentDB:
    """Create new agent"""
    async with async_session() as session:
        session.add(agent)
        await session.commit()
        await session.refresh(agent)
        return agent


async def get_service(service_id: str) -> ServiceDB | None:
    """Get service by ID"""
    async with async_session() as session:
        result = await session.execute(select(ServiceDB).where(ServiceDB.id == service_id))
        return result.scalar_one_or_none()


async def get_services(
    category: str | None = None, provider_wallet: str | None = None, limit: int = 50, offset: int = 0
) -> list[ServiceDB]:
    """Get services with optional filters"""
    async with async_session() as session:
        query = select(ServiceDB)
        if category:
            query = query.where(ServiceDB.category == category)
        if provider_wallet:
            query = query.where(ServiceDB.provider_wallet == provider_wallet.lower())
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()


async def create_service(service: ServiceDB) -> ServiceDB:
    """Create new service"""
    async with async_session() as session:
        session.add(service)
        await session.commit()
        await session.refresh(service)
        return service


async def update_service_stats(service_id: str, calls_delta: int = 0, revenue_delta: float = 0.0):
    """Update service call count and revenue"""
    async with async_session() as session:
        result = await session.execute(select(ServiceDB).where(ServiceDB.id == service_id))
        service = result.scalar_one_or_none()
        if service:
            service.calls_count += calls_delta
            service.revenue_usdc += revenue_delta
            await session.commit()


async def count_agents() -> int:
    """Count total agents"""
    async with async_session() as session:
        from sqlalchemy import func

        result = await session.execute(select(func.count(AgentDB.id)))
        return result.scalar() or 0


async def count_services() -> int:
    """Count total services"""
    async with async_session() as session:
        from sqlalchemy import func

        result = await session.execute(select(func.count(ServiceDB.id)))
        return result.scalar() or 0


async def get_all_services() -> list[ServiceDB]:
    """Get all services (for stats)"""
    async with async_session() as session:
        result = await session.execute(select(ServiceDB))
        return result.scalars().all()


async def log_transaction(tx: TransactionDB):
    """Log a transaction"""
    async with async_session() as session:
        session.add(tx)
        await session.commit()
