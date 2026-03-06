import os
from typing import Any, AsyncGenerator, Dict, List, Optional, Type, TypeVar

from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import ColumnProperty, sessionmaker

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
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine and session
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session for FastAPI dependency injection"""
    async with AsyncSessionLocal() as session:
        yield session


def _get_column_value(instance, col_name):
    try:
        return getattr(instance, col_name)
    except AttributeError:
        for attr, column in inspect(instance.__class__).c.items():
            if column.name == col_name:
                return getattr(instance, attr)
    raise AttributeError


T = TypeVar("T", bound="CRUDMixin")


class CRUDMixin:
    """Mixin class providing CRUD operations for SQLAlchemy models"""

    @classmethod
    async def count_all(cls: Type[T], db: AsyncSession):
        count_statement = select(func.count()).select_from(cls)
        result = await db.execute(count_statement)
        return result.scalar_one()

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
    async def query(cls: Type[T], db: AsyncSession, **kwargs):
        q = select(cls).filter_by(**kwargs)

        result = await db.execute(q)
        return result.unique().scalars().all()

    @classmethod
    async def get_multi(cls: Type[T], db: AsyncSession, *, skip: int = 0, limit: int = 100, filters: list = None, options: list = None) -> List[T]:
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
    async def create(cls: Type[T], db: AsyncSession, autocommit=True, **kwargs) -> T:
        """Create a new record (async)"""
        db_obj = cls(**kwargs)
        db.add(db_obj)
        if autocommit:
            try:
                await db.commit()
                await db.refresh(db_obj)
            except Exception:
                await db.rollback()
                raise

        return db_obj

    async def update(self: T, db: AsyncSession, autocommit=True, **kwargs) -> T:
        """Update an existing record (async)"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.add(self)
        if autocommit:
            try:
                await db.commit()
                await db.refresh(self)
            except Exception:
                await db.rollback()
                raise
        return self

    async def delete(self: T, db: AsyncSession, autocommit=True) -> bool:
        """Delete a record (async)"""
        await db.delete(self)
        if autocommit:
            try:
                await db.commit()
            except Exception:
                await db.rollback()
                raise
        return True

    @classmethod
    async def exists(cls: Type[T], id: Any, db: AsyncSession) -> bool:
        """Check if a record exists by ID (async)"""
        result = await db.execute(select(cls.id).where(cls.id == id))
        return result.scalar_one_or_none() is not None


class DictifiableMixin:
    def to_dict(self, include_relationships=None, ignore_properties=None):
        result = {}

        if not ignore_properties:
            ignore_properties = []

        for name, attr in inspect(self.__class__).all_orm_descriptors.items():
            if name in ignore_properties:
                continue
            if name.startswith("_"):
                continue
            if hasattr(attr, "property") and not isinstance(attr.property, ColumnProperty):
                continue

            name = getattr(attr, "name", name)
            result[name] = _get_column_value(self, name)

        if not include_relationships:
            include_relationships = []

        for rel in include_relationships:
            val = getattr(self, rel)
            if val is not None:
                result[rel] = getattr(self, rel).to_dict()

        return result

    def _json_repr_(self, *args, **kwargs):
        return self.to_dict(*args, **kwargs)
