# Initialize configuration *NEEDS TO BE DONE BEFORE ALL OTHER IMPORTS*
from lib.config import Config

CONFIG = Config(config_files=["default.json"], env_prefix="KEGTRON_PROXY")

# Initialize logging *NEEDS TO BE DONE BEFORE ALL OTHER IMPORTS*
from lib import logging

logging.init(config=CONFIG, fmt=logging.DEFAULT_LOG_FMT)
LOGGER = logging.getLogger(__name__)


LOGGER.debug(CONFIG.data_flat)

import argparse
import asyncio
import os
import sys

import uvicorn

import scan as kegtron_ble_scanner
from api import api

# Global application instance for access from other modules
app_instance = None


class Application:
    """Main application class"""

    def __init__(self, log_level: str = "INFO"):
        self.scanner_task = None
        self.http_server = None
        self.scanner = None
        self.log_level = log_level
        self.shutdown_event = asyncio.Event()
        self.scanner_restart_delay = 5  # seconds to wait before restarting scanner

    # async def initialize_first_user(self):
    #     """Create initial user if no users exist"""
    #     from db import async_session_scope
    #     from db.users import Users as UsersDB

    #     async with async_session_scope(CONFIG) as db_session:
    #         users = await UsersDB.query(db_session)

    #         if not users:
    #             init_user_email = CONFIG.get("auth.initial_user.email")
    #             set_init_user_pass = CONFIG.get("auth.initial_user.set_password")
    #             init_user_fname = CONFIG.get("auth.initial_user.first_name")
    #             init_user_lname = CONFIG.get("auth.initial_user.last_name")
    #             google_sso_enabled = CONFIG.get("auth.oidc.google.enabled")

    #             if not google_sso_enabled and not set_init_user_pass:
    #                 LOGGER.error("Cannot create an initial user! auth.initial_user.set_password and google authentication is disabled!")
    #                 sys.exit(1)

    #             data = {"email": init_user_email, "admin": True}
    #             if init_user_fname:
    #                 data["first_name"] = init_user_fname
    #             if init_user_lname:
    #                 data["last_name"] = init_user_lname

    #             LOGGER.info("No users exist, creating initial user: %s", data)
    #             if set_init_user_pass:
    #                 data["password"] = CONFIG.get("auth.initial_user.password")
    #                 LOGGER.warning("Creating initial user with a pre-configured password.")
    #                 LOGGER.warning("PLEASE REMEMBER TO LOG IN AND CHANGE IT ASAP!!")

    #             await UsersDB.create(db_session, **data)

    def get_scanner_status(self):
        """Get the current scanner status for health checks"""
        if not CONFIG.get("scanner.enabled"):
            return {"status": "disabled", "message": "Scanner is disabled in configuration"}
        
        if not self.scanner_task:
            return {"status": "not_started", "message": "Scanner task not initialized"}
        
        if self.scanner_task.done():
            if self.scanner_task.cancelled():
                return {"status": "cancelled", "message": "Scanner task was cancelled"}
            
            try:
                # Check if task completed with an exception
                self.scanner_task.result()
                return {"status": "stopped", "message": "Scanner task completed normally"}
            except Exception as e:
                return {"status": "failed", "message": f"Scanner task failed: {str(e)}"}
        
        return {"status": "running", "message": "Scanner is running normally"}
    
    async def start_scanner(self):
        """Start the BLE scanner with automatic restart on failure"""
        async def scanner_with_restart():
            """Inner function to handle scanner restarts"""
            consecutive_failures = 0
            max_consecutive_failures = 5
            
            while not self.shutdown_event.is_set():
                try:
                    LOGGER.info("Starting BLE scanner...")
                    await kegtron_ble_scanner.scan()
                    consecutive_failures = 0  # Reset on successful completion
                except asyncio.CancelledError:
                    LOGGER.info("Scanner task cancelled")
                    break
                except Exception as e:
                    consecutive_failures += 1
                    LOGGER.error(
                        "Scanner crashed (failure %d/%d): %s", 
                        consecutive_failures, 
                        max_consecutive_failures,
                        e,
                        exc_info=True
                    )
                    
                    if consecutive_failures >= max_consecutive_failures:
                        LOGGER.critical(
                            "Scanner failed %d times consecutively. Stopping restart attempts.",
                            max_consecutive_failures
                        )
                        break
                    
                    # Wait before restarting, with exponential backoff
                    wait_time = min(self.scanner_restart_delay * (2 ** (consecutive_failures - 1)), 60)
                    LOGGER.info("Restarting scanner in %d seconds...", wait_time)
                    
                    try:
                        await asyncio.wait_for(
                            self.shutdown_event.wait(),
                            timeout=wait_time
                        )
                        # If we get here, shutdown was requested
                        break
                    except asyncio.TimeoutError:
                        # Normal case - continue to restart
                        pass
        
        self.scanner_task = asyncio.create_task(scanner_with_restart())

    async def start_http_server(self):
        """Start the HTTP/WebSocket server"""
        host = CONFIG.get("api.host", "localhost")
        port = CONFIG.get("api.port", 8080)
        LOGGER.info("Serving API on %s:%d", host, port)

        config = uvicorn.Config(
            app=api,
            host=host,
            port=port,
            log_level=self.log_level.lower(),
            log_config=None,  # Disable uvicorn's default logging config; use our root logger
            proxy_headers=True,  # Handle X-Forwarded-* headers (replaces ProxyFix)
            forwarded_allow_ips=CONFIG.get("api.forwarded_allow_ips", "*"),
            reload=CONFIG.get("ENV") == "development",  # Auto-reload in development
        )
        self.http_server = uvicorn.Server(config)
        await self.http_server.serve()

    async def run(self):
        """Main application entry point.
        
        Initializes and starts all application components:
        - Starts the BLE scanner if enabled
        - Starts the HTTP/WebSocket server
        - Handles graceful shutdown on cancellation
        
        The method runs until interrupted (Ctrl+C) or cancelled.
        """
        # Initialize first user if needed
        # LOGGER.info("Checking for initial user...")
        # await self.initialize_first_user()

        scanner_enabled = CONFIG.get("scanner.enabled")
        if scanner_enabled:
            LOGGER.info("Starting the Kegtron BLE Scanner...")
            await self.start_scanner()

        try:
            await self.start_http_server()
        except asyncio.CancelledError:
            LOGGER.info("Application shutting down...")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Gracefully shutdown all application components.
        
        This method:
        - Sets the shutdown event to signal all tasks to stop
        - Cancels the scanner task and waits for it to complete
        - Logs the shutdown process for debugging
        
        Should be called when the application is terminating to ensure
        proper cleanup of resources.
        """
        LOGGER.info("Shutting down application...")
        
        # Signal shutdown to all tasks
        self.shutdown_event.set()

        if self.scanner_task:
            self.scanner_task.cancel()
            try:
                await self.scanner_task
            except asyncio.CancelledError:
                pass
            LOGGER.info("Scanner task shutdown complete")

        LOGGER.info("Application shutdown complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--log",
        dest="loglevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.environ.get("LOG_LEVEL", logging.get_def_log_level(CONFIG)).upper(),
        help="Set the logging level",
    )
    args = parser.parse_args()

    # Update logging level
    logging_level = logging.get_log_level(args.loglevel)
    logging.set_log_level(logging_level)

    # Create global app instance
    app_instance = Application(log_level=args.loglevel)

    try:
        asyncio.run(app_instance.run())
    except KeyboardInterrupt:
        LOGGER.info("Received keyboard interrupt, shutting down...")
        asyncio.run(app_instance.shutdown())
    except Exception:
        LOGGER.error("Unhandled application error", exc_info=True)
        sys.exit(1)
