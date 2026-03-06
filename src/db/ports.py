from typing import Any, Dict

from dateutil.parser import parse as parse_datetime
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db import Base, CRUDMixin, DictifiableMixin
from lib import logging

LOGGER = logging.getLogger(__name__)

TABLE_NAME = "ports"


class Port(Base, CRUDMixin, DictifiableMixin):
    __tablename__ = TABLE_NAME

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey("devices.id"), nullable=False)
    port_index = Column(Integer, nullable=False)
    port_name = Column(String, nullable=True)
    keg_size = Column(Float, nullable=True)
    volume_dispensed = Column(Float, nullable=True)
    start_volume = Column(Float, nullable=True)
    pulse_count = Column(Integer, nullable=True)
    display_unit = Column(String, nullable=True)
    configured = Column(Boolean, nullable=True)
    data = Column(JSON, nullable=True)  # Store any additional port data as JSON
    last_update_timestamp_utc = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship back to device
    device = relationship("Device", back_populates="ports")

    def to_dict(self, *args, **kwargs) -> Dict[str, Any]:
        return super().to_dict(*args, ignore_properties=["data"], **kwargs)

    @classmethod
    async def get_by_device_id_and_index(cls, device_id, index, db: AsyncSession):
        res = await cls.query(db, device_id=device_id, port_index=index)
        if not res:
            return None
        return res[0]

    @classmethod
    async def create(cls, db: AsyncSession, autocommit=True, **kwargs):
        # TODO override create method to check conditions:
        # - Device_id + port_index - must be unique
        if "last_update_timestamp_utc" in kwargs:
            timestamp = kwargs["last_update_timestamp_utc"]
            if isinstance(timestamp, str):
                kwargs["last_update_timestamp_utc"] = parse_datetime(timestamp)
        return await super().create(db, autocommit=autocommit, **kwargs)

    async def update(self, db: AsyncSession, autocommit=True, **kwargs):
        # TODO override create method to check conditions:
        # - Device_id + port_index - must be unique
        if "last_update_timestamp_utc" in kwargs:
            timestamp = kwargs["last_update_timestamp_utc"]
            if isinstance(timestamp, str):
                kwargs["last_update_timestamp_utc"] = parse_datetime(timestamp)
        return await super().update(db, autocommit=autocommit, **kwargs)
