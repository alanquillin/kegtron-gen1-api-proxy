from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import struct
from typing import Optional, Any
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession
from db.devices import Device as deviceDB
from db.ports import Port as portDB
from db import get_async_db
import kegtron
from kegtron import gatt
from schemas.rpc import ResetVolumeRequest
from lib.config import Config
from lib import logging
from lib.units import to_ml

LOGGER = logging.getLogger(__name__)
CONFIG = Config()


router_ports = APIRouter(prefix="/api/v1/devices/{device_id}/port/{port_index}/rpc")
router_devices = APIRouter(prefix="/api/v1/devices/{device_id}/rpc")


@router_devices.post("/Kegtron.UnlockWriteAll")
async def unlock_write_all_rpc(device_id: str, db: AsyncSession = Depends(get_async_db)):
    device = await deviceDB.get(device_id, db)
    if not device:
        raise HTTPException(status_code=404, detail=f'Unknown device with id {device_id}')

    await gatt.unlock_all(device)

    return {"success": True}

@router_ports.post("/Kegtron.UnlockWrite")
async def unlock_write_rpc(device_id: str, port_index: int, db: AsyncSession = Depends(get_async_db)):
    device = await deviceDB.get(device_id, db=db)
    if not device:
        raise HTTPException(status_code=404, detail=f'Unknown device with id {device_id}')

    if port_index is None:
        port_cnt = device.get("port_cnt", 1)
        if port_cnt > 1:
            raise HTTPException(status_code=400, detail="port value is required but not supplied.")
        port_index = 0

    await gatt.unlock(device, port_index)

    return {"success": True}


@router_ports.post("/Kegtron.ResetVolume")
async def reset_volume_rpc(device_id: str, port_index: int, request: ResetVolumeRequest, db: AsyncSession = Depends(get_async_db)):
    #raise HTTPException(status_code=405, detail="Method not yet implemented")
    device = await deviceDB.get(device_id, db)
    if not device:
        raise HTTPException(status_code=404, detail=f'Unknown device with id {device_id}')
    
    port_cnt = device.port_cnt
    if port_index >= port_cnt:
        raise HTTPException(status_code=400, detail="port value is required but not supplied.")

    port = await portDB.get_by_device_id_and_index(device_id, port_index, db)
    if not port:
        raise HTTPException(status_code=404, detail=f"Port with index {port_index} for device {device_id} not found")
    
    updates = {"volume_dispensed": 0}
    u_data: dict[int, bytearray] = {}
    size_key = None
    volume_key = None
    if port_index == 0:
        u_data[kegtron.CHAR_XGATT0_PULSE_ACCUM_RST_HANDLE] = gatt.to_bytearray(0x42, 1)
        size_key = kegtron.CHAR_XGATT0_VOL_SIZE_HANDLE
        volume_key = kegtron.CHAR_XGATT0_VOL_START_HANDLE
    elif port_index == 1:
        u_data[kegtron.CHAR_XGATT1_PULSE_ACCUM_RST_HANDLE] = gatt.to_bytearray(0x42, 1)
        size_key = kegtron.CHAR_XGATT1_VOL_SIZE_HANDLE
        volume_key = kegtron.CHAR_XGATT1_VOL_START_HANDLE
    else:
        raise HTTPException(status_code=400, detail=f'Unknown port index: {port_index}. Must be 0 or 1')

    unit = request.unit
    if not unit:
        unit = "mL"

    if request.keg_size:
        keg_size_ml = to_ml(request.keg_size, unit)
        updates["keg_size"] = keg_size_ml
        u_data[size_key] = gatt.to_bytearray(keg_size_ml, 2)

    if request.start_volume:
        start_volume_ml = to_ml(request.start_volume, unit)
        updates["start_volume"] = start_volume_ml
        u_data[volume_key] = gatt.to_bytearray(start_volume_ml, 2)

    LOGGER.debug(f'attempting to write data to device: {u_data}')
    await gatt.unlock(device, port_index)
    LOGGER.debug(f'attempting to write data to device {device_id}, data: {u_data}')
    await gatt.write_chars(device, u_data)
    LOGGER.debug(f"done writing to device {device_id}")

    LOGGER.debug(f"Updating port DB data on device {device_id} on port {port_index}, data: {updates}")
    await port.update(db, **updates)

    return {"success": True}
