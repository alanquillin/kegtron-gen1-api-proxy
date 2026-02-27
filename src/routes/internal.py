from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.devices import Device as deviceDB
from db import get_async_db

router = APIRouter()

class DeviceCreate(BaseModel):
    id: str = Field(..., description="Device ID")
    mac: str = Field(None, description="Device MAC address")
    name: str = Field(None, description="Device name")
    ports: Dict[str, Any] = Field(default_factory=dict, description="Device ports")

class DeviceUpdate(BaseModel):
    mac: str = Field(None, description="Device MAC address")
    name: str = Field(None, description="Device name")
    ports: Dict[str, Any] = Field(None, description="Device ports")
    rssi: int = Field(None, description="RSSI value")
    last_advertisement_timestamp_utc: str = Field(None, description="Last advertisement timestamp")
    model: str = Field(None, description="Device model")
    port_cnt: int = Field(None, description="Port count")

@router.post("/devices", status_code=201)
async def save_device(device_data: DeviceCreate, db: AsyncSession = Depends(get_async_db)):
    if not device_data.id:
        raise HTTPException(status_code=400, detail="The `id` field is required.")

    if await deviceDB.exists(device_data.id, db):
        raise HTTPException(status_code=400, detail="The device already exists")

    await deviceDB.create(device_data.id, device_data.dict(), db)

    return {"created": True}


@router.put("/devices/{device_id}")
async def update_device(device_id: str, device_data: DeviceUpdate, db: AsyncSession = Depends(get_async_db)):
    await deviceDB.update(device_id, device_data.dict(exclude_none=True), db)
    return {"updated": True}