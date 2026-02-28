from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from db.devices import Device as deviceDB
from db import get_async_db

router = APIRouter()


@router.get("")
async def get_devices_int(db: AsyncSession = Depends(get_async_db)) -> Dict[str, Any]:
    devices = await deviceDB.list(db)
    return [device.to_dict() for device in devices]


@router.get("/{device_id}")
async def get_device(device_id: str, db: AsyncSession = Depends(get_async_db)):
    from sqlalchemy.orm import selectinload
    device = await deviceDB.get(device_id, db, options=[selectinload(deviceDB.ports)])
    if not device:
        raise HTTPException(status_code=404, detail=f"Device with id {device_id} not found")
    return device.to_dict()