from typing import Dict, Any
from pydantic import BaseModel, Field

from schemas import CamelCaseModel

class PortUpdate(CamelCaseModel):
    display_unit: str = Field(None, description="Display unit")
