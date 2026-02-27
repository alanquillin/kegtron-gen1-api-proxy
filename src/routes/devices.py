from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from db.devices import Device as deviceDB
from db import get_async_db

router = APIRouter()


@router.get("")
async def get_devices_int(db: AsyncSession = Depends(get_async_db)) -> Dict[str, Any]:
    return await deviceDB.list(db)


@router.get("/{device_id}")
async def get_device(device_id: str, db: AsyncSession = Depends(get_async_db)):
    data = await deviceDB.get(device_id, db)
    if not data:
        raise HTTPException(status_code=404, detail=f"Device with id {device_id} not found")
    return data