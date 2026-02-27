import argparse
import os
import sys

from lib import logging
from lib.config import Config

# Initialize configuration
CONFIG = Config(config_files=["default.json", "api.default.json"], env_prefix="KENGTRON_PROXY")

# Initialize logging
logging.init(config=CONFIG, fmt=logging.DEFAULT_LOG_FMT)

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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lib.json import KegtronProxyJsonEncoder
from routes import internal, public, rpc, devices

app = FastAPI(
    title="Kegtron V1 API Proxy"
)

@app.on_event("startup")
async def startup_event():
    logging.info("Starting API service")
    # Initialize database tables
    from db import init_db
    await init_db()
    logging.info("Database initialized")

@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Shutting down API service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.config = CONFIG

app.include_router(internal.router, prefix="/api/internal/v1")
app.include_router(devices.router, prefix="/api/v1/devices")
app.include_router(public.router, prefix="/api/v1")
app.include_router(rpc.router, prefix="/api/v1")

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

    logger = logging.getLogger(__name__)
    logger.debug("config: %s", CONFIG.data_flat)
    logger.info("Serving on %s:%s", host, port)
    
    try:
        uvicorn.run(
            "api:app",
            host=host,
            port=port,
            log_level=args.loglevel.lower(),
            reload=False
        )
    except KeyboardInterrupt:
        logger.info("User interrupted - Goodbye")
        sys.exit()