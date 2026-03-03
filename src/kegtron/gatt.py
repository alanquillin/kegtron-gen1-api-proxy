import logging
from struct import unpack
from datetime import datetime, timezone

from bleak import BleakClient, BleakScanner

from lib.exceptions import InvalidKegtronAdvertisementData
import kegtron

LOGGER = logging.getLogger("kegtron.gatt")


async def write_chars(device, data, response=True):
    mac = device.mac

    async with BleakClient(mac) as client:
        LOGGER.debug(f'connected to Kegtron at {mac}')
        for k, v in data.items():
            client.services.get_characteristic(k)
            LOGGER.debug(f"writing '{v}' to character handle '{k}'")
            await client.write_gatt_char(k, v, response=response)


async def unlock(device, port: int):
    port_cnt = device.get("port_cnt", 1)
    
    if port == 0:
        key = kegtron.CHAR_XGATT0_WR_UNLOCK_HANDLE
    elif port == 1:
        port_cnt = device.get("port_cnt", 1)
        if port_cnt == 1:
            raise Exception("Invalid port number 1, device only have port 0")
        key = kegtron.CHAR_XGATT1_WR_UNLOCK_HANDLE
    else:
        raise Exception("invalid port number.  Must be 0 or 1")
    
    data = {key: kegtron.XGATT_WR_UNLOCK_VALUE}

    await write_chars(device, data)

async def unlock_all(device):
    port_cnt = device.get("port_cnt", 1)

    data = {kegtron.CHAR_XGATT0_WR_UNLOCK_HANDLE: kegtron.XGATT_WR_UNLOCK_VALUE}
    if port_cnt > 1:
        data[kegtron.CHAR_XGATT1_WR_UNLOCK_HANDLE] = kegtron.XGATT_WR_UNLOCK_VALUE

    await write_chars(device, data)
