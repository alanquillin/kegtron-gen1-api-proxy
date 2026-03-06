import argparse
import asyncio
import copy
import os
import sys
from datetime import datetime, timedelta

from lib import logging
from lib.config import Config
from lib.util import dict_to_camel_case

if __name__ == "__main__":
    # Initialize configuration
    CONFIG = Config(config_files=["default.json"], env_prefix="KEGTRON_SCANNER")
    # Initialize logging
    logging.init(config=CONFIG, fmt=logging.DEFAULT_LOG_FMT)
else:
    CONFIG = Config()

BACKEND = CONFIG.get("scanner.backend", "api")
if BACKEND == "db":
    from db import AsyncSessionLocal
    from db.devices import Device
    from db.ports import Port

LOGGER = logging.getLogger("ble_scanner")

from typing import Any

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from httpx import AsyncClient

from kegtron.parser import parse
from lib.time import utcnow_aware

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
        "port_cnt": parsed_data.get("port_cnt"),
        "last_advertisement_timestamp_utc": utcnow_aware(),
        "ports": {},
    }
    if await save_device(data):
        kegtron_devices[addr] = data
        LOGGER.info(f"Discovered new device: {data})")


async def _save_device_db(data: dict) -> bool:
    device_id = data["id"]
    mac = data["mac"]

    device_dict = data.copy()
    device_dict.pop("ports", None)
    LOGGER.info(f'Saving device to DB: "{device_id}"')
    LOGGER.debug(f"Device data: {device_dict}")
    async with AsyncSessionLocal() as db:
        if await Device.exists(device_id, db) or await Device.mac_exists(mac, db):
            return True
        device = await Device.create(db, **device_dict)

        return True if device else False


async def _save_device_api(data: dict) -> bool:
    if not CONFIG.get("proxy.enabled"):
        LOGGER.info("Proxy is disabled, skipping...")
        return True

    transformed_data = dict_to_camel_case(data)
    LOGGER.info(f'Saving device to proxy: "{data.get("name")}"')
    LOGGER.debug(f"Device data: {transformed_data}")
    async with AsyncClient() as client:
        r = await client.post(f"{proxy_url_prefix}/devices", json=to_json(transformed_data))
        if r.status_code != 201:
            if r.status_code == 400 and "The device already exists" in r.text:
                LOGGER.debug("Device already exists, so we are good!")
                return True
            else:
                LOGGER.error(f"Failed to save new device. Status Code: {r.status_code}, Message: {r.text}")
                return False
        else:
            LOGGER.debug("Device data saved!")
            return True


async def save_device(data: dict) -> bool:
    if BACKEND == "api":
        return await _save_device_api(data)

    return await _save_device_db(data)


async def _update_device_db(data: dict) -> bool:
    device_id = data["id"]
    async with AsyncSessionLocal() as db:
        device = await Device.get(device_id, db)
        ports = await Port.query(db, device_id=device_id)

        device_dict = copy.deepcopy(data)
        ports_dict = device_dict.pop("ports", None)
        if not device:
            device = await Device.create(db, autocommit=False, **device_dict)
        else:
            await device.update(db, autocommit=False, **device_dict)

        for idx, port_dict in ports_dict.items():
            port = None
            for _port in ports:
                if _port.port_index == idx:
                    port = _port
                    break
            if not port:
                port_dict["device_id"] = device_id
                port = await Port.create(db, autocommit=False, **port_dict)
            else:
                await port.update(db, autocommit=False, **port_dict)

        try:
            await db.commit()
            return True
        except Exception as ex:
            await db.rollback()
            LOGGER.error("Failed to update device and port data.  Error: %s", ex, exc_info=True)
            return False


async def _update_device_api(data: dict) -> bool:
    if not CONFIG.get("proxy.enabled"):
        LOGGER.info("Proxy is disabled, skipping...")
        return True

    LOGGER.debug("Transforming data: %s", data)
    transformed_data = dict_to_camel_case(data)
    LOGGER.debug(f'Updating device "{data.get("name")}" on proxy.  Device data: {transformed_data}')
    async with AsyncClient() as client:
        r = await client.put(f'{proxy_url_prefix}/devices/{data.get("id")}', json=to_json(transformed_data))
        if r.status_code != 200:
            LOGGER.error(f"Failed to update device data. Status Code: {r.status_code}, Message: {r.text}")
            return False
        else:
            return True


async def update_device(data: dict, port_data: dict, port_data_raw: bytes):
    mac = data["mac"]
    port_index = port_data["port_index"]
    force_device_update_after_sec = CONFIG.get("scanner.force_device_update_after_sec")
    now = utcnow_aware()

    if not mac in device_updates.keys():
        device_updates[mac] = {"ports": {}}

    if not port_index in device_updates[mac]["ports"].keys():
        device_updates[mac]["ports"][port_index] = {"updated": now - timedelta(seconds=force_device_update_after_sec + 1), "raw": port_data_raw}

    old_port_data_raw = device_updates[mac]["ports"][port_index]["raw"]
    old_port_updated = device_updates[mac]["ports"][port_index]["updated"]

    delta = now - old_port_updated
    if delta.seconds < force_device_update_after_sec:
        if port_data_raw == old_port_data_raw:
            LOGGER.debug(f'Port data did not change for {data["id"]} on port {port_index} and its still within the force update window, skipping update')
            return
        else:
            LOGGER.info(
                f'Device port data changed for {data["id"]} on port {port_index}.  Updating proxy.  Old data: {old_port_data_raw}, new data: {port_data_raw}'
            )
    else:
        LOGGER.info(f'Update window exceeded for {data["id"]} on port {port_index}, updating the proxy.  Last update: {old_port_updated.isoformat()}')

    data["last_update_timestamp_utc"] = now
    res = False
    if BACKEND == "api":
        res = await _update_device_api(data)
    else:
        res = await _update_device_db(data)

    if res:
        device_updates[mac]["ports"][port_index]["raw"] = port_data_raw
        device_updates[mac]["ports"][port_index]["updated"] = now
        LOGGER.debug("Device data updated!")
    else:
        LOGGER.error("Device update failed!")


async def proc_kegtron_device(device: BLEDevice, adv_data: AdvertisementData, raw_data: bytes, parsed_data: dict):
    addr = device.address
    if addr not in kegtron_devices.keys():
        LOGGER.info("New device detected.  addr: %s, name: %s", addr, device.name)
        await add_new_dev(addr, device.name, adv_data, parsed_data)

    if addr in kegtron_devices.keys():
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
        LOGGER.error(str(ex), exc_info=True)


async def scan():
    LOGGER.info("Scanning started...")
    try:
        while True:
            # The scanner automatically starts and stops when used as an async context manager
            async with BleakScanner(detection_callback=detection_callback):
                await asyncio.sleep(5.0)  # Scan for 5 seconds
    except asyncio.CancelledError:
        LOGGER.info("Cancel received, shutting down scanner.")
    except Exception as ex:
        LOGGER.error(str(ex), exc_info=True)


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

    proxy_url_prefix = f'{CONFIG.get("proxy.scheme")}://{CONFIG.get("proxy.host")}:{CONFIG.get("proxy.port")}/api/v1'

    ignore_logging_modules = ["bleson"]
    for i in ignore_logging_modules:
        _l = logging.getLogger(i)
        _l.setLevel(logging.ERROR)

    logging_level = logging.get_log_level(args.loglevel)
    logging.set_log_level(logging_level)
    try:
        asyncio.run(scan())
    except KeyboardInterrupt:
        LOGGER.info("User interrupted - Goodbye")
        sys.exit()
