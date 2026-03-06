import asyncio
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Create a temporary static directory for testing
import os
import shutil
import atexit

temp_static = tempfile.mkdtemp()

# Cleanup temp dir on exit
def cleanup_temp():
    if os.path.exists(temp_static):
        shutil.rmtree(temp_static)
atexit.register(cleanup_temp)

# Mock the config before importing api
with patch.dict(os.environ, {'KEGTRON_PROXY_STATIC_FILES_DIR': temp_static}):
    from lib.config import Config
    
    # Monkey patch get_static_dir to use temp directory
    import api as api_module
    api_module.DEFAULT_STATIC_DIR = temp_static
    
    from api import api
    from db import Base, get_async_db


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_db_session():
    """Create an async in-memory database session for testing."""
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(
        engine, 
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()
    
    await engine.dispose()


@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    config = MagicMock()
    
    # Set specific config values needed for API
    def config_get_side_effect(key, default=None):
        config_values = {
            "ENV": "test",
            "STATIC_FILES_DIR": temp_static,
            "default_display_unit": "mL",
            "api.registration_allow_origins": ["http://localhost:3000"]
        }
        return config_values.get(key, default)
    
    config.get = MagicMock(side_effect=config_get_side_effect)
    config.get_int = MagicMock(return_value=0)
    config.get_bool = MagicMock(return_value=False)
    config.get_list = MagicMock(return_value=[])
    
    return config


@pytest.fixture
async def client(async_db_session, mock_config):
    """Create a test client with mocked dependencies."""
    from httpx import ASGITransport
    
    async def override_get_db():
        yield async_db_session
    
    api.dependency_overrides[get_async_db] = override_get_db
    
    # Mock the config
    with patch('api.CONFIG', mock_config):
        with patch('routes.devices.CONFIG', mock_config):
            with patch('routes.ports.CONFIG', mock_config):
                with patch('routes.rpc.CONFIG', mock_config):
                    transport = ASGITransport(app=api)
                    async with AsyncClient(transport=transport, base_url="http://test") as ac:
                        yield ac
    
    api.dependency_overrides.clear()


@pytest.fixture
def sync_client(mock_config):
    """Create a synchronous test client for simple tests."""
    with patch('api.CONFIG', mock_config):
        with patch('routes.devices.CONFIG', mock_config):
            with patch('routes.ports.CONFIG', mock_config):
                with patch('routes.rpc.CONFIG', mock_config):
                    client = TestClient(api)
                    yield client


@pytest.fixture
async def sample_device_data():
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


@pytest.fixture
async def sample_device_kt200_data():
    """Sample KT-200 device data for testing."""
    return {
        "id": "test-device-002", 
        "name": "Test Kegtron KT-200",
        "model": "KT-200",
        "mac": "11:22:33:44:55:66",
        "portCnt": 2,
        "ports": {
            "0": {
                "portIndex": 0,
                "portName": "Port 0",
                "kegSize": 19000,
                "startVolume": 19000,
                "volumeDispensed": 500,
                "displayUnit": "mL",
                "configured": True
            },
            "1": {
                "portIndex": 1,
                "portName": "Port 1",
                "kegSize": 38000,
                "startVolume": 38000,
                "volumeDispensed": 1000,
                "displayUnit": "mL",
                "configured": True
            }
        }
    }


@pytest.fixture
def mock_gatt():
    """Mock the GATT module for BLE operations."""
    with patch('routes.rpc.gatt') as mock:
        mock.unlock_all = AsyncMock(return_value=True)
        mock.unlock = AsyncMock(return_value=True)
        mock.reset_volume = AsyncMock(return_value=True)
        mock.update_keg_size = AsyncMock(return_value=True)
        yield mock


@pytest.fixture
def mock_kegtron_parser():
    """Mock the Kegtron parser module."""
    with patch('kegtron.parser') as mock:
        mock.parse = MagicMock()
        mock.parse_scan = MagicMock()
        mock.parse_scan_short = MagicMock()
        yield mock


def convert_device_data_for_db(device_data):
    """Convert API device data to database format.
    
    This helper function converts between API format (camelCase with dict ports)
    and database format (snake_case with list ports).
    
    Args:
        device_data: Device data in API format with camelCase fields
        
    Returns:
        tuple: (db_device_data, db_ports_data) ready for database insertion
    """
    device_copy = device_data.copy()
    ports_data = device_copy.pop("ports", {})
    
    # Convert camelCase to snake_case for database
    db_device_data = {
        "id": device_copy["id"],
        "name": device_copy.get("name"),
        "model": device_copy.get("model"),
        "mac": device_copy["mac"],
        "port_cnt": device_copy.get("portCnt", 1)
    }
    
    db_ports_data = []
    for port_idx, port in ports_data.items():
        db_port_data = {
            "port_index": port["portIndex"],
            "port_name": port.get("portName"),
            "keg_size": port.get("kegSize", 0),
            "start_volume": port.get("startVolume", 0),
            "volume_dispensed": port.get("volumeDispensed", 0),
            "display_unit": port.get("displayUnit", "mL"),
            "configured": port.get("configured", True)
        }
        db_ports_data.append(db_port_data)
    
    return db_device_data, db_ports_data