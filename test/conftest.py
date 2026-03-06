import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_config():
    from lib.config import Config
    config = MagicMock(spec=Config)
    config.get = MagicMock(return_value=None)
    config.get_int = MagicMock(return_value=0)
    config.get_bool = MagicMock(return_value=False)
    config.get_list = MagicMock(return_value=[])
    return config


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.close = AsyncMock()
    return session