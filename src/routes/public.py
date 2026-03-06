from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_async_db
from db.devices import Device as deviceDB

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health():
    return "We are up and running!"


@router.get("/ping")
async def ping():
    return "pong"
