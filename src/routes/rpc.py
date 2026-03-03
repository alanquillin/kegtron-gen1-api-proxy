from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession
from db.devices import Device as deviceDB
from db import get_async_db
import kegtron
from kegtron import gatt

router_ports = APIRouter(prefix="/api/v1/devices/{device_id}/port/{port_index}/rpc")
router_devices = APIRouter(prefix="/api/v1/devices/{device_id}/rpc")

@router_ports.post("/Kegtron.ResetVolume")
async def reset_volume_rpc(device_id: str, port_index: int, request: ResetVolumeRequest):
    raise HTTPException(status_code=405, detail="Method not yet implemented")
    # device = deviceDB.get(device_id)
    # if not device:
    #     raise HTTPException(status_code=404, detail=f'Unknown device with id {device_id}')

    # port_index = request.port
    
    # if port_index is None:
    #     port_cnt = device.get("port_cnt", 1)
    #     if port_cnt > 1:
    #         raise HTTPException(status_code=400, detail="port value is required but not supplied.")
    #     port_index = 0

    # u_data = {}
    # size_key = None
    # volume_key = None
    # if port_index == 0:
    #     u_data[kegtron.CHAR_XGATT0_PULSE_ACCUM_RST_HANDLE] = 0x42
    #     size_key = kegtron.CHAR_XGATT0_VOL_SIZE_HANDLE
    #     volume_key = kegtron.CHAR_XGATT0_VOL_START_HANDLE
    # elif port_index == 1:
    #     u_data[kegtron.CHAR_XGATT1_PULSE_ACCUM_RST_HANDLE] = 0x42
    #     size_key = kegtron.CHAR_XGATT1_VOL_SIZE_HANDLE
    #     volume_key = kegtron.CHAR_XGATT1_VOL_START_HANDLE
    # else:
    #     raise HTTPException(status_code=400, detail=f'Unknown port index: {port_index}. Must be 0 or 1')

    # if request.size:
    #     u_data[size_key] = request.size

    # if request.startVolume:
    #     u_data[volume_key] = request.startVolume

    # app.logger.debug(f'attempting to write data to device: {u_data}')
    # await gatt.write_chars(device, u_data)

    # return {"success": True}


@router_devices.post("/Kegtron.UnlockWriteAll")
async def unlock_write_all_rpc(device_id: str):
    raise HTTPException(status_code=405, detail="Method not yet implemented")
    # device = deviceDB.get(device_id)
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