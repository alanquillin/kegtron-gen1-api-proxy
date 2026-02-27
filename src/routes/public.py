from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from db.devices import Device as deviceDB
from db import get_async_db

router = APIRouter()

@router.get("/health")
async def health():
    return "We are up and running!"


@router.get("/ping")
async def ping():
    return "pong"
