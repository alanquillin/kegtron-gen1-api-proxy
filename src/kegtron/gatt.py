import logging
import struct
from typing import Any

from bleak import BleakClient

from lib.exceptions import InvalidKegtronAdvertisementData
import kegtron

LOGGER = logging.getLogger("kegtron.gatt")


def to_bytearray(val: Any, bytes: int, endian: str = 'little') -> bytearray:
    if isinstance(val, float):
        LOGGER.debug("rounding and converting float to int.")
        val = int(round(val))

    if isinstance(val, int):
        LOGGER.debug("converting the int value %s to bytes", val)
        b = val.to_bytes(bytes, endian)
        #b = struct.pack('<H', val)
        LOGGER.debug("converting bytes to byte array: %s", b)
        return bytearray(b)
    
    raise Exception(f"Unable to convert vale to bytearray.  Type: {type(val)}")

async def write_chars(device, data: dict[int, bytearray], response=True):
    mac = device.mac

    async with BleakClient(mac) as client:
        LOGGER.debug(f'connected to Kegtron at {mac}')
        if client.is_connected:
            for k, v in data.items():
                client.services.get_characteristic(k)
                LOGGER.debug(f"writing '{v}' to character handle '{k}'")
                await client.write_gatt_char(k, v, response=response)
        else:
            LOGGER.warning("failed to connect to device at mac: %s", mac)


async def unlock(device, port: int):
    port_cnt = device.port_cnt
    
    if port == 0:
        key = kegtron.CHAR_XGATT0_WR_UNLOCK_HANDLE
    elif port == 1:
        port_cnt = device.get("port_cnt", 1)
        if port_cnt == 1:
            raise Exception("Invalid port number 1, device only have port 0")
        key = kegtron.CHAR_XGATT1_WR_UNLOCK_HANDLE
    else:
        raise Exception("invalid port number.  Must be 0 or 1")
    
    data = {key: to_bytearray(kegtron.XGATT_WR_UNLOCK_VALUE, 4)}

    await write_chars(device, data)

async def unlock_all(device):
    port_cnt = device.port_cnt

    val = to_bytearray(kegtron.XGATT_WR_UNLOCK_VALUE, 4)
    data = {kegtron.CHAR_XGATT0_WR_UNLOCK_HANDLE: val}
    if port_cnt > 1:
        data[kegtron.CHAR_XGATT1_WR_UNLOCK_HANDLE] = val

    await write_chars(device, data)
