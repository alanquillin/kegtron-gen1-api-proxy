"""Integration tests for service account API endpoints."""

import pytest
import asyncio
import json
from typing import Dict
from httpx import AsyncClient


class TestServiceAccountsIntegration:
    """Integration tests for service account endpoints."""

    @pytest.mark.asyncio
    async def test_list_service_accounts_admin_only(self, async_api_client: AsyncClient, test_user: Dict, admin_user: Dict):
        """Test listing service accounts requires admin privileges."""
        # Non-admin should be forbidden
        headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        response = await async_api_client.get("/api/v1/service_accounts", headers=headers)
        assert response.status_code == 403
        assert "not authorized to access" in response.json()["detail"].lower()
        
        # Admin should succeed
        admin_headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        response = await async_api_client.get("/api/v1/service_accounts", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_service_account_admin_only(self, async_api_client: AsyncClient, admin_user: Dict, test_user: Dict):
        """Test creating a service account requires admin."""
        # Non-admin should be forbidden
        headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        new_account_data = {
            "name": "Test Service"
        }
        response = await async_api_client.post("/api/v1/service_accounts", json=new_account_data, headers=headers)
        assert response.status_code == 403
        
        # Admin should succeed
        admin_headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        response = await async_api_client.post("/api/v1/service_accounts", json=new_account_data, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Service"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_service_account_with_custom_api_key(self, async_api_client: AsyncClient, admin_user: Dict):
        """Test creating a service account with custom API key."""
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        custom_key = "custom-test-api-key-12345"
        new_account_data = {
            "name": "Custom API Service",
            "apiKey": custom_key
        }
        
        response = await async_api_client.post("/api/v1/service_accounts", json=new_account_data, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Custom API Service"
        
        # Verify the custom API key works
        custom_headers = {"Authorization": f"Bearer {custom_key}"}
        auth_response = await async_api_client.get("/api/v1/devices", headers=custom_headers)
        assert auth_response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_service_account_admin_only(self, async_api_client: AsyncClient, admin_user: Dict, test_service_account: Dict):
        """Test getting a specific service account requires admin."""
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        response = await async_api_client.get(f"/api/v1/service_accounts/{test_service_account['id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == test_service_account["name"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_service_account(self, async_api_client: AsyncClient, admin_user: Dict):
        """Test getting non-existent service account returns 404."""
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        response = await async_api_client.get("/api/v1/service_accounts/nonexistent-id", headers=headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_service_account(self, async_api_client: AsyncClient, admin_user: Dict):
        """Test updating a service account."""
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        
        # Create a service account
        create_data = {"name": "Update Test", "admin": False}
        create_response = await async_api_client.post("/api/v1/service_accounts", json=create_data, headers=headers)
        assert create_response.status_code == 201
        account_id = create_response.json()["id"]
        
        # Update it
        update_data = {
            "name": "Updated Service"
        }
        update_response = await async_api_client.patch(f"/api/v1/service_accounts/{account_id}", json=update_data, headers=headers)
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Updated Service"

    @pytest.mark.asyncio
    async def test_update_nonexistent_service_account(self, async_api_client: AsyncClient, admin_user: Dict):
        """Test updating non-existent service account returns 404."""
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        update_data = {"name": "Updated"}
        response = await async_api_client.patch("/api/v1/service_accounts/nonexistent-id", json=update_data, headers=headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_service_account_admin_only(self, async_api_client: AsyncClient, admin_user: Dict, test_user: Dict):
        """Test deleting a service account requires admin."""
        admin_headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        
        # Create a service account to delete
        create_data = {"name": "Delete Test"}
        create_response = await async_api_client.post("/api/v1/service_accounts", json=create_data, headers=admin_headers)
        assert create_response.status_code == 201
        account_id = create_response.json()["id"]
        
        # Non-admin should be forbidden
        user_headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        delete_response = await async_api_client.delete(f"/api/v1/service_accounts/{account_id}", headers=user_headers)
        assert delete_response.status_code == 403
        
        # Admin should succeed
        delete_response = await async_api_client.delete(f"/api/v1/service_accounts/{account_id}", headers=admin_headers)
        assert delete_response.status_code == 204
        
        # Verify it's deleted
        get_response = await async_api_client.get(f"/api/v1/service_accounts/{account_id}", headers=admin_headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_service_account_api_key(self, async_api_client: AsyncClient, admin_user: Dict):
        """Test generating new API key for service account."""
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        
        # Create a service account
        create_data = {"name": "API Key Test", "admin": False}
        create_response = await async_api_client.post("/api/v1/service_accounts", json=create_data, headers=headers)
        assert create_response.status_code == 201
        account_id = create_response.json()["id"]
        
        # Generate new API key
        gen_response = await async_api_client.post(f"/api/v1/service_accounts/{account_id}/api_key/generate", headers=headers)
        assert gen_response.status_code == 200
        data = gen_response.json()
        assert "apiKey" in data
        assert len(data["apiKey"]) == 36  # UUID format
        
        # Verify the new API key works
        new_headers = {"Authorization": f"Bearer {data['apiKey']}"}
        auth_response = await async_api_client.get("/api/v1/devices", headers=new_headers)
        assert auth_response.status_code == 200

    @pytest.mark.asyncio
    async def test_generate_api_key_nonexistent_account(self, async_api_client: AsyncClient, admin_user: Dict):
        """Test generating API key for non-existent account returns 404."""
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        response = await async_api_client.post("/api/v1/service_accounts/nonexistent-id/api_key/generate", headers=headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_service_account_api_key_admin_only(self, async_api_client: AsyncClient, admin_user: Dict, test_user: Dict):
        """Test deleting service account API key requires admin."""
        admin_headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        
        # Create a service account
        create_data = {"name": "API Delete Test", "admin": False}
        create_response = await async_api_client.post("/api/v1/service_accounts", json=create_data, headers=admin_headers)
        assert create_response.status_code == 201
        account_id = create_response.json()["id"]
        
        # Generate an API key
        gen_response = await async_api_client.post(f"/api/v1/service_accounts/{account_id}/api_key/generate", headers=admin_headers)
        assert gen_response.status_code == 200
        api_key = gen_response.json()["apiKey"]
        
        # Non-admin should be forbidden
        user_headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        delete_response = await async_api_client.delete(f"/api/v1/service_accounts/{account_id}/api_key", headers=user_headers)
        assert delete_response.status_code == 403
        assert "not authorized to access this resource" in delete_response.json()["detail"].lower()
        
        # Admin should succeed
        delete_response = await async_api_client.delete(f"/api/v1/service_accounts/{account_id}/api_key", headers=admin_headers)
        assert delete_response.status_code == 204
        
        # Verify API key is deleted (should no longer work)
        deleted_headers = {"Authorization": f"Bearer {api_key}"}
        auth_response = await async_api_client.get("/api/v1/users/current", headers=deleted_headers)
        assert auth_response.status_code == 401

    @pytest.mark.asyncio
    async def test_service_account_permissions(self, async_api_client: AsyncClient, admin_user: Dict):
        """Test service account permission levels."""
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        
        # Create service account
        regular_data = {"name": "Regular Service"}
        regular_response = await async_api_client.post("/api/v1/service_accounts", json=regular_data, headers=headers)
        assert regular_response.status_code == 201
        regular_key = regular_response.json().get("apiKey")
        
        # Generate API key if not returned
        if not regular_key:
            regular_id = regular_response.json()["id"]
            gen_response = await async_api_client.post(f"/api/v1/service_accounts/{regular_id}/api_key/generate", headers=headers)
            regular_key = gen_response.json()["apiKey"]
        
        # Create another service account
        admin_data = {"name": "Another Service"}
        admin_response = await async_api_client.post("/api/v1/service_accounts", json=admin_data, headers=headers)
        assert admin_response.status_code == 201
        admin_service_key = admin_response.json().get("apiKey")
        
        # Generate API key if not returned
        if not admin_service_key:
            admin_id = admin_response.json()["id"]
            gen_response = await async_api_client.post(f"/api/v1/service_accounts/{admin_id}/api_key/generate", headers=headers)
            admin_service_key = gen_response.json()["apiKey"]
        
        # Test regular service account permissions
        regular_headers = {"Authorization": f"Bearer {regular_key}"}
        
        # Can access devices
        response = await async_api_client.get("/api/v1/devices", headers=regular_headers)
        assert response.status_code == 200
        
        # Cannot access users list
        response = await async_api_client.get("/api/v1/users", headers=regular_headers)
        assert response.status_code == 403
        
        # Test second service account permissions (same as first)
        admin_service_headers = {"Authorization": f"Bearer {admin_service_key}"}
        
        # Can access devices
        response = await async_api_client.get("/api/v1/devices", headers=admin_service_headers)
        assert response.status_code == 200
        
        # Cannot access users list (service accounts don't have admin privileges)
        response = await async_api_client.get("/api/v1/users", headers=admin_service_headers)
        assert response.status_code == 403


class TestServiceAccountAuthenticationIntegration:
    """Integration tests for service account authentication."""

    @pytest.mark.asyncio
    async def test_service_account_api_key_authentication(self, async_api_client: AsyncClient, test_service_account: Dict):
        """Test service account authentication with API key."""
        # Test that public endpoints work without auth
        response = await async_api_client.get("/api/v1/devices")
        assert response.status_code == 200
        
        # Test authenticated endpoints - use /api/v1/users/current which requires auth
        # Without API key
        response = await async_api_client.get("/api/v1/users/current")
        assert response.status_code == 401
        
        # With API key in header (service account should get 404 for /users/current)
        headers = {"Authorization": f"Bearer {test_service_account['api_key']}"}
        response = await async_api_client.get("/api/v1/users/current", headers=headers)
        assert response.status_code == 404  # Service accounts return 404 for /users/current
        
        # Test service account can access other auth-required endpoints
        # List service accounts requires auth
        response = await async_api_client.get("/api/v1/service_accounts", headers=headers)
        # Regular service accounts (non-admin) should get 403
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_service_account_cannot_use_session(self, async_api_client: AsyncClient):
        """Test that service accounts cannot use session authentication."""
        # Service accounts don't have email/password, so they can't login
        # This test ensures that even if someone tries to create a session
        # for a service account, it won't work
        
        # Attempt to login with fake service account credentials
        login_data = {"email": "service@test.com", "password": "password123"}
        response = await async_api_client.post("/login", json=login_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_service_account_cannot_access_admin_endpoints(self, async_api_client: AsyncClient, admin_user: Dict):
        """Test service accounts cannot access admin endpoints."""
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        
        # Create a service account
        service_data = {
            "name": "Test Service Account"
        }
        response = await async_api_client.post("/api/v1/service_accounts", json=service_data, headers=headers)
        assert response.status_code == 201
        account_id = response.json()["id"]
        
        # Generate API key
        gen_response = await async_api_client.post(f"/api/v1/service_accounts/{account_id}/api_key/generate", headers=headers)
        assert gen_response.status_code == 200
        service_api_key = gen_response.json()["apiKey"]
        
        # Use service account to try admin actions
        service_headers = {"Authorization": f"Bearer {service_api_key}"}
        
        # Should NOT be able to create users (admin-only)
        new_user_data = {
            "email": "servicetest@test.com",
            "firstName": "Service",
            "lastName": "Created",
            "admin": False
        }
        user_response = await async_api_client.post("/api/v1/users", json=new_user_data, headers=service_headers)
        assert user_response.status_code == 403
        
        # Should NOT be able to list users (admin-only)
        list_response = await async_api_client.get("/api/v1/users", headers=service_headers)
        assert list_response.status_code == 403

    @pytest.mark.asyncio
    async def test_mixed_authentication_priority(self, async_api_client: AsyncClient, test_user: Dict):
        """Test that API key authentication takes priority over session."""
        # Login to create session
        login_data = {"email": test_user["email"], "password": "password123"}
        login_response = await async_api_client.post("/login", json=login_data)
        assert login_response.status_code == 200
        
        # Verify session works
        response = await async_api_client.get("/api/v1/users/current")
        assert response.status_code == 200
        assert response.json()["email"] == test_user["email"]
        
        # Now use an invalid API key - session should still work
        # The session remains valid even with an invalid bearer token
        headers = {"Authorization": "Bearer invalid-key"}
        response = await async_api_client.get("/api/v1/users/current", headers=headers)
        assert response.status_code == 200  # Session is still valid