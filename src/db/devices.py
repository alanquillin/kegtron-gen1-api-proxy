from typing import Dict, Any, Optional

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Boolean, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, Optional, List
import secrets
import hashlib

from db import Base, CRUDMixin
from db.ports import Port

TABLE_NAME = 'devices'

class Device(Base, CRUDMixin):
    __tablename__ = TABLE_NAME

    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    mac = Column(String, unique=True, nullable=True)
    model = Column(String, nullable=True)
    port_cnt = Column(Integer, default=1)
    rssi = Column(Integer, nullable=True)
    last_advertisement_timestamp_utc = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to ports
    ports = relationship("Port", back_populates="device", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mac": self.mac,
            "model": self.model,
            "port_cnt": self.port_cnt,
            "rssi": self.rssi,
            "last_advertisement_timestamp_utc": self.last_advertisement_timestamp_utc.isoformat() if self.last_advertisement_timestamp_utc else None,
            "ports": {str(port.port_index): port.to_dict() for port in self.ports}
        }
    
    @classmethod
    async def list(cls, db: AsyncSession):
        result = await db.execute(select(Device).options(selectinload(Device.ports)))
        return result.scalars().all()

    @classmethod
    async def create_with_ports(cls, db, device_data: Dict[str, Any]):
        """Create device with ports in a single transaction"""
        from dateutil.parser import parse as parse_datetime
        
        # Extract port data if present
        ports_data = device_data.pop('ports', {})
        
        # Handle timestamp
        if 'last_advertisement_timestamp_utc' in device_data:
            timestamp = device_data['last_advertisement_timestamp_utc']
            if isinstance(timestamp, str):
                device_data['last_advertisement_timestamp_utc'] = parse_datetime(timestamp)
        
        # Create device
        device = await cls.create(db, **device_data)
        
        # Create ports
        for port_index, port_data in ports_data.items():
            port = Port(
                device_id=device.id,
                port_index=int(port_index),
                keg_size=port_data.get('keg_size'),
                total_volume=port_data.get('total_volume'),
                start_volume=port_data.get('start_volume'),
                pulse_count=port_data.get('pulse_count'),
                data=port_data
            )
            db.add(port)
        
        await db.commit()
        await db.refresh(device)
        
        # Ensure ports are loaded
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        stmt = select(cls).where(cls.id == device.id).options(selectinload(cls.ports))
        result = await db.execute(stmt)
        device = result.scalar_one()
        
        return device
    
    async def update_with_ports(self, db, update_data: Dict[str, Any]):
        """Update device and its ports"""
        from dateutil.parser import parse as parse_datetime
        
        # Extract port data if present
        ports_data = update_data.pop('ports', None)
        
        # Handle timestamp
        if 'last_advertisement_timestamp_utc' in update_data:
            timestamp = update_data['last_advertisement_timestamp_utc']
            if isinstance(timestamp, str):
                update_data['last_advertisement_timestamp_utc'] = parse_datetime(timestamp)
        
        # Update device fields
        await self.update(db, **update_data)
        
        # Update or create ports
        if ports_data:
            existing_ports = {port.port_index: port for port in self.ports}
            
            for port_index, port_data in ports_data.items():
                port_idx = int(port_index)
                if port_idx in existing_ports:
                    # Update existing port
                    port = existing_ports[port_idx]
                    await port.update(db, **{
                        'keg_size': port_data.get('keg_size', port.keg_size),
                        'total_volume': port_data.get('total_volume', port.total_volume),
                        'start_volume': port_data.get('start_volume', port.start_volume),
                        'pulse_count': port_data.get('pulse_count', port.pulse_count),
                        'data': port_data
                    })
                else:
                    # Create new port
                    port = Port(
                        device_id=self.id,
                        port_index=port_idx,
                        keg_size=port_data.get('keg_size'),
                        total_volume=port_data.get('total_volume'),
                        start_volume=port_data.get('start_volume'),
                        pulse_count=port_data.get('pulse_count'),
                        data=port_data
                    )
                    db.add(port)
        
        await db.commit()
        await db.refresh(self)
        
        # Ensure ports are loaded
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        stmt = select(Device).where(Device.id == self.id).options(selectinload(Device.ports))
        result = await db.execute(stmt)
        device = result.scalar_one()
        
        return device