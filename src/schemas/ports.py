from typing import Any, Dict

from pydantic import BaseModel, Field

from schemas import CamelCaseModel


class PortUpdateFromDevice(CamelCaseModel):
    keg_size: float = Field(None, description="Size of keg (in mL)")
    start_volume: float = Field(None, description="Start volume (in mL)")
    volume_dispensed: float = Field(None, description="The amount of volume dispensed (in mL)")
    port_name: str = Field(None, description="Name of port")
    last_update_timestamp_utc: str = Field(None, description="Timestampo for last update to port values (or forced)")
    configured: bool = Field(None, description="Is Port configured")
    port_index: int = Field(None, description="Port index")


class PortUpdate(CamelCaseModel):
    display_unit: str = Field(None, description="Display unit")
    port_name: str = Field(None, description="Name of port")
    keg_size: float = Field(None, description="Size of keg (in mL)")
    start_volume: float = Field(None, description="Start volume (in mL)")
    volume_dispensed: float = Field(None, description="The amount of volume dispensed (in mL)")
