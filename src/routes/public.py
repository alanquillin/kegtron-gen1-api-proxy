from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_async_db
from db.devices import Device as deviceDB

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health():
    """Health check endpoint with scanner status"""
    health_status = {
        "status": "healthy",
        "api": "running"
    }
    
    # Try to get scanner status if app instance is available
    try:
        import app
        if hasattr(app, 'app_instance') and app.app_instance:
            health_status["scanner"] = app.app_instance.get_scanner_status()
        else:
            # App module exists but no instance (e.g., in tests)
            health_status["scanner"] = {"status": "not_initialized", "message": "Application instance not available"}
    except ImportError:
        # Running in test environment or standalone API
        health_status["scanner"] = {"status": "unknown", "message": "Running without scanner module"}
    except Exception as e:
        health_status["scanner"] = {"status": "error", "message": str(e)}
    
    return health_status


@router.get("/scanner/status")
async def scanner_status():
    """Get detailed scanner status information"""
    try:
        import app
        if hasattr(app, 'app_instance') and app.app_instance:
            status = app.app_instance.get_scanner_status()
            # Add timestamp
            
            status["checked_at"] = datetime.utcnow().isoformat() + "Z"
            return status
        else:
            return {
                "status": "not_initialized", 
                "message": "Application instance not available",
                "checked_at": datetime.utcnow().isoformat() + "Z"
            }
    except ImportError:
        return {
            "status": "unknown", 
            "message": "Running without scanner module",
            "checked_at": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e),
            "checked_at": datetime.utcnow().isoformat() + "Z"
        }


@router.get("/ping")
async def ping():
    return "pong"
