"""Integration tests for user API endpoints."""

import pytest
import asyncio
import json
from typing import Dict
from httpx import AsyncClient


class TestUsersIntegration:
    """Integration tests for user endpoints."""

    @pytest.mark.asyncio
    async def test_get_current_user(self, async_api_client: AsyncClient, test_user: Dict):
        """Test getting current authenticated user."""
        # Login as test user
        login_data = {"email": test_user["email"], "password": "password123"}
        login_response = await async_api_client.post("/login", json=login_data)
        assert login_response.status_code == 200
        
        # Get current user
        response = await async_api_client.get("/api/v1/users/current")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["firstName"] == test_user["first_name"]
        assert data["lastName"] == test_user["last_name"]

    @pytest.mark.asyncio
    async def test_get_current_user_with_api_key(self, async_api_client: AsyncClient, test_user: Dict):
        """Test getting current user with API key authentication."""
        headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        response = await async_api_client.get("/api/v1/users/current", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]

    @pytest.mark.asyncio
    async def test_get_current_user_service_account(self, async_api_client: AsyncClient, test_service_account: Dict):
        """Test that service accounts return 404 for current user."""
        headers = {"Authorization": f"Bearer {test_service_account['api_key']}"}
        response = await async_api_client.get("/api/v1/users/current", headers=headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_users_requires_admin(self, async_api_client: AsyncClient, test_user: Dict, admin_user: Dict):
        """Test listing users requires admin privileges."""
        # Non-admin should be forbidden
        headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        response = await async_api_client.get("/api/v1/users", headers=headers)
        assert response.status_code == 403
        
        # Admin should succeed
        admin_headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        response = await async_api_client.get("/api/v1/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2  # At least test_user and admin_user

    @pytest.mark.asyncio
    async def test_create_user_admin_only(self, async_api_client: AsyncClient, admin_user: Dict):
        """Test creating a user requires admin."""
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        new_user_data = {
            "email": "newuser@test.com",
            "firstName": "New",
            "lastName": "User",
            "admin": False
        }
        
        response = await async_api_client.post("/api/v1/users", json=new_user_data, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["firstName"] == "New"
        assert data["lastName"] == "User"
        assert data["admin"] is False
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_user_by_id_admin_only(self, async_api_client: AsyncClient, admin_user: Dict, test_user: Dict):
        """Test getting a specific user requires admin."""
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        response = await async_api_client.get(f"/api/v1/users/{test_user['id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]

    @pytest.mark.asyncio
    async def test_update_user_self(self, async_api_client: AsyncClient, test_user: Dict):
        """Test users can update their own information."""
        headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        update_data = {
            "firstName": "Updated",
            "lastName": "Name"
        }
        
        response = await async_api_client.patch(f"/api/v1/users/{test_user['id']}", json=update_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["firstName"] == "Updated"
        assert data["lastName"] == "Name"

    @pytest.mark.asyncio
    async def test_update_other_user_forbidden(self, async_api_client: AsyncClient, test_user: Dict, admin_user: Dict):
        """Test non-admin cannot update other users."""
        headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        update_data = {"firstName": "Hacked"}
        
        response = await async_api_client.patch(f"/api/v1/users/{admin_user['id']}", json=update_data, headers=headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_admin_status_non_admin(self, async_api_client: AsyncClient, test_user: Dict):
        """Test non-admin cannot change admin status."""
        headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        update_data = {"admin": True}
        
        response = await async_api_client.patch(f"/api/v1/users/{test_user['id']}", json=update_data, headers=headers)
        assert response.status_code == 200
        
        # Verify admin status didn't change
        response = await async_api_client.get("/api/v1/users/current", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["admin"] is False

    @pytest.mark.asyncio
    async def test_delete_user_admin_only(self, async_api_client: AsyncClient, admin_user: Dict):
        """Test deleting a user requires admin."""
        # First create a user to delete
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        new_user_data = {
            "email": "deletetest@test.com",
            "firstName": "Delete",
            "lastName": "Test",
            "admin": False
        }
        
        create_response = await async_api_client.post("/api/v1/users", json=new_user_data, headers=headers)
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]
        
        # Delete the user
        delete_response = await async_api_client.delete(f"/api/v1/users/{user_id}", headers=headers)
        assert delete_response.status_code == 204
        
        # Verify user is deleted
        get_response = await async_api_client.get(f"/api/v1/users/{user_id}", headers=headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_user_api_key_self(self, async_api_client: AsyncClient, test_user: Dict):
        """Test users can get their own API key."""
        headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        response = await async_api_client.get(f"/api/v1/users/{test_user['id']}/api_key", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "apiKey" in data
        assert data["apiKey"] == test_user["api_key"]

    @pytest.mark.asyncio
    async def test_get_other_user_api_key_forbidden(self, async_api_client: AsyncClient, test_user: Dict, admin_user: Dict):
        """Test non-admin cannot get other users' API keys."""
        headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        response = await async_api_client.get(f"/api/v1/users/{admin_user['id']}/api_key", headers=headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_generate_api_key_self(self, async_api_client: AsyncClient, test_user: Dict):
        """Test users can generate their own API key."""
        headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        response = await async_api_client.post(f"/api/v1/users/{test_user['id']}/api_key/generate", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "apiKey" in data
        assert len(data["apiKey"]) == 36  # UUID format
        assert data["apiKey"] != test_user["api_key"]  # New key is different

    @pytest.mark.asyncio
    async def test_delete_api_key_self(self, async_api_client: AsyncClient, admin_user: Dict):
        """Test users can delete their own API key."""
        # Create a test user for this test
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        new_user_data = {
            "email": "apikeytest@test.com",
            "firstName": "API",
            "lastName": "Test",
            "admin": False
        }
        
        create_response = await async_api_client.post("/api/v1/users", json=new_user_data, headers=headers)
        assert create_response.status_code == 201
        user_data = create_response.json()
        user_id = user_data["id"]
        
        # Generate an API key
        gen_response = await async_api_client.post(f"/api/v1/users/{user_id}/api_key/generate", headers=headers)
        assert gen_response.status_code == 200
        api_key = gen_response.json()["apiKey"]
        
        # Delete the API key
        user_headers = {"Authorization": f"Bearer {api_key}"}
        delete_response = await async_api_client.delete(f"/api/v1/users/{user_id}/api_key", headers=user_headers)
        assert delete_response.status_code == 200
        
        # Verify API key is deleted (should now fail to authenticate)
        verify_response = await async_api_client.get("/api/v1/users/current", headers=user_headers)
        assert verify_response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_can_manage_other_users(self, async_api_client: AsyncClient, admin_user: Dict, test_user: Dict):
        """Test admin can update and manage other users."""
        headers = {"Authorization": f"Bearer {admin_user['api_key']}"}
        
        # Update another user
        update_data = {
            "firstName": "AdminUpdated",
            "lastName": "ByAdmin",
            "admin": True  # Admin can change admin status
        }
        
        response = await async_api_client.patch(f"/api/v1/users/{test_user['id']}", json=update_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["firstName"] == "AdminUpdated"
        assert data["lastName"] == "ByAdmin"
        assert data["admin"] is True
        
        # Generate API key for another user
        api_response = await async_api_client.post(f"/api/v1/users/{test_user['id']}/api_key/generate", headers=headers)
        assert api_response.status_code == 200
        assert "apiKey" in api_response.json()


class TestUserAuthenticationIntegration:
    """Integration tests for user authentication flows."""

    @pytest.mark.asyncio
    async def test_session_based_authentication(self, async_api_client: AsyncClient, test_user: Dict):
        """Test session-based authentication with login."""
        # Initially not authenticated
        response = await async_api_client.get("/api/v1/users/current")
        assert response.status_code == 401
        
        # Login
        login_data = {"email": test_user["email"], "password": "password123"}
        login_response = await async_api_client.post("/login", json=login_data)
        assert login_response.status_code == 200
        
        # Now authenticated via session
        response = await async_api_client.get("/api/v1/users/current")
        assert response.status_code == 200
        assert response.json()["email"] == test_user["email"]
        
        # Logout (returns redirect)
        logout_response = await async_api_client.post("/logout")
        assert logout_response.status_code in (200, 307)  # May redirect
        
        # No longer authenticated
        response = await async_api_client.get("/api/v1/users/current")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_authentication(self, async_api_client: AsyncClient, test_user: Dict):
        """Test API key authentication."""
        # Without API key
        response = await async_api_client.get("/api/v1/users/current")
        assert response.status_code == 401
        
        # With API key in header
        headers = {"Authorization": f"Bearer {test_user['api_key']}"}
        response = await async_api_client.get("/api/v1/users/current", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == test_user["email"]
        
        # With API key as query parameter
        response = await async_api_client.get(f"/api/v1/users/current?api_key={test_user['api_key']}")
        assert response.status_code == 200
        assert response.json()["email"] == test_user["email"]

    @pytest.mark.asyncio
    async def test_invalid_api_key(self, async_api_client: AsyncClient):
        """Test invalid API key returns 401."""
        headers = {"Authorization": "Bearer invalid-api-key"}
        response = await async_api_client.get("/api/v1/users/current", headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_password_login(self, async_api_client: AsyncClient, test_user: Dict):
        """Test login with wrong password fails."""
        login_data = {"email": test_user["email"], "password": "wrongpassword"}
        response = await async_api_client.post("/login", json=login_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_nonexistent_user_login(self, async_api_client: AsyncClient):
        """Test login with non-existent user fails."""
        login_data = {"email": "nonexistent@test.com", "password": "password123"}
        response = await async_api_client.post("/login", json=login_data)
        assert response.status_code == 401