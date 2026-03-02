from db.devices import Device
from lib.units import from_ml

def transform_device(device: Device):
    device_dict = device.to_dict()
    

    if device.ports:
        ports = {str(port.port_index): port.to_dict() for port in device.ports}
        for i, port_dict in ports.items():
            display_unit = port_dict.get("display_unit", "ml")
            if display_unit != "ml":
                port_dict["keg_size"] = from_ml(port_dict.get("keg_size"), display_unit)
                port_dict["volume_dispensed"] = from_ml(port_dict.get("volume_dispensed"), display_unit)
                port_dict["start_volume"] = from_ml(port_dict.get("start_volume"), display_unit)

                ports[i] = port_dict
        device_dict["ports"] = ports

    return device_dict