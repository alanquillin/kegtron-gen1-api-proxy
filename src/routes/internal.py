from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.devices import Device as deviceDB
from db.ports import Port as portsDB
from db import get_async_db
from lib.config import Config
from lib import logging
from schemas.devices import DeviceCreate, DeviceUpdate

LOGGER = logging.getLogger(__name__)
CONFIG = Config()

router = APIRouter()

async def _create_device_with_ports(device_dict: dict, db: AsyncSession):
    ports = device_dict.pop("ports", None)

    dev = await deviceDB.create(db, autocommit=False, **device_dict)
    new_ports = []
    if ports:
        for port_dict in ports:
            if "display_unit" not in port_dict:
                display_unit = CONFIG.get("default_display_unit", "ml")
                LOGGER.debug("display unit not provided, setting to system default: %s", display_unit)
                port_dict["display_unit"] = display_unit
            p = await portsDB.create(db, autocommit=False, **port_dict)
            new_ports.append(p)
    try:
        await db.commit()
        await db.refresh(dev)
        for p in ports:
            await db.refresh(p)
    except Exception:
        await db.rollback()
        raise

    return dev, ports

@router.post("/devices", status_code=201)
async def save_device(device_data: DeviceCreate, db: AsyncSession = Depends(get_async_db)):
    if not device_data.id:
        raise HTTPException(status_code=400, detail="The `id` field is required.")

    if await deviceDB.exists(device_data.id, db):
        raise HTTPException(status_code=400, detail="The device already exists")

    device_dict = device_data.model_dump()
    await _create_device_with_ports(device_dict, db)
    
    return {"created": True}


@router.patch("/devices/{device_id}")
async def update_device(device_id: str, device_data: DeviceUpdate, db: AsyncSession = Depends(get_async_db)):
    device = await deviceDB.get(device_id, db)
    if not device:
        # Create new device if doesn't exist
        device_dict = device_data.model_dump(exclude_none=True)
        await _create_device_with_ports(device_dict, db)
    else:
        # Update existing device
        device_dict = device_data.model_dump(exclude_none=True)
        LOGGER.debug("Updating device with data: %s", device_dict)
        ports_dict = device_dict.pop("ports", None)

        ports = None
        if ports_dict:
            ports =  await portsDB.query(db, device_id=device_id)

        await device.update(db, autocommit=False, **device_dict)
        updated_ports = []
        if ports_dict:
            for idx, port_dict in ports_dict.items():
                idx = int(idx)
                port_dict["device_id"] = device_id
                LOGGER.debug("Upserting port with data: %s", port_dict)
                if ports:
                    port = None
                    for _port in ports:
                        if _port.port_index == idx:
                            port = _port
                            break
                    if port:
                        LOGGER.debug("Found existing port for index %s, updating", idx)
                        p = await port.update(db, autocommit=False, **port_dict)
                        updated_ports.append(p)
                    else:
                        LOGGER.debug("No port found for index %s, creating", idx)
                        if "display_unit" not in port_dict:
                            display_unit = CONFIG.get("default_display_unit", "ml")
                            LOGGER.debug("display unit not provided, setting to system default: %s", display_unit)
                            port_dict["display_unit"] = display_unit
                        p = await portsDB.create(db, autocommit=False, **port_dict)
                        updated_ports.append(p)
                else:
                    LOGGER.debug("No existing ports found for device, creating port for index %s", idx)
                    p = await portsDB.create(db, autocommit=False, **port_dict)
                    updated_ports.append(p)
        try:
            await db.commit()
            await db.refresh(device)
            for p in updated_ports:
                await db.refresh(p)
        except Exception:
            await db.rollback()
            raise
    return {"updated": True}