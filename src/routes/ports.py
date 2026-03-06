from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_async_db
from db.ports import Port
from db.ports import Port as portsDB
from lib import logging
from lib.config import Config
from schemas.ports import PortUpdate

LOGGER = logging.getLogger(__name__)
CONFIG = Config()

router = APIRouter(prefix="/api/v1/devices/{device_id}/ports")


@router.patch("/{port_index}")
async def update_device(device_id: str, port_index: int, port_data: PortUpdate, db: AsyncSession = Depends(get_async_db)):
    port = await Port.get_by_device_id_and_index(device_id, port_index, db)

    if not port:
        raise HTTPException(status_code=404, detail=f"Port with index {port_index} for device {device_id} not found")

    data = port_data.model_dump(exclude_unset=True)
    if "display_unit" in data:
        display_unit = data["display_unit"]
        if display_unit not in ["gal", "ml", "mL", "l", "L", "oz"]:
            raise HTTPException(status_code=404, detail=f"Invalid display unit '{display_unit}'.  Must be one of: [gal, mL, L, oz]")
        if display_unit == "ml":
            data["display_unit"] = "mL"
        elif display_unit == "l":
            data["display_unit"] = "L"

    LOGGER.debug("Updating port with index %s, on device %s with data: %s", port_index, device_id, data)
    await port.update(db, **data)

    return {"updated": True}
