"""
Integration test fixtures for running tests against a real API server.
These tests validate actual HTTP interactions as external services would experience them.
"""

import asyncio
import os
import sys
import tempfile
import time
from multiprocessing import Process
from pathlib import Path
from typing import Generator, Optional

import pytest
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def wait_for_api(base_url: str, timeout: int = 30) -> bool:
    """Wait for API to be ready to accept requests."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = httpx.get(f"{base_url}/api/v1/health")
            if response.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.ReadError):
            pass
        time.sleep(0.5)
    return False


def run_api_server(port: int, db_url: str, config_dir: str, static_dir: str):
    """Run the API server in a separate process."""
    import os
    import sys
    import uvicorn
    from pathlib import Path
    
    # Extract database path from SQLite URL
    db_path = db_url.replace("sqlite:///", "")
    
    # Set up environment - Use a special test env variable
    os.environ["TEST_DATABASE_PATH"] = db_path
    os.environ["KEGTRON_PROXY_CONFIG_BASE_DIR"] = config_dir
    os.environ["KEGTRON_PROXY_STATIC_FILES_DIR"] = static_dir
    os.environ["KEGTRON_PROXY_ENV"] = "test"
    os.environ["KEGTRON_PROXY_APP_SECRET_KEY"] = "test-secret-key-for-integration-tests"
    os.environ["KEGTRON_PROXY_API_COOKIES_SECURE"] = "False"  # Explicit False string
    
    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    
    # Run migrations to create tables
    from alembic import command
    from alembic.config import Config as AlembicConfig
    
    alembic_cfg = AlembicConfig()
    alembic_cfg.set_main_option("script_location", str(Path(__file__).parent.parent.parent / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")
    
    # Import and configure Config BEFORE importing API
    from lib.config import Config
    config = Config()
    config.setup(env_prefix="KEGTRON_PROXY", config_files=["default.json"], base_dir=config_dir)
    
    # Import API after setting environment and config
    from api import api
    
    # Run the server
    uvicorn.run(
        api,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False
    )


@pytest.fixture(scope="session")
def test_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture(scope="session")
def test_config_dir():
    """Create a temporary config directory for testing."""
    config_dir = tempfile.mkdtemp(prefix="kegtron_test_config_")
    
    # Create a minimal config file
    config_file = os.path.join(config_dir, "default.json")
    with open(config_file, "w") as f:
        # Disable https_only for cookies since tests use HTTP
        import json
        config_data = {
            "ENV": "test",
            "default_display_unit": "mL",
            "app": {
                "secret_key": "test-secret-key"
            },
            "api": {
                "cookies": {
                    "secure": False
                }
            }
        }
        f.write(json.dumps(config_data))
    
    yield config_dir
    
    # Cleanup
    import shutil
    try:
        shutil.rmtree(config_dir)
    except:
        pass


@pytest.fixture(scope="session")
def test_static_dir():
    """Create a temporary static files directory for testing."""
    static_dir = tempfile.mkdtemp(prefix="kegtron_test_static_")
    
    yield static_dir
    
    # Cleanup
    import shutil
    try:
        shutil.rmtree(static_dir)
    except:
        pass


@pytest.fixture(scope="session")
def api_port():
    """Get a port for the test API server."""
    # Use a fixed port for testing - you might want to find a free port dynamically
    return 8765


@pytest.fixture(scope="session")
def api_base_url(api_port):
    """Get the base URL for the test API server."""
    return f"http://127.0.0.1:{api_port}"


@pytest.fixture(scope="session")
def test_db_url(test_db_path):
    """Get the database URL for testing."""
    return f"sqlite:///{test_db_path}"


@pytest.fixture(scope="session")
def api_server_process(api_port, test_db_url, test_config_dir, test_static_dir, api_base_url):
    """Start the API server in a separate process."""
    
    # Start the API server process
    process = Process(
        target=run_api_server,
        args=(api_port, test_db_url, test_config_dir, test_static_dir),
        daemon=True
    )
    process.start()
    
    # Wait for the API to be ready
    if not wait_for_api(api_base_url):
        process.terminate()
        process.join(timeout=5)
        pytest.fail("API server failed to start within timeout")
    
    yield process
    
    # Cleanup
    process.terminate()
    process.join(timeout=10)
    if process.is_alive():
        process.kill()
        process.join()


@pytest.fixture(scope="function")
def db_session(test_db_url, api_server_process):
    """Create a database session for test setup/teardown."""
    # Ensure server has started and created tables via migrations
    _ = api_server_process
    
    engine = create_engine(test_db_url)
    session = Session(engine)
    
    yield session
    
    session.close()
    engine.dispose()


@pytest.fixture(scope="function", autouse=True)
def clean_database(db_session, api_server_process):
    """Clean the database before each test."""
    # Ensure server is running
    _ = api_server_process
    
    # Clean all tables (check if they exist first)
    try:
        db_session.execute(text("DELETE FROM ports"))
        db_session.execute(text("DELETE FROM devices"))
        db_session.execute(text("DELETE FROM service_accounts"))
        db_session.execute(text("DELETE FROM users"))
        db_session.commit()
    except Exception:
        db_session.rollback()
        # Tables might not exist yet, that's ok
    
    yield
    
    # Clean again after test
    try:
        db_session.execute(text("DELETE FROM ports"))
        db_session.execute(text("DELETE FROM devices"))
        db_session.execute(text("DELETE FROM service_accounts"))
        db_session.execute(text("DELETE FROM users"))
        db_session.commit()
    except:
        db_session.rollback()


@pytest.fixture
def api_client(api_base_url, api_server_process):
    """Create an HTTP client for testing the API."""
    # Ensure server is running
    _ = api_server_process
    
    with httpx.Client(base_url=api_base_url, timeout=10.0) as client:
        yield client


@pytest.fixture
async def async_api_client(api_base_url, api_server_process):
    """Create an async HTTP client for testing the API."""
    # Ensure server is running
    _ = api_server_process
    
    # Create client with cookie jar support
    async with httpx.AsyncClient(
        base_url=api_base_url, 
        timeout=10.0,
        follow_redirects=False,  # Don't auto-follow redirects (causes issues with POST to logout)
        cookies=httpx.Cookies()  # Explicitly create a cookie jar
    ) as client:
        yield client


@pytest.fixture
def create_test_user(db_session):
    """Factory fixture to create test users in the database."""
    def _create_user(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        api_key="test-api-key",
        admin=False
    ):
        from db.users import User
        from argon2 import PasswordHasher
        
        ph = PasswordHasher()
        password_hash = ph.hash("password123")  # Default password for test users
        
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            api_key=api_key,
            admin=admin,
            password_hash=password_hash
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    return _create_user


@pytest.fixture
def create_test_service_account(db_session):
    """Factory fixture to create test service accounts in the database."""
    def _create_service_account(
        name="Test Service",
        api_key="service-api-key"
    ):
        from db.service_accounts import ServiceAccount
        
        account = ServiceAccount(
            name=name,
            api_key=api_key
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        return account
    
    return _create_service_account


@pytest.fixture
def test_user(create_test_user):
    """Create a regular test user."""
    return {
        "id": create_test_user().id,
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "api_key": "test-api-key",
        "admin": False
    }


@pytest.fixture
def admin_user(create_test_user):
    """Create an admin test user."""
    admin = create_test_user(
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        api_key="admin-api-key",
        admin=True
    )
    return {
        "id": admin.id,
        "email": admin.email,
        "first_name": admin.first_name,
        "last_name": admin.last_name,
        "api_key": admin.api_key,
        "admin": admin.admin
    }


@pytest.fixture
def test_service_account(create_test_service_account):
    """Create a test service account."""
    account = create_test_service_account()
    return {
        "id": account.id,
        "name": account.name,
        "api_key": account.api_key
    }


@pytest.fixture
def create_test_device(db_session):
    """Factory fixture to create test devices in the database."""
    def _create_device(
        device_id="test-device-001",
        name="Test Device",
        model="KT-100",
        mac="AA:BB:CC:DD:EE:FF",
        port_cnt=1,
        ports=None
    ):
        from db.devices import Device
        from db.ports import Port
        
        device = Device(
            id=device_id,
            name=name,
            model=model,
            mac=mac,
            port_cnt=port_cnt
        )
        db_session.add(device)
        db_session.commit()
        db_session.refresh(device)
        
        # Create ports if provided
        if ports:
            for port_data in ports:
                port = Port(
                    device_id=device.id,
                    **port_data
                )
                db_session.add(port)
            db_session.commit()
        
        return device
    
    return _create_device


@pytest.fixture
def sample_device_data():
    """Sample device data for testing."""
    return {
        "id": "test-device-001",
        "name": "Test Kegtron",
        "model": "KT-100",
        "mac": "AA:BB:CC:DD:EE:FF",
        "portCnt": 1,
        "ports": {
            "0": {
                "portIndex": 0,
                "portName": "Test Port",
                "kegSize": 19000,
                "startVolume": 19000,
                "volumeDispensed": 0,
                "displayUnit": "mL",
                "configured": True
            }
        }
    }