from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from db.devices import Device as deviceDB
from db import get_async_db
from services.devices import transform_device

router = APIRouter()


@router.get("")
async def get_devices_int(db: AsyncSession = Depends(get_async_db)) -> List[dict]:
    devices = await deviceDB.list(db)
    return [transform_device(device) for device in devices]


@router.get("/{device_id}")
async def get_device(device_id: str, db: AsyncSession = Depends(get_async_db)) -> dict:
    from sqlalchemy.orm import selectinload
    device = await deviceDB.get(device_id, db, options=[selectinload(deviceDB.ports)])
    if not device:
        raise HTTPException(status_code=404, detail=f"Device with id {device_id} not found")
    return transform_device(device)