from typing import Dict, Any
from pydantic import BaseModel, Field

from schemas import CamelCaseModel
from schemas.ports import PortUpdateFromDevice

class DeviceBase(CamelCaseModel):
    mac: str = Field(None, description="Device MAC address")
    name: str = Field(None, description="Device name")
    model: str = Field(None, description="Device model")
    port_cnt: int = Field(None, description="Port count")
    rssi: int = Field(None, description="RSSI value")
    last_advertisement_timestamp_utc: str = Field(None, description="Last advertisement timestamp")
    ports: Dict[int, PortUpdateFromDevice] = Field(default_factory=dict, description="Device ports")

class DeviceCreate(DeviceBase):
    id: str = Field(..., description="Device ID")

class DeviceUpdate(DeviceBase):
    pass