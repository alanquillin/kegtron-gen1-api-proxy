"""Test authentication and authorization for API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from db.devices import Device as DeviceDB
from db.ports import Port as PortDB
from db.users import User as UserDB
from db.service_accounts import ServiceAccount as ServiceAccountDB

from .conftest import convert_device_data_for_db


class TestAuthenticationRequired:
    """Test that protected endpoints require authentication."""

    @pytest.mark.asyncio
    async def test_device_update_requires_auth(self, client_no_auth, async_db_session, sample_device_data):
        """Test that updating a device requires authentication."""
        # Create a device first
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        await async_db_session.commit()

        # Try to update without auth - should get 401
        update_data = {"name": "Updated Name"}
        response = await client_no_auth.put(f"/api/v1/devices/{device.id}", json=update_data)
        assert response.status_code == 401
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_device_patch_requires_auth(self, client_no_auth, async_db_session, sample_device_data):
        """Test that patching a device requires authentication."""
        # Create a device first
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        await async_db_session.commit()

        # Try to patch without auth - should get 401
        update_data = {"name": "Updated Name"}
        response = await client_no_auth.patch(f"/api/v1/devices/{device.id}", json=update_data)
        assert response.status_code == 401
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_port_update_requires_auth(self, client_no_auth, async_db_session, sample_device_data):
        """Test that updating a port requires authentication."""
        # Create a device with ports
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()

        # Try to update port without auth - should get 401
        update_data = {"port_name": "Updated Port"}
        response = await client_no_auth.patch(f"/api/v1/devices/{device.id}/ports/0", json=update_data)
        assert response.status_code == 401
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_rpc_unlock_all_requires_auth(self, client_no_auth, async_db_session, sample_device_data):
        """Test that RPC unlock all requires authentication."""
        # Create a device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        await async_db_session.commit()

        # Try to unlock without auth - should get 401
        response = await client_no_auth.post(f"/api/v1/devices/{device.id}/rpc/Kegtron.UnlockWriteAll")
        assert response.status_code == 401
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_rpc_unlock_port_requires_auth(self, client_no_auth, async_db_session, sample_device_data):
        """Test that RPC unlock port requires authentication."""
        # Create a device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        await async_db_session.commit()

        # Try to unlock port without auth - should get 401
        response = await client_no_auth.post(f"/api/v1/devices/{device.id}/ports/0/rpc/Kegtron.UnlockWrite")
        assert response.status_code == 401
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_rpc_reset_volume_requires_auth(self, client_no_auth, async_db_session, sample_device_data):
        """Test that RPC reset volume requires authentication."""
        # Create a device with ports
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()

        # Try to reset volume without auth - should get 401
        request_data = {"kegSize": 19000}
        response = await client_no_auth.post(
            f"/api/v1/devices/{device.id}/ports/0/rpc/Kegtron.ResetVolume",
            json=request_data
        )
        assert response.status_code == 401
        assert "not authorized" in response.json()["detail"].lower()


class TestUserAPIKeyAuthentication:
    """Test authentication using user API keys."""

    @pytest.mark.asyncio
    async def test_user_api_key_bearer_token(self, async_db_session, mock_config, sample_device_data):
        """Test that a valid user API key in Bearer token allows access."""
        from httpx import ASGITransport, AsyncClient
        from api import api
        from db import get_async_db

        # Create a test user with API key
        test_user = await UserDB.create(
            async_db_session,
            email="apiuser@example.com",
            first_name="API",
            last_name="User",
            api_key="user-test-api-key-123",
            admin=False
        )
        await async_db_session.commit()

        # Create a device for testing
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        await async_db_session.commit()

        # Override database dependency
        async def override_get_db():
            yield async_db_session

        api.dependency_overrides[get_async_db] = override_get_db

        # Test with Bearer token
        with patch('api.CONFIG', mock_config):
            with patch('routes.devices.CONFIG', mock_config):
                transport = ASGITransport(app=api)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    # Make request with Bearer token
                    headers = {"Authorization": f"Bearer {test_user.api_key}"}
                    update_data = {"name": "Updated via API Key"}
                    response = await client.patch(
                        f"/api/v1/devices/{device.id}",
                        json=update_data,
                        headers=headers
                    )
                    assert response.status_code == 200

        api.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_user_api_key_query_param(self, async_db_session, mock_config, sample_device_data):
        """Test that a valid user API key as query parameter allows access."""
        from httpx import ASGITransport, AsyncClient
        from api import api
        from db import get_async_db

        # Create a test user with API key
        test_user = await UserDB.create(
            async_db_session,
            email="apiuser2@example.com",
            first_name="API",
            last_name="User2",
            api_key="user-test-api-key-456",
            admin=False
        )
        await async_db_session.commit()

        # Create a device for testing
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()

        # Override database dependency
        async def override_get_db():
            yield async_db_session

        api.dependency_overrides[get_async_db] = override_get_db

        # Test with query parameter
        with patch('api.CONFIG', mock_config):
            with patch('routes.ports.CONFIG', mock_config):
                transport = ASGITransport(app=api)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    # Make request with API key as query param
                    update_data = {"port_name": "Updated Port via API Key"}
                    response = await client.patch(
                        f"/api/v1/devices/{device.id}/ports/0?api_key={test_user.api_key}",
                        json=update_data
                    )
                    assert response.status_code == 200

        api.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_invalid_user_api_key(self, async_db_session, mock_config, sample_device_data):
        """Test that an invalid user API key is rejected."""
        from httpx import ASGITransport, AsyncClient
        from api import api
        from db import get_async_db

        # Create a device for testing
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        await async_db_session.commit()

        # Override database dependency
        async def override_get_db():
            yield async_db_session

        api.dependency_overrides[get_async_db] = override_get_db

        # Test with invalid API key
        with patch('api.CONFIG', mock_config):
            with patch('routes.devices.CONFIG', mock_config):
                transport = ASGITransport(app=api)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    # Make request with invalid Bearer token
                    headers = {"Authorization": "Bearer invalid-api-key"}
                    update_data = {"name": "Should Fail"}
                    response = await client.patch(
                        f"/api/v1/devices/{device.id}",
                        json=update_data,
                        headers=headers
                    )
                    assert response.status_code == 401

        api.dependency_overrides.clear()


class TestServiceAccountAPIKeyAuthentication:
    """Test authentication using service account API keys."""

    @pytest.mark.asyncio
    async def test_service_account_api_key_bearer_token(self, async_db_session, mock_config, sample_device_data):
        """Test that a valid service account API key in Bearer token allows access."""
        from httpx import ASGITransport, AsyncClient
        from api import api
        from db import get_async_db

        # Create a test service account with API key
        service_account = await ServiceAccountDB.create(
            async_db_session,
            name="Test Service",
            api_key="service-test-api-key-789"
        )
        await async_db_session.commit()

        # Create a device for testing
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        await async_db_session.commit()

        # Override database dependency
        async def override_get_db():
            yield async_db_session

        api.dependency_overrides[get_async_db] = override_get_db

        # Test with Bearer token
        with patch('api.CONFIG', mock_config):
            with patch('routes.devices.CONFIG', mock_config):
                transport = ASGITransport(app=api)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    # Make request with Bearer token
                    headers = {"Authorization": f"Bearer {service_account.api_key}"}
                    update_data = {"name": "Updated via Service Account"}
                    response = await client.patch(
                        f"/api/v1/devices/{device.id}",
                        json=update_data,
                        headers=headers
                    )
                    assert response.status_code == 200

        api.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_service_account_api_key_query_param(self, async_db_session, mock_config, sample_device_data, mock_gatt):
        """Test that a valid service account API key as query parameter allows access."""
        from httpx import ASGITransport, AsyncClient
        from api import api
        from db import get_async_db

        # Create a test service account with API key
        service_account = await ServiceAccountDB.create(
            async_db_session,
            name="Test Service 2",
            api_key="service-test-api-key-abc"
        )
        await async_db_session.commit()

        # Create a device for testing
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        await async_db_session.commit()

        # Override database dependency
        async def override_get_db():
            yield async_db_session

        api.dependency_overrides[get_async_db] = override_get_db

        # Test with query parameter on RPC endpoint
        with patch('api.CONFIG', mock_config):
            with patch('routes.rpc.CONFIG', mock_config):
                with patch('routes.rpc.gatt', mock_gatt):
                    transport = ASGITransport(app=api)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        # Make request with API key as query param
                        response = await client.post(
                            f"/api/v1/devices/{device.id}/rpc/Kegtron.UnlockWriteAll?api_key={service_account.api_key}"
                        )
                        assert response.status_code == 200
                        mock_gatt.unlock_all.assert_called_once()

        api.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_service_account_cannot_access_admin_endpoints(self, async_db_session, mock_config):
        """Test that service accounts cannot access admin endpoints."""
        from httpx import ASGITransport, AsyncClient
        from api import api
        from db import get_async_db

        # Create a regular service account
        service_account = await ServiceAccountDB.create(
            async_db_session,
            name="Regular Service",
            api_key="service-key-123"
        )
        await async_db_session.commit()

        # Override database dependency
        async def override_get_db():
            yield async_db_session

        api.dependency_overrides[get_async_db] = override_get_db

        # Test accessing admin endpoint (users list)
        with patch('api.CONFIG', mock_config):
            transport = ASGITransport(app=api)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                headers = {"Authorization": f"Bearer {service_account.api_key}"}
                response = await client.get("/api/v1/users", headers=headers)
                # Service accounts cannot access admin endpoints
                assert response.status_code == 403

        api.dependency_overrides.clear()


class TestMixedAuthentication:
    """Test various authentication scenarios."""

    @pytest.mark.asyncio
    async def test_public_endpoints_no_auth(self, client_no_auth, async_db_session, sample_device_data):
        """Test that public endpoints work without authentication."""
        # Create a device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()

        # These should work without auth
        response = await client_no_auth.get("/api/v1/devices")
        assert response.status_code == 200

        response = await client_no_auth.get(f"/api/v1/devices/{device.id}")
        assert response.status_code == 200


    @pytest.mark.asyncio
    async def test_session_auth_preferred_over_api_key(self, async_db_session, mock_config, sample_device_data):
        """Test that when both session and API key are present, the system handles it correctly."""
        from httpx import ASGITransport, AsyncClient
        from api import api
        from db import get_async_db
        from starlette.middleware.sessions import SessionMiddleware

        # Create two users
        api_user = await UserDB.create(
            async_db_session,
            email="apiuser@example.com",
            first_name="API",
            last_name="User",
            api_key="api-key-user",
            admin=False
        )
        
        session_user = await UserDB.create(
            async_db_session,
            email="sessionuser@example.com",
            first_name="Session",
            last_name="User",
            api_key="session-key-user",
            admin=False
        )
        await async_db_session.commit()

        # Create a device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        await async_db_session.commit()

        # Override database dependency
        async def override_get_db():
            yield async_db_session

        api.dependency_overrides[get_async_db] = override_get_db

        # Test with both API key and session
        with patch('api.CONFIG', mock_config):
            with patch('routes.devices.CONFIG', mock_config):
                transport = ASGITransport(app=api)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    # Set API key header
                    headers = {"Authorization": f"Bearer {api_user.api_key}"}
                    
                    # The API key should work (session is not set in test client)
                    update_data = {"name": "Updated Name"}
                    response = await client.patch(
                        f"/api/v1/devices/{device.id}",
                        json=update_data,
                        headers=headers
                    )
                    assert response.status_code == 200

        api.dependency_overrides.clear()

    @pytest.mark.asyncio  
    async def test_base64_encoded_api_key(self, async_db_session, mock_config, sample_device_data):
        """Test that base64 encoded API keys are properly decoded."""
        from httpx import ASGITransport, AsyncClient
        from api import api
        from db import get_async_db
        import base64

        # Create a test user
        test_user = await UserDB.create(
            async_db_session,
            email="b64user@example.com",
            first_name="B64",
            last_name="User",
            api_key="plain-text-api-key",
            admin=False
        )
        await async_db_session.commit()

        # Create a device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        device = await DeviceDB.create(async_db_session, **db_device_data)
        await async_db_session.commit()

        # Override database dependency
        async def override_get_db():
            yield async_db_session

        api.dependency_overrides[get_async_db] = override_get_db

        # Encode the API key
        encoded_key = base64.b64encode(test_user.api_key.encode()).decode()

        # Test with base64 encoded Bearer token
        with patch('api.CONFIG', mock_config):
            with patch('routes.devices.CONFIG', mock_config):
                transport = ASGITransport(app=api)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    headers = {"Authorization": f"Bearer {encoded_key}"}
                    update_data = {"name": "Updated with B64 Key"}
                    response = await client.patch(
                        f"/api/v1/devices/{device.id}",
                        json=update_data,
                        headers=headers
                    )
                    assert response.status_code == 200

        api.dependency_overrides.clear()


class TestAdminAuthorization:
    """Test admin-only endpoint authorization."""

    @pytest.mark.asyncio
    async def test_non_admin_user_cannot_access_admin_endpoints(self, async_db_session, mock_config):
        """Test that non-admin users cannot access admin endpoints."""
        from httpx import ASGITransport, AsyncClient
        from api import api
        from db import get_async_db

        # Create a non-admin user
        regular_user = await UserDB.create(
            async_db_session,
            email="regular@example.com",
            first_name="Regular",
            last_name="User",
            api_key="regular-api-key",
            admin=False
        )
        await async_db_session.commit()

        # Override database dependency
        async def override_get_db():
            yield async_db_session

        api.dependency_overrides[get_async_db] = override_get_db

        # Try to access admin endpoint
        with patch('api.CONFIG', mock_config):
                transport = ASGITransport(app=api)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    headers = {"Authorization": f"Bearer {regular_user.api_key}"}
                    response = await client.get("/api/v1/users", headers=headers)
                    assert response.status_code == 403
                    assert "not authorized to access" in response.json()["detail"].lower()

        api.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_admin_user_can_access_admin_endpoints(self, async_db_session, mock_config):
        """Test that admin users can access admin endpoints."""
        from httpx import ASGITransport, AsyncClient
        from api import api
        from db import get_async_db

        # Create an admin user
        admin_user = await UserDB.create(
            async_db_session,
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            api_key="admin-api-key",
            admin=True
        )
        await async_db_session.commit()

        # Override database dependency
        async def override_get_db():
            yield async_db_session

        api.dependency_overrides[get_async_db] = override_get_db

        # Access admin endpoint
        with patch('api.CONFIG', mock_config):
                transport = ASGITransport(app=api)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    headers = {"Authorization": f"Bearer {admin_user.api_key}"}
                    response = await client.get("/api/v1/users", headers=headers)
                    assert response.status_code == 200

        api.dependency_overrides.clear()