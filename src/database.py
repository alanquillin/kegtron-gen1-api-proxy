import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import asyncio
from typing import AsyncGenerator

# Database URL
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./kegtron.db")
ASYNC_DATABASE_URL = os.environ.get("ASYNC_DATABASE_URL", "sqlite+aiosqlite:///./kegtron.db")

# Sync engine and session
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine and session
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    future=True
)

AsyncSessionLocal = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


@contextmanager
def get_db():
    """Sync database session context manager"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session for FastAPI dependency injection"""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Initialize database tables"""
    from models.device import Base
    
    # For async SQLite, we need to use run_sync
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db_sync():
    """Initialize database tables synchronously"""
    from models.device import Base
    Base.metadata.create_all(bind=engine)