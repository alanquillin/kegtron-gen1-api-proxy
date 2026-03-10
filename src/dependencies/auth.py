"""
Authentication dependencies for FastAPI.
Replaces Flask-Login functionality with FastAPI dependency injection.
"""

import base64
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_async_db
from db.service_accounts import ServiceAccount as ServiceAccountDB
from db.users import User as UsersDB
from lib import logging
from lib.config import Config

CONFIG = Config()
LOGGER = logging.getLogger(__name__)

# Create security scheme for optional Bearer token
security = HTTPBearer(auto_error=False)


class AuthUser:
    """
    FastAPI version of AuthUser (replaces Flask-Login's UserMixin).
    Represents an authenticated user with their permissions.
    """

    def __init__(self, id_, first_name, last_name, email, profile_pic, api_key, admin, service_account, service_name):
        self.id = id_
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.profile_pic = profile_pic
        self.api_key = api_key
        self.admin = admin
        self.is_authenticated = True
        self.service_account = service_account
        self.service_name = service_name

    @staticmethod
    async def from_user(user):
        """Create AuthUser from database User model"""
        if not user:
            return None

        return AuthUser(user.id, user.first_name, user.last_name, user.email, user.profile_pic, user.api_key, user.admin, False, None)

    @staticmethod
    async def from_service_account(service_account):
        """Create AuthUser from database User model"""
        if not service_account:
            return None

        return AuthUser(service_account.id, None, None, None, None, service_account.api_key, False, True, service_account.name)


async def get_current_user_from_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None,
    db: AsyncSession = Depends(get_async_db),
) -> Optional[AuthUser]:
    """
    Check for API key authentication via Bearer token or query parameter.
    Returns AuthUser if valid API key found, None otherwise.
    """
    api_key = None

    # Try query param first (?api_key=...)
    if request:
        api_key = request.query_params.get("api_key")

    LOGGER.debug("api_key present: %s", bool(api_key))
    LOGGER.debug("credentials present: %s", bool(credentials))
    # Try Bearer token from Authorization header
    if not api_key and credentials:
        api_key = credentials.credentials

        # Try base64 decode (some clients send base64-encoded keys)
        if api_key:
            try:
                LOGGER.debug("Attempting base64 decode of API key")
                api_key = base64.b64decode(api_key).decode("ascii")
            except Exception:
                # If decode fails, use the key as-is
                pass

    if api_key:
        user = await UsersDB.get_by_api_key(db, api_key)
        if user:
            LOGGER.debug("Authenticated user via API key: %s", user.email)
            return await AuthUser.from_user(user)
        else:
            user = await ServiceAccountDB.get_by_api_key(db, api_key)
            if user:
                LOGGER.debug("Authenticated service account via API key: %s", user.api_key)
                return await AuthUser.from_service_account(user)

    return None


async def get_current_user_from_session(request: Request, db: AsyncSession = Depends(get_async_db)) -> Optional[AuthUser]:
    """
    Check for session-based authentication (cookie).
    Returns AuthUser if valid session found, None otherwise.
    """
    user_id = request.session.get("user_id")

    if user_id:
        user = await UsersDB.get(user_id, db)
        if user:
            LOGGER.debug("Authenticated user via session: %s", user.email)
            return await AuthUser.from_user(user)

    return None


async def get_optional_user(
    api_key_user: Optional[AuthUser] = Depends(get_current_user_from_api_key),
    session_user: Optional[AuthUser] = Depends(get_current_user_from_session),
) -> Optional[AuthUser]:
    """
    Try API key authentication first, then session authentication.
    Returns AuthUser if authenticated by either method, None otherwise.
    This dependency does NOT raise an error if no authentication is found.
    """
    return api_key_user or session_user


async def require_user(user: Optional[AuthUser] = Depends(get_optional_user)) -> AuthUser:
    """
    Require authentication - raises 401 if not authenticated.
    This is the FastAPI equivalent of Flask-Login's @login_required decorator.

    Usage in router:
        @router.get("/protected")
        async def protected_endpoint(current_user: AuthUser = Depends(require_user)):
            return {"user": current_user.email}
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized. Please login first.",
        )
    return user


async def require_admin(user: AuthUser = Depends(require_user)) -> AuthUser:
    """
    Require admin role - raises 403 if not admin.
    This is the FastAPI equivalent of the @requires_admin decorator.

    Usage in router:
        @router.get("/admin-only")
        async def admin_endpoint(current_user: AuthUser = Depends(require_admin)):
            return {"admin": True}
    """
    if not user.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource.",
        )
    return user
