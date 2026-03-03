from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import Optional
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
    
    u_data = {}
    size_key = None
    volume_key = None
    if port_index == 0:
        u_data[kegtron.CHAR_XGATT0_PULSE_ACCUM_RST_HANDLE] = 0x42
        size_key = kegtron.CHAR_XGATT0_VOL_SIZE_HANDLE
        volume_key = kegtron.CHAR_XGATT0_VOL_START_HANDLE
    elif port_index == 1:
        u_data[kegtron.CHAR_XGATT1_PULSE_ACCUM_RST_HANDLE] = 0x42
        size_key = kegtron.CHAR_XGATT1_VOL_SIZE_HANDLE
        volume_key = kegtron.CHAR_XGATT1_VOL_START_HANDLE
    else:
        raise HTTPException(status_code=400, detail=f'Unknown port index: {port_index}. Must be 0 or 1')

    unit = request.unit
    if not unit:
        unit = "mL"

    if request.keg_size:
        u_data[size_key] = to_ml(request.keg_size, unit)

    if request.start_volume:
        u_data[volume_key] = to_ml(request.start_volume, unit)

    # LOGGER.debug(f'attempting to write data to device: {u_data}')
    # await gatt.unlock(device, port_index)
    LOGGER.debug(f'attempting to write data to device: {u_data}')
    await gatt.write_chars(device, u_data)

    return {"success": True}


@router_devices.post("/Kegtron.UnlockWriteAll")
async def unlock_write_all_rpc(device_id: str, db: AsyncSession = Depends(get_async_db)):
    raise HTTPException(status_code=405, detail="Method not yet implemented")
    # device = await deviceDB.get(device_id, db)
    # if not device:
    #     raise HTTPException(status_code=404, detail=f'Unknown device with id {device_id}')

    # await gatt.unlock_all(device)

    # return {"success": True}

@router_ports.post("/Kegtron.UnlockWrite")
async def unlock_write_rpc(device_id: str, port_index: int, db: AsyncSession = Depends(get_async_db)):
    raise HTTPException(status_code=405, detail="Method not yet implemented")
    # device = await deviceDB.get(device_id, db=db)
    # if not device:
    #     raise HTTPException(status_code=404, detail=f'Unknown device with id {device_id}')

    # port_index = request.port

    # if port_index is None:
    #     port_cnt = device.get("port_cnt", 1)
    #     if port_cnt > 1:
    #         raise HTTPException(status_code=400, detail="port value is required but not supplied.")
    #     port_index = 0

    # await gatt.unlock(device, port_index)

    # return {"success": True}