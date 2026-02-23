from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload
from datetime import datetime
from dateutil.parser import parse as parse_datetime

from database import get_db, get_async_db, SessionLocal
from models import Device, Port


async def exists(device_id: str, db: AsyncSession = None) -> bool:
    """Check if device exists (async)"""
    if db is None:
        async with get_async_db() as session:
            return await exists(device_id, session)
    
    result = await db.execute(select(Device).where(Device.id == device_id))
    return result.scalar_one_or_none() is not None


async def get(device_id: str, db: AsyncSession = None) -> Optional[Dict[str, Any]]:
    """Get device by ID (async)"""
    if db is None:
        async with get_async_db() as session:
            return await get(device_id, session)
    
    result = await db.execute(
        select(Device).options(selectinload(Device.ports)).where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    return device.to_dict() if device else None


async def list(db: AsyncSession = None) -> Dict[str, Any]:
    """List all devices (async)"""
    if db is None:
        async for session in get_async_db():
            return await list(session)
    
    result = await db.execute(select(Device).options(selectinload(Device.ports)))
    devices = result.scalars().all()
    return {device.id: device.to_dict() for device in devices}


async def create(device_id: str, data: Dict[str, Any], db: AsyncSession = None) -> Dict[str, Any]:
    """Create new device (async)"""
    if db is None:
        async for session in get_async_db():
            return await create(device_id, data, session)
    
    # Create device
    device = Device(
        id=device_id,
        name=data.get("name"),
        mac=data.get("mac"),
        model=data.get("model"),
        port_cnt=data.get("port_cnt", 1),
        rssi=data.get("rssi")
    )
    
    # Handle last_advertisement_timestamp_utc if present
    if "last_advertisement_timestamp_utc" in data:
        timestamp = data["last_advertisement_timestamp_utc"]
        if isinstance(timestamp, str):
            device.last_advertisement_timestamp_utc = parse_datetime(timestamp)
        elif isinstance(timestamp, datetime):
            device.last_advertisement_timestamp_utc = timestamp
    
    # Handle ports if present
    if "ports" in data and isinstance(data["ports"], dict):
        for port_index, port_data in data["ports"].items():
            port = Port(
                port_index=int(port_index),
                keg_size=port_data.get("keg_size"),
                total_volume=port_data.get("total_volume"),
                start_volume=port_data.get("start_volume"),
                pulse_count=port_data.get("pulse_count"),
                data=port_data  # Store all data as JSON
            )
            device.ports.append(port)
    
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device.to_dict()


async def update(device_id: str, data: Dict[str, Any], db: AsyncSession = None) -> Dict[str, Any]:
    """Update device (async)"""
    if db is None:
        async for session in get_async_db():
            return await update(device_id, data, session)
    
    result = await db.execute(
        select(Device).options(selectinload(Device.ports)).where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        # Create new device if doesn't exist
        return await create(device_id, data, db)
    
    # Update fields
    if "name" in data:
        device.name = data["name"]
    if "mac" in data:
        device.mac = data["mac"]
    if "model" in data:
        device.model = data["model"]
    if "port_cnt" in data:
        device.port_cnt = data["port_cnt"]
    if "rssi" in data:
        device.rssi = data["rssi"]
    if "last_advertisement_timestamp_utc" in data:
        timestamp = data["last_advertisement_timestamp_utc"]
        if isinstance(timestamp, str):
            device.last_advertisement_timestamp_utc = parse_datetime(timestamp)
        elif isinstance(timestamp, datetime):
            device.last_advertisement_timestamp_utc = timestamp
    
    # Update or create ports
    if "ports" in data and isinstance(data["ports"], dict):
        existing_ports = {port.port_index: port for port in device.ports}
        
        for port_index, port_data in data["ports"].items():
            port_idx = int(port_index)
            if port_idx in existing_ports:
                # Update existing port
                port = existing_ports[port_idx]
                if "keg_size" in port_data:
                    port.keg_size = port_data["keg_size"]
                if "total_volume" in port_data:
                    port.total_volume = port_data["total_volume"]
                if "start_volume" in port_data:
                    port.start_volume = port_data["start_volume"]
                if "pulse_count" in port_data:
                    port.pulse_count = port_data["pulse_count"]
                port.data = port_data  # Update JSON data
            else:
                # Create new port
                port = Port(
                    port_index=port_idx,
                    keg_size=port_data.get("keg_size"),
                    total_volume=port_data.get("total_volume"),
                    start_volume=port_data.get("start_volume"),
                    pulse_count=port_data.get("pulse_count"),
                    data=port_data
                )
                device.ports.append(port)
    
    await db.commit()
    await db.refresh(device)
    return device.to_dict()


# Synchronous versions for backward compatibility (used by scan.py)
def exists_sync(device_id: str) -> bool:
    """Check if device exists (sync)"""
    with get_db() as db:
        device = db.query(Device).filter(Device.id == device_id).first()
        return device is not None


def get_sync(device_id: str) -> Optional[Dict[str, Any]]:
    """Get device by ID (sync)"""
    with get_db() as db:
        device = db.query(Device).options(selectinload(Device.ports)).filter(Device.id == device_id).first()
        return device.to_dict() if device else None


def list_sync() -> Dict[str, Any]:
    """List all devices (sync)"""
    with get_db() as db:
        devices = db.query(Device).options(selectinload(Device.ports)).all()
        return {device.id: device.to_dict() for device in devices}


def create_sync(device_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create new device (sync)"""
    with get_db() as db:
        device = Device(
            id=device_id,
            name=data.get("name"),
            mac=data.get("mac"),
            model=data.get("model"),
            port_cnt=data.get("port_cnt", 1),
            rssi=data.get("rssi")
        )
        
        if "last_advertisement_timestamp_utc" in data:
            timestamp = data["last_advertisement_timestamp_utc"]
            if isinstance(timestamp, str):
                device.last_advertisement_timestamp_utc = parse_datetime(timestamp)
            elif isinstance(timestamp, datetime):
                device.last_advertisement_timestamp_utc = timestamp
        
        if "ports" in data and isinstance(data["ports"], dict):
            for port_index, port_data in data["ports"].items():
                port = Port(
                    port_index=int(port_index),
                    keg_size=port_data.get("keg_size"),
                    total_volume=port_data.get("total_volume"),
                    start_volume=port_data.get("start_volume"),
                    pulse_count=port_data.get("pulse_count"),
                    data=port_data
                )
                device.ports.append(port)
        
        db.add(device)
        db.commit()
        db.refresh(device)
        return device.to_dict()


def update_sync(device_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update device (sync)"""
    with get_db() as db:
        device = db.query(Device).options(selectinload(Device.ports)).filter(Device.id == device_id).first()
        
        if not device:
            return create_sync(device_id, data)
        
        if "name" in data:
            device.name = data["name"]
        if "mac" in data:
            device.mac = data["mac"]
        if "model" in data:
            device.model = data["model"]
        if "port_cnt" in data:
            device.port_cnt = data["port_cnt"]
        if "rssi" in data:
            device.rssi = data["rssi"]
        if "last_advertisement_timestamp_utc" in data:
            timestamp = data["last_advertisement_timestamp_utc"]
            if isinstance(timestamp, str):
                device.last_advertisement_timestamp_utc = parse_datetime(timestamp)
            elif isinstance(timestamp, datetime):
                device.last_advertisement_timestamp_utc = timestamp
        
        if "ports" in data and isinstance(data["ports"], dict):
            existing_ports = {port.port_index: port for port in device.ports}
            
            for port_index, port_data in data["ports"].items():
                port_idx = int(port_index)
                if port_idx in existing_ports:
                    port = existing_ports[port_idx]
                    if "keg_size" in port_data:
                        port.keg_size = port_data["keg_size"]
                    if "total_volume" in port_data:
                        port.total_volume = port_data["total_volume"]
                    if "start_volume" in port_data:
                        port.start_volume = port_data["start_volume"]
                    if "pulse_count" in port_data:
                        port.pulse_count = port_data["pulse_count"]
                    port.data = port_data
                else:
                    port = Port(
                        port_index=port_idx,
                        keg_size=port_data.get("keg_size"),
                        total_volume=port_data.get("total_volume"),
                        start_volume=port_data.get("start_volume"),
                        pulse_count=port_data.get("pulse_count"),
                        data=port_data
                    )
                    device.ports.append(port)
        
        db.commit()
        db.refresh(device)
        return device.to_dict()