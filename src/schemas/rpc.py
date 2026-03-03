from typing import Optional
from pydantic import BaseModel, Field

from schemas import CamelCaseModel
class ResetVolumeRequest(CamelCaseModel):
    keg_size: Optional[float] = Field(None, description="Volume size")
    start_volume: Optional[float] = Field(None, description="Starting volume")
    unit: Optional[str] = Field("mL", description="The unit for the keg_size and start volume values.  Must be one of: [gal, mL, L, oz]")
