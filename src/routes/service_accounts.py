"""Users router for FastAPI"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_async_db
from db.service_accounts import ServiceAccount as ServiceAccountsDB
from dependencies.auth import AuthUser, require_admin, require_user
from lib import logging
from schemas.service_accounts import ServiceAccountCreate, ServiceAccountUpdate
from services.service_accounts import ServiceAccountService

router = APIRouter(prefix="/api/v1/service_accounts", tags=["service_accounts"])
LOGGER = logging.getLogger(__name__)


@router.get("", response_model=List[dict])
async def list_service_accounts(current_user: AuthUser = Depends(require_admin), db: AsyncSession = Depends(get_async_db)):
    """List all service accounts (admin only)"""
    service_accounts = await ServiceAccountsDB.list(db)
    return [await ServiceAccountService.transform_response(s) for s in service_accounts]


@router.post("", response_model=dict, status_code=201)
async def create_service_account(
    service_account_data: ServiceAccountCreate,
    current_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new service account (admin only)"""
    data = service_account_data.model_dump(exclude_unset=True)
    LOGGER.debug("Creating service account with: %s", data)

    if "api_key" not in data:
        data["api_key"] = str(uuid.uuid4())

    service_account = await ServiceAccountsDB.create(db, **data)
    return await ServiceAccountService.transform_response(service_account)


@router.get("/{service_account_id}", response_model=dict)
async def get_service_account(
    service_account_id: str,
    current_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific service account (admin only)"""
    service_account = await ServiceAccountsDB.get(service_account_id, db)

    if not service_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    return await ServiceAccountService.transform_response(service_account)


@router.patch("/{service_account_id}", response_model=dict)
async def update_service_account(
    service_account_id: str,
    service_account_data: ServiceAccountUpdate,
    current_user: AuthUser = Depends(require_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update a service account (admin only)"""
    service_account = await ServiceAccountsDB.get(service_account_id, db)
    if not service_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    data = service_account_data.model_dump(exclude_unset=True)

    if data:
        await service_account.update(db, **data)

    service_account = await ServiceAccountsDB.get(service_account_id, db)
    await db.refresh(service_account)
    return await ServiceAccountService.transform_response(service_account)


@router.delete("/{service_account_id}", status_code=204)
async def delete_service_account(
    service_account_id: str,
    current_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a service account (admin only)"""
    service_account = await ServiceAccountsDB.get(service_account_id, db)
    if not service_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    await service_account.delete(db)
    return True


@router.post("/{service_account_id}/api_key/generate", response_model=dict)
async def generate_service_account_api_key(
    service_account_id: str,
    current_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Generate a new API key for service account"""
    # Users can only generate their own API key unless they're admin
    service_account = await ServiceAccountsDB.get(service_account_id, db)
    if not service_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    # Generate new API key
    new_api_key = str(uuid.uuid4())
    await service_account.update(db, api_key=new_api_key)

    return {"apiKey": new_api_key}


@router.delete("/{service_account_id}/api_key", status_code=204)
async def delete_service_account_api_key(
    service_account_id: str,
    current_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete service account's API key (admin only)"""
    service_account = await ServiceAccountsDB.get(service_account_id, db)
    if not service_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    if not current_user.admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete API key for this service account")

    await service_account.update(db, api_key=None)
    return True
