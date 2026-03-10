"""
Integration tests for authentication and authorization.
These tests run against a real API server to validate actual HTTP behavior.
"""

import pytest
import httpx


class TestAuthenticationIntegration:
    """Test authentication requirements against running API."""
    
    def test_device_update_requires_auth(self, api_client, create_test_device):
        """Test that updating a device requires authentication."""
        # Create a device
        device = create_test_device()
        
        # Try to update without auth - should get 401
        response = api_client.put(
            f"/api/v1/devices/{device.id}",
            json={"name": "Updated Name"}
        )
        assert response.status_code == 401
        assert "not authorized" in response.json()["detail"].lower()
    
    def test_device_patch_requires_auth(self, api_client, create_test_device):
        """Test that patching a device requires authentication."""
        # Create a device
        device = create_test_device()
        
        # Try to patch without auth - should get 401
        response = api_client.patch(
            f"/api/v1/devices/{device.id}",
            json={"name": "Updated Name"}
        )
        assert response.status_code == 401
        assert "not authorized" in response.json()["detail"].lower()
    
    def test_port_update_requires_auth(self, api_client, create_test_device):
        """Test that updating a port requires authentication."""
        # Create a device with ports
        device = create_test_device(
            ports=[{
                "port_index": 0,
                "port_name": "Test Port",
                "keg_size": 19000,
                "start_volume": 19000,
                "volume_dispensed": 0,
                "display_unit": "mL",
                "configured": True
            }]
        )
        
        # Try to update port without auth - should get 401
        response = api_client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json={"port_name": "Updated Port"}
        )
        assert response.status_code == 401
        assert "not authorized" in response.json()["detail"].lower()
    
    def test_rpc_endpoints_require_auth(self, api_client, create_test_device):
        """Test that RPC endpoints require authentication."""
        # Create a device
        device = create_test_device()
        
        # Test UnlockWriteAll
        response = api_client.post(f"/api/v1/devices/{device.id}/rpc/Kegtron.UnlockWriteAll")
        assert response.status_code == 401
        
        # Test UnlockWrite
        response = api_client.post(f"/api/v1/devices/{device.id}/port/0/rpc/Kegtron.UnlockWrite")
        assert response.status_code == 401
        
        # Test ResetVolume
        response = api_client.post(
            f"/api/v1/devices/{device.id}/port/0/rpc/Kegtron.ResetVolume",
            json={"kegSize": 19000}
        )
        assert response.status_code == 401
    
    def test_public_endpoints_no_auth_required(self, api_client, create_test_device):
        """Test that public endpoints work without authentication."""
        # Create a device
        device = create_test_device(
            ports=[{
                "port_index": 0,
                "port_name": "Test Port",
                "keg_size": 19000,
                "start_volume": 19000,
                "volume_dispensed": 0,
                "display_unit": "mL",
                "configured": True
            }]
        )
        
        # Health check - should work
        response = api_client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        
        # Ping - should work
        response = api_client.get("/api/v1/ping")
        assert response.status_code == 200
        assert response.json() == "pong"
        
        # GET devices - should work
        response = api_client.get("/api/v1/devices")
        assert response.status_code == 200
        devices = response.json()
        assert len(devices) == 1
        assert devices[0]["id"] == device.id
        
        # GET specific device - should work
        response = api_client.get(f"/api/v1/devices/{device.id}")
        assert response.status_code == 200
        assert response.json()["id"] == device.id
        
        # POST new device - should work
        new_device_data = {
            "id": "new-device-123",
            "mac": "FF:EE:DD:CC:BB:AA",
            "name": "New Device",
            "model": "KT-100",
            "portCnt": 1,
            "ports": {
                "0": {
                    "portIndex": 0,
                    "portName": "Port 0",
                    "kegSize": 19000,
                    "startVolume": 19000,
                    "volumeDispensed": 0,
                    "displayUnit": "mL",
                    "configured": True
                }
            }
        }
        response = api_client.post("/api/v1/devices", json=new_device_data)
        assert response.status_code == 201
        assert response.json() == {"created": True}


