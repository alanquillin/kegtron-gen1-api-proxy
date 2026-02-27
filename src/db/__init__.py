import os
from typing import AsyncGenerator, Dict, Any, Optional, List, Type, TypeVar

from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session, selectinload, DeclarativeMeta
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager

from lib import logging
from lib.config import Config

__all__ = [
    "Base",
    "devices",
    "ports",
]

CONFIG = Config()
LOGGER = logging.getLogger(__name__)

# Database URL
def get_db_file_path() -> str:
    path = CONFIG.get("db.path")
    base_dir = CONFIG.get("db.base_dir")
    if base_dir:
        path = os.path.normpath(os.path.join(base_dir, path))
    LOGGER.debug("DB file path: %s", path)
    return path

DATABASE_URL = f"sqlite:///{get_db_file_path()}"
ASYNC_DATABASE_URL = f"sqlite+aiosqlite:///{get_db_file_path()}"

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
    
    # For async SQLite, we need to use run_sync
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db_sync():
    """Initialize database tables synchronously"""
    Base.metadata.create_all(bind=engine)

Base = declarative_base()

T = TypeVar('T', bound='CRUDMixin')


class CRUDMixin:
    """Mixin class providing CRUD operations for SQLAlchemy models"""
    
    @classmethod
    async def list(cls, db: AsyncSession) -> List[T]:
        result = await db.execute(select(cls))
        return result.scalars().all()

    @classmethod
    async def get(cls: Type[T], id: Any, db: AsyncSession, options: list = None) -> Optional[T]:
        """Get a single record by ID (async)"""
        query = select(cls).where(cls.id == id)
        if options:
            for option in options:
                query = query.options(option)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_multi(
        cls: Type[T], 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: list = None,
        options: list = None
    ) -> List[T]:
        """Get multiple records (async)"""
        query = select(cls)
        if filters:
            for f in filters:
                query = query.where(f)
        if options:
            for option in options:
                query = query.options(option)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
        
    @classmethod
    async def create(cls: Type[T], db: AsyncSession, **kwargs) -> T:
        """Create a new record (async)"""
        db_obj = cls(**kwargs)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(self: T, db: AsyncSession, **kwargs) -> T:
        """Update an existing record (async)"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.add(self)
        await db.commit()
        await db.refresh(self)
        return self
    
    async def delete(self: T, db: AsyncSession) -> bool:
        """Delete a record (async)"""
        await db.delete(self)
        await db.commit()
        return True
    
    @classmethod
    async def exists(cls: Type[T], id: Any, db: AsyncSession) -> bool:
        """Check if a record exists by ID (async)"""
        result = await db.execute(select(cls.id).where(cls.id == id))
        return result.scalar_one_or_none() is not None
    
    # Synchronous versions for backward compatibility
    @classmethod
    def get_sync(cls: Type[T], id: Any, db: Session, options: list = None) -> Optional[T]:
        """Get a single record by ID (sync)"""
        query = db.query(cls)
        if options:
            for option in options:
                query = query.options(option)
        return query.filter(cls.id == id).first()
    
    @classmethod
    def get_multi_sync(
        cls: Type[T], 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: list = None,
        options: list = None
    ) -> List[T]:
        """Get multiple records (sync)"""
        query = db.query(cls)
        if filters:
            for f in filters:
                query = query.filter(f)
        if options:
            for option in options:
                query = query.options(option)
        return query.offset(skip).limit(limit).all()
    
    @classmethod
    def create_sync(cls: Type[T], db: Session, **kwargs) -> T:
        """Create a new record (sync)"""
        db_obj = cls(**kwargs)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_sync(self: T, db: Session, **kwargs) -> T:
        """Update an existing record (sync)"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.add(self)
        db.commit()
        db.refresh(self)
        return self
    
    def delete_sync(self: T, db: Session) -> bool:
        """Delete a record (sync)"""
        db.delete(self)
        db.commit()
        return True
    
    @classmethod
    def exists_sync(cls: Type[T], id: Any, db: Session) -> bool:
        """Check if a record exists by ID (sync)"""
        return db.query(cls.id).filter(cls.id == id).first() is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary - should be overridden by subclasses"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}