from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import kegtron
from db import get_async_db
from db.devices import Device as deviceDB
from db.ports import Port as portDB
from dependencies.auth import AuthUser, require_user
from kegtron import gatt
from lib import logging
from lib.config import Config
from lib.units import to_ml
from lib.util import string_to_bytes
from schemas.rpc import ResetVolumeRequest, SetKegSizeRequest, SetPortNameRequest, SetStartVolumeRequest

LOGGER = logging.getLogger(__name__)
CONFIG = Config()


router_ports = APIRouter(prefix="/api/v1/devices/{device_id}/ports/{port_index}/rpc")
router_devices = APIRouter(prefix="/api/v1/devices/{device_id}/rpc")


async def write_data_to_device_and_update_port(device: deviceDB, port: portDB, u_data: dict[int, bytearray], updates: dict[str, any], db: AsyncSession) -> bool:
    LOGGER.debug("attempting to write data to device: %s", u_data)
    await gatt.unlock(device, port.port_index)
    LOGGER.debug("attempting to write data to device %s, data: %s", device.id, u_data)
    await gatt.write_chars(device, u_data)

    LOGGER.debug("Updating port DB data on device %s on port %s, data: %s", device.id, port.port_index, updates)
    await port.update(db, **updates)

    return True


@router_devices.post("/Kegtron.UnlockWriteAll")
async def unlock_write_all_rpc(device_id: str, db: AsyncSession = Depends(get_async_db), current_user: AuthUser = Depends(require_user)):
    device = await deviceDB.get(device_id, db)
    if not device:
        raise HTTPException(status_code=404, detail=f"Unknown device with id {device_id}")

    await gatt.unlock_all(device)

    return {"success": True}


@router_ports.post("/Kegtron.UnlockWrite")
async def unlock_write_rpc(device_id: str, port_index: int, db: AsyncSession = Depends(get_async_db), current_user: AuthUser = Depends(require_user)):
    device = await deviceDB.get(device_id, db=db)
    if not device:
        raise HTTPException(status_code=404, detail=f"Unknown device with id {device_id}")

    port_cnt = device.port_cnt
    if port_index >= port_cnt:
        raise HTTPException(status_code=400, detail=f"Port index {port_index} is out of range for device {device_id}.  Must be between 0 and {port_cnt - 1}")

    await gatt.unlock(device, port_index)

    return {"success": True}


@router_ports.post("/Kegtron.ResetVolume")
async def reset_volume_rpc(
    device_id: str, port_index: int, request: ResetVolumeRequest, db: AsyncSession = Depends(get_async_db), current_user: AuthUser = Depends(require_user)
):
    device = await deviceDB.get(device_id, db)
    if not device:
        raise HTTPException(status_code=404, detail=f"Unknown device with id {device_id}")

    port_cnt = device.port_cnt
    if port_index >= port_cnt:
        raise HTTPException(status_code=400, detail=f"Port index {port_index} is out of range for device {device_id}.  Must be between 0 and {port_cnt - 1}")

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
        raise HTTPException(status_code=400, detail=f"Unknown port index: {port_index}. Must be 0 or 1")

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

    res = await write_data_to_device_and_update_port(device, port, u_data, updates, db)

    return {"success": res}


@router_ports.post("/Kegtron.SetPortName")
async def set_port_name_rpc(
    device_id: str, port_index: int, request: SetPortNameRequest, db: AsyncSession = Depends(get_async_db), current_user: AuthUser = Depends(require_user)
):
    device = await deviceDB.get(device_id, db)
    if not device:
        raise HTTPException(status_code=404, detail=f"Unknown device with id {device_id}")

    port_cnt = device.port_cnt
    if port_index >= port_cnt:
        raise HTTPException(status_code=400, detail=f"Port index {port_index} is out of range for device {device_id}.  Must be between 0 and {port_cnt - 1}")

    port = await portDB.get_by_device_id_and_index(device_id, port_index, db)
    if not port:
        raise HTTPException(status_code=404, detail=f"Port with index {port_index} for device {device_id} not found")

    updates = {"port_name": request.name}
    u_data: dict[int, bytearray] = {}
    name_key = kegtron.CHAR_XGATT0_USER_NAME_HANDLE
    if port_index == 1:
        name_key = kegtron.CHAR_XGATT1_USER_NAME_HANDLE

    u_data[name_key] = string_to_bytes(request.name, max_len=20)

    res = await write_data_to_device_and_update_port(device, port, u_data, updates, db)

    return {"success": res}


@router_ports.post("/Kegtron.SetKegSize")
async def set_keg_size_rpc(
    device_id: str, port_index: int, request: SetKegSizeRequest, db: AsyncSession = Depends(get_async_db), current_user: AuthUser = Depends(require_user)
):
    device = await deviceDB.get(device_id, db)
    if not device:
        raise HTTPException(status_code=404, detail=f"Unknown device with id {device_id}")

    port_cnt = device.port_cnt
    if port_index >= port_cnt:
        raise HTTPException(status_code=400, detail=f"Port index {port_index} is out of range for device {device_id}.  Must be between 0 and {port_cnt - 1}")

    port = await portDB.get_by_device_id_and_index(device_id, port_index, db)
    if not port:
        raise HTTPException(status_code=404, detail=f"Port with index {port_index} for device {device_id} not found")

    updates = {"keg_size": request.keg_size}
    u_data: dict[int, bytearray] = {}
    key = kegtron.CHAR_XGATT0_VOL_SIZE_HANDLE
    if port_index == 1:
        key = kegtron.CHAR_XGATT1_VOL_SIZE_HANDLE

    unit = request.unit
    if not unit:
        unit = "mL"

    keg_size_ml = to_ml(request.keg_size, unit)
    u_data[key] = gatt.to_bytearray(keg_size_ml, 2)

    res = await write_data_to_device_and_update_port(device, port, u_data, updates, db)

    return {"success": res}


@router_ports.post("/Kegtron.SetStartVolume")
async def set_start_volume_rpc(
    device_id: str, port_index: int, request: SetStartVolumeRequest, db: AsyncSession = Depends(get_async_db), current_user: AuthUser = Depends(require_user)
):
    device = await deviceDB.get(device_id, db)
    if not device:
        raise HTTPException(status_code=404, detail=f"Unknown device with id {device_id}")

    port_cnt = device.port_cnt
    if port_index >= port_cnt:
        raise HTTPException(status_code=400, detail="port value is required but not supplied.")

    port = await portDB.get_by_device_id_and_index(device_id, port_index, db)
    if not port:
        raise HTTPException(status_code=404, detail=f"Port with index {port_index} for device {device_id} not found")

    updates = {"start_volume": request.start_volume}
    u_data: dict[int, bytearray] = {}
    key = kegtron.CHAR_XGATT0_VOL_START_HANDLE
    if port_index == 1:
        key = kegtron.CHAR_XGATT1_VOL_START_HANDLE

    unit = request.unit
    if not unit:
        unit = "mL"

    start_volume_ml = to_ml(request.start_volume, unit)
    u_data[key] = gatt.to_bytearray(start_volume_ml, 2)

    res = await write_data_to_device_and_update_port(device, port, u_data, updates, db)

    return {"success": res}
