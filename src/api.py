import argparse
import os
import sys

from lib import logging
from lib.config import Config

# Initialize configuration
CONFIG = Config(config_files=["default.json", "api.default.json"], env_prefix="KEGTRON_PROXY")

# Initialize logging
logging.init(config=CONFIG, fmt=logging.DEFAULT_LOG_FMT)
LOGGER = logging.getLogger(__name__)

# Monkey patch to fix FastAPI/Pydantic compatibility issue with reserved keywords
import inspect
from inspect import Parameter

# Store the original Parameter class
_original_parameter_class = inspect.Parameter

import keyword

class PatchedParameter(_original_parameter_class):
    """Patched Parameter class that allows reserved keywords as parameter names"""
    def __init__(self, name, *args, **kwargs):
        # Replace Python keywords with underscore suffix to avoid conflicts
        if keyword.iskeyword(name):
            name = name + '_'
        super().__init__(name, *args, **kwargs)

# Replace the Parameter class
inspect.Parameter = PatchedParameter

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routes import internal, public, rpc, devices

app = FastAPI(
    title="Kegtron V1 API Proxy"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.config = CONFIG

# Serve static files

DEFAULT_STATIC_DIR = os.path.join(os.getcwd(), "static")

def get_static_dir() -> str:
    static_dir = CONFIG.get("STATIC_FILES_DIR", DEFAULT_STATIC_DIR)
    LOGGER.debug("Static .html files path: %s", static_dir)
    return static_dir

# @app.get("/")
# async def serve_home():
#     """Serve the Angular SPA index.html"""
#     static_dir = CONFIG.get("STATIC_FILES_DIR", DEFAULT_STATIC_DIR)
#     index_path = os.path.join(static_dir, "index.html")
#     LOGGER.debug("Static index.html file path: %s", index_path)
#     if os.path.exists(index_path):
#         return FileResponse(index_path)
#     raise HTTPException(status_code=500, detail="Static files not found")

# @app.get("/home")
# async def serve_home_alt():
#     return await serve_home()

app.include_router(internal.router, prefix="/api/internal/v1")
app.include_router(devices.router, prefix="/api/v1/devices")
app.include_router(public.router, prefix="/api/v1")
app.include_router(rpc.router, prefix="/api/v1")

app.mount("/", StaticFiles(directory=get_static_dir(), html=True), name="static")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-l",
        "--log",
        dest="loglevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.environ.get("LOG_LEVEL", "INFO").upper(),
        help="Set the logging level",
    )
    args = parser.parse_args()

    logging_level = logging.get_log_level(args.loglevel)
    logging.set_log_level(logging_level)

    host = CONFIG.get("api.host", "localhost")
    port = CONFIG.get("api.port", 8000)

    LOGGER.debug("config: %s", CONFIG.data_flat)
    LOGGER.info("Serving on %s:%s", host, port)
    
    try:
        uvicorn.run(
            "api:app",
            host=host,
            port=port,
            log_level=args.loglevel.lower(),
            log_config=None,
            reload=False,
        )
    except KeyboardInterrupt:
        LOGGER.info("User interrupted - Goodbye")
        sys.exit()