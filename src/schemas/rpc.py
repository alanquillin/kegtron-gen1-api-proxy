from typing import Optional

from pydantic import Field

from schemas import CamelCaseModel


class ResetVolumeRequest(CamelCaseModel):
    keg_size: Optional[float] = Field(None, description="Volume size")
    start_volume: Optional[float] = Field(None, description="Starting volume")
    unit: Optional[str] = Field("mL", description="The unit for the keg_size and start volume values.  Must be one of: [gal, mL, L, oz]")

class SetPortNameRequest(CamelCaseModel):
    name: str = Field(..., description="Name of port")

class SetKegSizeRequest(CamelCaseModel):
    keg_size: float = Field(..., description="Size of keg (in mL)")
    unit: Optional[str] = Field("mL", description="The unit for the keg_size value.  Must be one of: [gal, mL, L, oz]")

class SetStartVolumeRequest(CamelCaseModel):
    start_volume: float = Field(..., description="Starting volume (in mL)")
    unit: Optional[str] = Field("mL", description="The unit for the start_volume value.  Must be one of: [gal, mL, L, oz]")