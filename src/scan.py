import argparse
import asyncio
from datetime import datetime, timedelta
import os
import sys

from lib.config import Config
from lib import logging
from lib.util import dict_to_camel_case

# Initialize configuration
CONFIG = Config(config_files=["default.json", "scanner.default.json"], env_prefix="KEGTRON_SCANNER")

# Initialize logging
logging.init(config=CONFIG, fmt=logging.DEFAULT_LOG_FMT)

LOGGER = logging.getLogger("ble_scanner_3")

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from httpx import AsyncClient
from typing import Any

from lib.time import utcnow_aware
from kegtron.parser import parse

proxy_url_prefix = None

kegtron_devices = {}
device_updates = {}

def name_to_id(name):
    return name.lower().replace(" ", "-")


def to_json(data: Any):
    if isinstance(data, dict):
        for k, v in data.items():
            data[k] = to_json(v)    
        return data 
    
    if isinstance(data, datetime):
        return data.isoformat()
    
    return data

async def add_new_dev(addr: str, name: str, adv_data: AdvertisementData, parsed_data: dict):
    data = {
        "mac": addr, 
        "name": name, 
        "id": name_to_id(name), 
        "rssi": adv_data.rssi, 
        "model": parsed_data.get("model"),
        "portCnt": parsed_data.get("port_cnt"),
        "lastAdvertisementTimestampUtc": utcnow_aware(),
        "ports": {}
    }
    if await save_device(data):
        kegtron_devices[addr] = data
        LOGGER.info(f'Discovered new device: {data})')


async def save_device(data: dict) -> bool:
    if not CONFIG.get("proxy.enabled"):
        LOGGER.info("Proxy is disabled, skipping...")
        return True

    LOGGER.info(f'Saving device to proxy: "{data.get("name")}"')
    LOGGER.debug(f'Device data: {data}')
    async with AsyncClient() as client:
        r = await client.post(f'{proxy_url_prefix}/devices', json=to_json(data))
        if r.status_code != 201:
            if r.status_code == 400 and "The device already exists" in r.text:
                LOGGER.debug("Device already exists, so we are good!")
                return True
            else:    
                LOGGER.error(f'Failed to save new device. Status Code: {r.status_code}, Message: {r.text}')
                return False
        else:
            LOGGER.debug('Device data saved!')
            return True


async def update_device(data: dict, port_data: dict, port_data_raw: bytes):
    if not CONFIG.get("proxy.enabled"):
        return
    
    mac = data["mac"]
    port_index = port_data["port_index"]
    force_device_update_after_sec = CONFIG.get("force_device_update_after_sec")
    now = utcnow_aware()

    if not mac in device_updates.keys():
        device_updates[mac] = {
            "ports": {}
        }

    if not port_index in device_updates[mac]["ports"].keys():
        device_updates[mac]["ports"][port_index] = {
            "updated": now - timedelta(seconds = force_device_update_after_sec + 1),
            "raw": port_data_raw
        }

    old_port_data_raw = device_updates[mac]["ports"][port_index]["raw"]
    old_port_updated = device_updates[mac]["ports"][port_index]["updated"]

    delta = now - old_port_updated
    if delta.seconds < force_device_update_after_sec:
        if port_data_raw == old_port_data_raw:
            LOGGER.debug(f'Port data did not change for {data["id"]} on port {port_index} and its still within the force update window, skipping update')
            return
        else:
            LOGGER.info(f'Device port data changed for {data["id"]} on port {port_index}.  Updating proxy.  Old data: {old_port_data_raw}, new data: {port_data_raw}')
    else:
        LOGGER.info(f'Update window exceeded for {data["id"]} on port {port_index}, updating the proxy.  Last update: {old_port_updated.isoformat()}')

    data["last_update_timestamp_utc"] = utcnow_aware()
    transformed_data = dict_to_camel_case(data)
    LOGGER.debug(f'Updating device "{data.get("name")}" on proxy.  Device data: {transformed_data}')
    async with AsyncClient() as client:
        r = await client.patch(f'{proxy_url_prefix}/devices/{data.get("id")}', json=to_json(transformed_data))
        if r.status_code != 200:
            LOGGER.error(f'Failed to update device data. Status Code: {r.status_code}, Message: {r.text}')
        else:
            device_updates[mac]["ports"][port_index]["raw"] = port_data_raw
            device_updates[mac]["ports"][port_index]["updated"] = now
            LOGGER.debug('Device data updated!')

async def proc_kegtron_device(device: BLEDevice, adv_data: AdvertisementData, raw_data: bytes, parsed_data: dict):
    addr = device.address
    if(addr not in kegtron_devices.keys()):
        LOGGER.info("New device detected.  addr: %s, name: %s", addr, device.name)
        await add_new_dev(addr, device.name, adv_data, parsed_data)

    if(addr in kegtron_devices.keys()):
        kegtron_devices[addr]["rssi"] = adv_data.rssi
        kegtron_devices[addr]["last_advertisement_timestamp_utc"] = utcnow_aware()
        
        kegtron_devices[addr]["model"] = parsed_data["model"]
        kegtron_devices[addr]["port_cnt"] = parsed_data["port_cnt"]
        
        port_data = parsed_data["port_data"]
        kegtron_devices[addr]["ports"][port_data["port_index"]] = port_data

        await update_device(kegtron_devices[addr], port_data, raw_data)

        LOGGER.debug(kegtron_devices[addr])

async def detection_callback(device: BLEDevice, adv_data: AdvertisementData):
    try:
        if not device or not device.name:
            return
        if device.name.startswith("Kegtron"):
            LOGGER.debug("Device found: %s (%s)", device.name, device.address)
            LOGGER.debug("Device data: %s", device)
            LOGGER.debug("Advertisement data: %s", adv_data)
            if adv_data.manufacturer_data:
                for _, raw_data in adv_data.manufacturer_data.items():
                    parsed_data = parse(raw_data)
                    await proc_kegtron_device(device, adv_data, raw_data, parsed_data)
    except Exception as ex:
        LOGGER.error(str(ex))

async def scan_with_callback():
    LOGGER.info("Scanning started with callback...")
    try:
        while True: 
            # The scanner automatically starts and stops when used as an async context manager
            async with BleakScanner(detection_callback=detection_callback):
                await asyncio.sleep(5.0) # Scan for 5 seconds
    except asyncio.CancelledError:
        LOGGER.info("Cancel received, shutting down scanner.")
    except Exception as ex:
        LOGGER.error(str(ex))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--log",
        dest="loglevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.environ.get("LOG_LEVEL", logging.get_def_log_level(CONFIG)).upper(),
        help="Set the logging level",
        
    )
    parser.add_argument("--no-proxy", action="store_true", help="When true, do not send data to proxy service")

    args = parser.parse_args()

    CONFIG.set("proxy.enabled", not args.no_proxy)
    app_config = CONFIG

    proxy_url_prefix = f'{CONFIG.get("proxy.scheme")}://{CONFIG.get("proxy.host")}:{CONFIG.get("proxy.port")}/api/internal/v1'
    
    ignore_logging_modules = ['bleson']
    for i in ignore_logging_modules:
        _l = logging.getLogger(i)
        _l.setLevel(logging.ERROR)

    logging_level = logging.get_log_level(args.loglevel)
    logging.set_log_level(logging_level)
    try:
        asyncio.run(scan_with_callback())
    except KeyboardInterrupt:
        LOGGER.info("User interrupted - Goodbye")
        sys.exit()