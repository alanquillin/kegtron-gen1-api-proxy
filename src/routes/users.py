"""Users router for FastAPI"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_async_db
from db.users import User as UsersDB
from dependencies.auth import AuthUser, require_admin, require_user
from lib import logging
from schemas.users import UserCreate, UserUpdate
from services.users import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])
LOGGER = logging.getLogger(__name__)


@router.get("/current", response_model=dict)
async def get_current_user(current_user: AuthUser = Depends(require_user), db: AsyncSession = Depends(get_async_db)):
    """Get current authenticated user"""
    if current_user.service_account:
        raise HTTPException(status_code=404, detail="User not found")

    user = await UsersDB.get(current_user.id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return await UserService.transform_response(user, current_user)


@router.get("", response_model=List[dict])
async def list_users(current_user: AuthUser = Depends(require_admin), db: AsyncSession = Depends(get_async_db)):
    """List all users (admin only)"""
    users = await UsersDB.query(db)
    return [await UserService.transform_response(u, current_user) for u in users]


@router.post("", response_model=dict, status_code=201)
async def create_user(
    user_data: UserCreate,
    current_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new user (admin only)"""
    data = user_data.model_dump(exclude_unset=True)
    LOGGER.debug("Creating user with: %s", data)

    user = await UsersDB.create(db, **data)
    return await UserService.transform_response(user, current_user)


@router.get("/{user_id}", response_model=dict)
async def get_user(
    user_id: str,
    current_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific user (admin only)"""
    user = await UsersDB.get(user_id, db)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return await UserService.transform_response(user, current_user)


@router.patch("/{user_id}", response_model=dict)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: AuthUser = Depends(require_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update a user"""
    # Users can only update themselves unless they're admin
    if user_id != str(current_user.id) and not current_user.admin:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    user = await UsersDB.get(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    data = user_data.model_dump(exclude_unset=True)

    # Non-admins cannot change admin status
    if "admin" in data and not current_user.admin:
        del data["admin"]

    # Handle password change with verification
    if "password" in data:
        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError

        # Non-admin changing own password, or admin not in play: verify current password when one exists
        if user_id == str(current_user.id) or not current_user.admin:
            if user.password_hash:
                # User has an existing password: require and verify current_password
                if not data.get("current_password"):
                    raise HTTPException(status_code=400, detail="Current password required to change password")
                ph = PasswordHasher()
                try:
                    ph.verify(user.password_hash, data["current_password"])
                except VerifyMismatchError:
                    raise HTTPException(status_code=401, detail="Current password is incorrect")  # pylint: disable=raise-missing-from
            # else: no existing password — allow setting password without current_password (user already authenticated)

        # Hash the new password
        ph = PasswordHasher()
        data["password_hash"] = ph.hash(data["password"])
        del data["password"]

    # Remove current_password from update data if present
    if "current_password" in data:
        del data["current_password"]

    LOGGER.debug("Updating user %s with data: %s", user_id, data)

    if data:
        await user.update(db, **data)
        await db.refresh(user)

    return await UserService.transform_response(user, current_user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    current_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a user (admin only)"""
    user = await UsersDB.get(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await user.delete(db)
    return


@router.get("/{user_id}/api_key", response_model=dict)
async def get_user_api_key(
    user_id: str,
    current_user: AuthUser = Depends(require_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get user's API key"""
    # Users can only get their own API key unless they're admin
    if user_id != str(current_user.id) and not current_user.admin:
        raise HTTPException(status_code=403, detail="Not authorized to view this API key")

    user = await UsersDB.get(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"apiKey": user.api_key}


@router.post("/{user_id}/api_key/generate", response_model=dict)
async def generate_user_api_key(
    user_id: str,
    current_user: AuthUser = Depends(require_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Generate a new API key for user"""
    # Users can only generate their own API key unless they're admin
    if user_id != str(current_user.id) and not current_user.admin:
        raise HTTPException(status_code=403, detail="Not authorized to generate API key for this user")

    user = await UsersDB.get(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate new API key
    new_api_key = str(uuid.uuid4())
    await user.update(db, api_key=new_api_key)

    return {"apiKey": new_api_key}


@router.delete("/{user_id}/api_key")
async def delete_user_api_key(
    user_id: str,
    current_user: AuthUser = Depends(require_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete user's API key"""
    # Users can only delete their own API key unless they're admin
    if user_id != str(current_user.id) and not current_user.admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete API key for this user")

    user = await UsersDB.get(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await user.update(db, api_key=None)
    return True
