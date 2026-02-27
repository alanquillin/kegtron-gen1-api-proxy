import argparse
import os
from datetime import datetime, timedelta
import sys

from lib.config import Config
from lib import logging

# Initialize configuration
CONFIG = Config(config_files=["default.json", "scanner.default.json"], env_prefix="KENGTRON_SCANNER")

# Initialize logging
logging.init(config=CONFIG, fmt=logging.DEFAULT_LOG_FMT)

from adafruit_ble import BLERadio
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
import httpx

from lib.time import utcnow_aware
from kegtron import parser as kegtron_parser

LOG = logging.getLogger("ble_scanner")

proxy_url_prefix = None

kegtron_devices = {}
device_updates = {}

def name_to_id(name):
    return name.lower().replace(" ", "-")


def to_json(data):
    if isinstance(data, dict):
        for k, v in data.items():
            data[k] = to_json(v)    
        return data 
    
    if isinstance(data, datetime):
        return data.isoformat()
    
    return data

def add_new_dev(addr, name, adv):
    data = {"mac": addr, "name": name, "id": name_to_id(name), "ports": {}}
    if save_device(data):
        kegtron_devices[addr] = data
        LOG.info(f'Discovered new device: {data})')


def save_device(data):
    if not CONFIG.get("proxy.enabled"):
        return True

    LOG.info(f'Saving device to proxy: "{data.get("name")}"')
    LOG.debug(f'Device data: {data}')
    r = httpx.post(f'{proxy_url_prefix}/devices', json=to_json(data))
    if r.status_code != 201:
        if r.status_code == 400 and "The device already exists" in r.text:
            LOG.debug("Device already exists, so we are good!")
            return True
        else:    
            LOG.error(f'Failed to save new device. Status Code: {r.status_code}, Message: {r.text}')
            return False
    else:
        LOG.debug('Device data saved!')
        return True


def update_device(data, port_data, port_data_raw):
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
            LOG.debug(f'Port data did not change for {data["id"]} on port {port_index} and its still within the force update window, skipping update')
            return
        else:
            LOG.info(f'Device port data changed for {data["id"]} on port {port_index}.  Updating proxy.  Old data: {old_port_data_raw}, new data: {port_data_raw}')
    else:
        LOG.info(f'Update window exceeded for {data["id"]} on port {port_index}, updating the proxy.  Last update: {old_port_updated.isoformat()}')

    LOG.debug(f'Updating device "{data.get("name")}" on proxy.  Device data: {data}')
    r = httpx.put(f'{proxy_url_prefix}/devices/{data.get("id")}', json=to_json(data))
    if r.status_code != 200:
        LOG.error(f'Failed to update device data. Status Code: {r.status_code}, Message: {r.text}')
    else:
        device_updates[mac]["ports"][port_index]["raw"] = port_data_raw
        device_updates[mac]["ports"][port_index]["updated"] = now
        LOG.debug('Device data updated!')


def on_adv(adv):
    addr = adv.address.string
    if(addr not in kegtron_devices.keys()):
        if adv.short_name and adv.short_name.startswith("Kegtron"):
            add_new_dev(addr, adv.short_name, adv)
        elif adv.complete_name and adv.complete_name.startswith("Kegtron"):
            add_new_dev(addr, adv.complete_name, adv)

    if(addr in kegtron_devices.keys()):
        kegtron_devices[addr]["rssi"] = adv.rssi
        kegtron_devices[addr]["last_advertisement_timestamp_utc"] = utcnow_aware()
        raw_data = bytes(adv)
        LOG.debug(f'Raw Data: {raw_data}')
        try:
            raw_data = raw_data[0:31]
            parsed_data = kegtron_parser.parse(raw_data)
        except Exception as ex:
            LOG.error(f'Failed to parse Kegtron data: Error: {ex.message}, Data: {raw_data}')
            return
        
        kegtron_devices[addr]["model"] = parsed_data["model"]
        kegtron_devices[addr]["port_cnt"] = parsed_data["port_cnt"]
        
        port_data = parsed_data["port_data"]
        kegtron_devices[addr]["ports"][port_data["port_index"]] = port_data

        update_device(kegtron_devices[addr], port_data, raw_data)

        LOG.debug(kegtron_devices[addr])

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

    ble = BLERadio()
    try:
        LOG.info("Starting scanner...")
        for advertisement in ble.start_scan(ProvideServicesAdvertisement, Advertisement):
            on_adv(advertisement)

    except KeyboardInterrupt:
        LOG.info("Stopping scanner..")
        ble.stop_scan()
        LOG.info("Scanner stopped!")
        sys.exit()
