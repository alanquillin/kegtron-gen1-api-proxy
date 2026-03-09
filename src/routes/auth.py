"""
Authentication router for FastAPI.
Handles login, logout, and Google OAuth flows.
"""

import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_async_db
from db.users import User as UsersDB
from lib import logging
from lib.config import Config

router = APIRouter(tags=["auth"], include_in_schema=False)
CONFIG = Config()
LOGGER = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    """Request model for password-based login"""

    email: str
    password: str


@router.post("/login")
async def login(request: Request, login_data: LoginRequest, db_session: AsyncSession = Depends(get_async_db)):
    """
    Password-based login endpoint.
    Sets session cookie on successful authentication.
    """
    user = await UsersDB.get_by_email(db_session, login_data.email)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")

    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user does not have a password set. Please try logging in with google.",
        )

    ph = PasswordHasher()
    try:
        if not ph.verify(user.password_hash, login_data.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")
    except VerifyMismatchError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized") from e

    # Set session cookie (replaces Flask-Login's login_user)
    request.session["user_id"] = str(user.id)
    LOGGER.info("User logged in: %s", user.email)

    return True


@router.get("/logout")
async def logout(request: Request):
    """
    Logout endpoint.
    Clears session and redirects to login page.
    """
    request.session.clear()
    return RedirectResponse(url="/login.html")
