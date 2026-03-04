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

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes import ports, public, rpc, devices

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

app.include_router(rpc.router_devices)
app.include_router(rpc.router_ports)
app.include_router(devices.router)
app.include_router(ports.router)
app.include_router(public.router)

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