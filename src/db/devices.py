from dateutil.parser import parse as parse_datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Boolean, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, Optional, List
import secrets
import hashlib

from db import Base, CRUDMixin, DictifiableMixin
from db.ports import Port
from lib import logging

LOGGER = logging.getLogger(__name__)

TABLE_NAME = 'devices'

class Device(Base, CRUDMixin, DictifiableMixin):
    __tablename__ = TABLE_NAME

    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    mac = Column(String, unique=True, nullable=False)
    model = Column(String, nullable=True)
    port_cnt = Column(Integer, nullable=True)
    rssi = Column(Integer, nullable=True)
    last_advertisement_timestamp_utc = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to ports
    ports = relationship("Port", back_populates="device", cascade="all, delete-orphan")

    @classmethod
    async def list(cls, db: AsyncSession):
        result = await db.execute(select(Device).options(selectinload(Device.ports)))
        return result.scalars().all()
    
    @classmethod
    async def create(cls, db: AsyncSession, autocommit=True, **kwargs):
        if 'last_advertisement_timestamp_utc' in kwargs:
            timestamp = kwargs['last_advertisement_timestamp_utc']
            if isinstance(timestamp, str):
                kwargs['last_advertisement_timestamp_utc'] = parse_datetime(timestamp)
        return await super().create(db, autocommit=autocommit, **kwargs)
    
    async def update(self, db: AsyncSession, autocommit=True, **kwargs):
        if 'last_advertisement_timestamp_utc' in kwargs:
            timestamp = kwargs['last_advertisement_timestamp_utc']
            if isinstance(timestamp, str):
                kwargs['last_advertisement_timestamp_utc'] = parse_datetime(timestamp)
        return await super().update(db, autocommit=autocommit, **kwargs)

    @classmethod
    async def mac_exists(cls, mac: Any, db: AsyncSession) -> bool:
        """Check if a record exists by ID (async)"""
        result = await db.execute(select(cls.mac).where(cls.mac == mac))
        return result.scalar_one_or_none() is not None