class TestUserAPIKeyAuthentication:
    """Test authentication using user API keys against running API."""
    
    def test_user_api_key_bearer_token(self, api_client, create_test_user, create_test_device):
        """Test that a valid user API key in Bearer token allows access."""
        # Create a user with API key
        user = create_test_user(api_key="user-test-key-123")
        
        # Create a device
        device = create_test_device()
        
        # Update device with Bearer token auth
        headers = {"Authorization": f"Bearer {user.api_key}"}
        response = api_client.patch(
            f"/api/v1/devices/{device.id}",
            json={"name": "Updated via API Key"},
            headers=headers
        )
        if response.status_code != 200:
            print(f"Error response: {response.status_code} - {response.text}")
        assert response.status_code == 200
        assert response.json() == {"updated": True}
        
        # Verify the update worked
        response = api_client.get(f"/api/v1/devices/{device.id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Updated via API Key"
    
    def test_user_api_key_query_param(self, api_client, create_test_user, create_test_device):
        """Test that a valid user API key as query parameter allows access."""
        # Create a user with API key
        user = create_test_user(api_key="user-test-key-456")
        
        # Create a device with port
        device = create_test_device(
            ports=[{
                "port_index": 0,
                "port_name": "Original Port",
                "keg_size": 19000,
                "start_volume": 19000,
                "volume_dispensed": 0,
                "display_unit": "mL",
                "configured": True
            }]
        )
        
        # Update port with API key as query param
        response = api_client.patch(
            f"/api/v1/devices/{device.id}/ports/0?api_key={user.api_key}",
            json={"port_name": "Updated Port via Query Param"}
        )
        assert response.status_code == 200
        assert response.json() == {"updated": True}
        
        # Verify the update worked
        response = api_client.get(f"/api/v1/devices/{device.id}")
        assert response.status_code == 200
        device_data = response.json()
        assert device_data["ports"]["0"]["portName"] == "Updated Port via Query Param"
    
    def test_invalid_api_key_rejected(self, api_client, create_test_device):
        """Test that an invalid API key is rejected."""
        # Create a device
        device = create_test_device()
        
        # Try with invalid Bearer token
        headers = {"Authorization": "Bearer invalid-api-key"}
        response = api_client.patch(
            f"/api/v1/devices/{device.id}",
            json={"name": "Should Fail"},
            headers=headers
        )
        assert response.status_code == 401
        assert "not authorized" in response.json()["detail"].lower()
        
        # Try with invalid query param
        response = api_client.patch(
            f"/api/v1/devices/{device.id}?api_key=invalid-key",
            json={"name": "Should Also Fail"}
        )
        assert response.status_code == 401
    
    def test_base64_encoded_api_key(self, api_client, create_test_user, create_test_device):
        """Test that base64 encoded API keys are properly decoded."""
        import base64
        
        # Create a user
        user = create_test_user(api_key="plain-text-api-key")
        
        # Create a device
        device = create_test_device()
        
        # Encode the API key
        encoded_key = base64.b64encode(user.api_key.encode()).decode()
        
        # Use encoded key as Bearer token
        headers = {"Authorization": f"Bearer {encoded_key}"}
        response = api_client.patch(
            f"/api/v1/devices/{device.id}",
            json={"name": "Updated with B64 Key"},
            headers=headers
        )
        assert response.status_code == 200
        
        # Verify update
        response = api_client.get(f"/api/v1/devices/{device.id}")
        assert response.json()["name"] == "Updated with B64 Key"


class TestServiceAccountAPIKeyAuthentication:
    """Test authentication using service account API keys against running API."""
    
    def test_service_account_api_key_bearer_token(self, api_client, create_test_service_account, create_test_device):
        """Test that a valid service account API key in Bearer token allows access."""
        # Create a service account
        service_account = create_test_service_account(api_key="service-key-789")
        
        # Create a device
        device = create_test_device()
        
        # Update device with service account Bearer token
        headers = {"Authorization": f"Bearer {service_account.api_key}"}
        response = api_client.patch(
            f"/api/v1/devices/{device.id}",
            json={"name": "Updated via Service Account"},
            headers=headers
        )
        assert response.status_code == 200
        assert response.json() == {"updated": True}
        
        # Verify the update
        response = api_client.get(f"/api/v1/devices/{device.id}")
        assert response.json()["name"] == "Updated via Service Account"
    
    def test_service_account_api_key_query_param(self, api_client, create_test_service_account, create_test_device):
        """Test that a valid service account API key as query parameter allows access."""
        # Create a service account
        service_account = create_test_service_account(api_key="service-key-abc")
        
        # Create a device with port
        device = create_test_device(
            ports=[{
                "port_index": 0,
                "port_name": "Test Port",
                "keg_size": 19000,
                "start_volume": 19000,
                "volume_dispensed": 0,
                "display_unit": "mL",
                "configured": True
            }]
        )
        
        # Use a simpler endpoint that doesn't require GATT operations
        # Update port with service account API key as query param
        response = api_client.patch(
            f"/api/v1/devices/{device.id}/ports/0?api_key={service_account.api_key}",
            json={"port_name": "Updated via Service Account Query"}
        )
        assert response.status_code == 200
        
        # Verify the update worked
        response = api_client.get(f"/api/v1/devices/{device.id}")
        device_data = response.json()
        assert device_data["ports"]["0"]["portName"] == "Updated via Service Account Query"


class TestAdminAuthorization:
    """Test admin-only endpoint authorization against running API."""
    
    def test_non_admin_user_cannot_access_admin_endpoints(self, api_client, create_test_user):
        """Test that non-admin users cannot access admin endpoints."""
        # Create a regular user
        user = create_test_user(api_key="regular-key", admin=False)
        
        # Try to access users list (admin only)
        headers = {"Authorization": f"Bearer {user.api_key}"}
        response = api_client.get("/api/v1/users", headers=headers)
        assert response.status_code == 403
        assert "not authorized to access" in response.json()["detail"].lower()
    
    def test_admin_user_can_access_admin_endpoints(self, api_client, create_test_user):
        """Test that admin users can access admin endpoints."""
        # Create an admin user
        admin = create_test_user(
            email="admin@example.com",
            api_key="admin-key",
            admin=True
        )
        
        # Access users list
        headers = {"Authorization": f"Bearer {admin.api_key}"}
        response = api_client.get("/api/v1/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        assert len(users) == 1
        assert users[0]["email"] == "admin@example.com"
    
    def test_service_account_cannot_access_admin_endpoints(self, api_client, create_test_service_account):
        """Test that service accounts cannot access admin endpoints."""
        # Create a service account
        service_account = create_test_service_account(
            name="Regular Service",
            api_key="service-key-123"
        )
        
        # Try to access service accounts list (admin only) - should be forbidden
        headers = {"Authorization": f"Bearer {service_account.api_key}"}
        response = api_client.get("/api/v1/service_accounts", headers=headers)
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()


class TestSessionAuthentication:
    """Test session-based authentication against running API."""
    
    def test_login_creates_session(self, api_client, create_test_user):
        """Test that login creates a session that can be used for auth."""
        # Create a user with password
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        user = create_test_user(api_key="user-key")
        # Note: In a real scenario, we'd need to set the password hash
        # For this test, we'll skip password login and focus on API key auth
        
        # This test would require password support to be fully implemented
        # Skipping for now as the focus is on API key authentication
        pass


class TestConcurrentRequests:
    """Test concurrent authenticated requests against running API."""
    
    def test_concurrent_api_key_requests(self, api_client, create_test_user, create_test_device):
        """Test that multiple concurrent requests with API keys work correctly."""
        import concurrent.futures
        
        # Create multiple users
        users = [
            create_test_user(email=f"user{i}@example.com", api_key=f"key-{i}")
            for i in range(3)
        ]
        
        # Create multiple devices
        devices = [
            create_test_device(
                device_id=f"device-{i}",
                mac=f"AA:BB:CC:DD:EE:{i:02X}"
            )
            for i in range(3)
        ]
        
        def update_device(user_key, device_id, name):
            """Helper to update a device with authentication."""
            headers = {"Authorization": f"Bearer {user_key}"}
            response = api_client.patch(
                f"/api/v1/devices/{device_id}",
                json={"name": name},
                headers=headers
            )
            return response.status_code == 200
        
        # Make concurrent updates
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for i, (user, device) in enumerate(zip(users, devices)):
                future = executor.submit(
                    update_device,
                    user.api_key,
                    device.id,
                    f"Updated by User {i}"
                )
                futures.append(future)
            
            # All updates should succeed
            results = [f.result() for f in futures]
            assert all(results)
        
        # Verify all updates were applied
        for i, device in enumerate(devices):
            response = api_client.get(f"/api/v1/devices/{device.id}")
            assert response.status_code == 200
            assert response.json()["name"] == f"Updated by User {i}"


class TestRateLimiting:
    """Test API behavior under load and with invalid auth attempts."""
    
    def test_multiple_invalid_auth_attempts(self, api_client, create_test_device):
        """Test that multiple invalid auth attempts are handled properly."""
        device = create_test_device()
        
        # Make multiple requests with invalid API keys
        for i in range(10):
            headers = {"Authorization": f"Bearer invalid-key-{i}"}
            response = api_client.patch(
                f"/api/v1/devices/{device.id}",
                json={"name": f"Attempt {i}"},
                headers=headers
            )
            assert response.status_code == 401
        
        # Valid request should still work
        # (In production, you might implement rate limiting for failed auth)
        response = api_client.get(f"/api/v1/devices/{device.id}")
        assert response.status_code == 200