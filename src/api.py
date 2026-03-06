import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from lib import logging
from lib.config import Config
from routes import ports, public, rpc, devices

CONFIG = Config()
LOGGER = logging.getLogger(__name__)

api = FastAPI(
    title="Kegtron Gen1 API Proxy",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc" if CONFIG.get("ENV") == "development" else None,
)

# CORS middleware
if CONFIG.get("ENV") in ("development", "test"):
    LOGGER.debug("Setting up development/test environment with full CORS")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production - selective CORS
    api.add_middleware(
        CORSMiddleware,
        allow_origins=CONFIG.get("api.registration_allow_origins", []),
        allow_methods=["PUT", "OPTIONS"],
        allow_headers=["Content-Type"],
        expose_headers=["Content-Type"],
        max_age=3000,
        allow_credentials=True,
    )

api.state.config = CONFIG

# Serve static files

DEFAULT_STATIC_DIR = os.path.join(os.getcwd(), "static")

def get_static_dir() -> str:
    static_dir = CONFIG.get("STATIC_FILES_DIR", DEFAULT_STATIC_DIR)
    LOGGER.debug("Static .html files path: %s", static_dir)
    return static_dir

api.include_router(rpc.router_devices)
api.include_router(rpc.router_ports)
api.include_router(devices.router)
api.include_router(ports.router)
api.include_router(public.router)

api.mount("/", StaticFiles(directory=get_static_dir(), html=True), name="static")