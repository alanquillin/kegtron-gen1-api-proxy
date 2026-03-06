from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_async_db
from db.devices import Device as deviceDB
from db.ports import Port as portsDB
from lib import logging
from lib.config import Config
from schemas.devices import DeviceCreate, DeviceUpdate
from services.devices import transform_device

LOGGER = logging.getLogger(__name__)
CONFIG = Config()

router = APIRouter(prefix="/api/v1/devices")


async def _create_device_with_ports(device_dict: dict, db: AsyncSession):
    ports = device_dict.pop("ports", None)

    dev = await deviceDB.create(db, autocommit=False, **device_dict)
    new_ports = []
    if ports:
        # Handle ports as dict (from schema) or list (legacy)
        port_items = ports.values() if isinstance(ports, dict) else ports
        for port_dict in port_items:
            if "display_unit" not in port_dict:
                display_unit = CONFIG.get("default_display_unit", "mL")
                LOGGER.debug("display unit not provided, setting to system default: %s", display_unit)
                port_dict["display_unit"] = display_unit
            port_dict["device_id"] = dev.id
            p = await portsDB.create(db, autocommit=False, **port_dict)
            new_ports.append(p)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return dev, new_ports


@router.get("")
async def get_devices_int(db: AsyncSession = Depends(get_async_db)) -> List[dict]:
    devices = await deviceDB.list(db)
    return [transform_device(device) for device in devices]


@router.post("", status_code=201)
async def save_device(device_data: DeviceCreate, db: AsyncSession = Depends(get_async_db)):
    if not device_data.id:
        raise HTTPException(status_code=400, detail="The `id` field is required.")

    if await deviceDB.exists(device_data.id, db):
        raise HTTPException(status_code=400, detail="The device already exists")

    if await deviceDB.mac_exists(device_data.mac, db):
        raise HTTPException(status_code=400, detail=f"A device already exists for mac address {device_data.mac}")

    device_dict = device_data.model_dump()
    await _create_device_with_ports(device_dict, db)

    return {"created": True}


@router.get("/{device_id}")
async def get_device(device_id: str, db: AsyncSession = Depends(get_async_db)) -> dict:
    device = await deviceDB.get(device_id, db, options=[selectinload(deviceDB.ports)])
    if not device:
        raise HTTPException(status_code=404, detail=f"Device with id {device_id} not found")
    return transform_device(device)


async def update_device_ports(device_id: str, ports_dict: dict, ports: list[portsDB], db: AsyncSession, create_on_not_found=False):
    for idx, port_dict in ports_dict.items():
        idx = int(idx)
        LOGGER.debug("Upserting port with data: %s", port_dict)
        if ports:
            port = None
            for _port in ports:
                if _port.port_index == idx:
                    port = _port
                    break
            if port:
                LOGGER.debug("Found existing port for index %s, updating", idx)
                await port.update(db, autocommit=False, **port_dict)
            else:
                if create_on_not_found:
                    LOGGER.debug("No port found for index %s, creating", idx)
                    if "display_unit" not in port_dict:
                        display_unit = CONFIG.get("default_display_unit", "mL")
                        LOGGER.debug("display unit not provided, setting to system default: %s", display_unit)
                        port_dict["display_unit"] = display_unit
                    port_dict["device_id"] = device_id
                    await portsDB.create(db, autocommit=False, **port_dict)
                else:
                    raise HTTPException(status_code=404, detail=f"Port with index {idx} for device {device_id} not found")
        else:
            LOGGER.debug("No existing ports found for device, creating port for index %s", idx)
            port_dict["device_id"] = device_id
            await portsDB.create(db, autocommit=False, **port_dict)


@router.put("/{device_id}")
async def update_device(device_id: str, device_data: DeviceUpdate, db: AsyncSession = Depends(get_async_db)):
    device = await deviceDB.get(device_id, db)
    if not device:
        # Create new device if doesn't exist
        device_dict = device_data.model_dump(exclude_unset=True)
        if "id" not in device_dict:
            device_dict["id"] = device_id
        await _create_device_with_ports(device_dict, db)
    else:
        # Update existing device
        device_dict = device_data.model_dump(exclude_none=True)
        ports_dict = device_dict.pop("ports", None)

        ports = None
        if ports_dict:
            ports = await portsDB.query(db, device_id=device_id)

        LOGGER.debug("Updating device with data: %s", device_dict)
        await device.update(db, autocommit=False, **device_dict)
        if ports_dict:
            await update_device_ports(device_id, ports_dict, ports, db, create_on_not_found=True)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return {"updated": True}


@router.patch("/{device_id}")
async def update_device(device_id: str, device_data: DeviceUpdate, db: AsyncSession = Depends(get_async_db)):
    device = await deviceDB.get(device_id, db)
    if not device:
        # Create new device if doesn't exist
        raise HTTPException(status_code=404, detail=f"Device with id {device_id} not found")
    else:
        # Update existing device
        device_dict = device_data.model_dump(exclude_unset=True)
        LOGGER.debug("Updating device with data: %s", device_dict)
        ports_dict = device_dict.pop("ports", None)

        ports = None
        if ports_dict:
            ports = await portsDB.query(db, device_id=device_id)

        await device.update(db, autocommit=False, **device_dict)
        if ports_dict:
            await update_device_ports(device_id, ports_dict, ports, db)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return {"updated": True}
