"""Unit tests for user API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from db.users import User as UserDB
from dependencies.auth import AuthUser


class TestUserEndpoints:
    """Test user API endpoints."""

    @pytest.mark.asyncio
    async def test_get_current_user(self, client, mock_auth_user):
        """Test getting current authenticated user."""
        # Mock the database to return a user
        mock_user = MagicMock()
        mock_user.id = mock_auth_user.id
        mock_user.email = mock_auth_user.email
        mock_user.first_name = mock_auth_user.first_name
        mock_user.last_name = mock_auth_user.last_name
        mock_user.admin = mock_auth_user.admin
        mock_user.api_key = mock_auth_user.api_key
        
        with patch('routes.users.UsersDB.get', new_callable=AsyncMock) as mock_get:
            # Patch db.refresh to do nothing with mock objects
            with patch.object(AsyncSession, 'refresh', new=AsyncMock(return_value=None)):
                with patch('routes.users.UserService.transform_response', new_callable=AsyncMock) as mock_transform:
                    mock_get.return_value = mock_user
                    mock_transform.return_value = {
                        "id": mock_auth_user.id,
                        "email": mock_auth_user.email,
                        "firstName": mock_auth_user.first_name,
                        "lastName": mock_auth_user.last_name,
                        "admin": mock_auth_user.admin
                    }
                    
                    response = await client.get("/api/v1/users/current")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["email"] == mock_auth_user.email
                    assert data["firstName"] == mock_auth_user.first_name
                    assert data["lastName"] == mock_auth_user.last_name

    @pytest.mark.asyncio
    async def test_get_current_user_service_account(self, client):
        """Test that service accounts return None for current user."""
        # Override auth to return a service account
        mock_service_account = AuthUser(
            id_="service-id",
            first_name=None,
            last_name=None,
            email=None,
            profile_pic=None,
            api_key="service-key",
            admin=False,
            service_account=True,
            service_name="Test Service"
        )
        
        from api import api
        from dependencies.auth import require_user
        
        async def override_require_user():
            return mock_service_account
        
        api.dependency_overrides[require_user] = override_require_user
        
        response = await client.get("/api/v1/users/current")
        assert response.status_code == 404  # Changed to return 404 for service accounts
        
        # Clean up override
        del api.dependency_overrides[require_user]

    @pytest.mark.asyncio
    async def test_list_users_admin_only(self, client_admin):
        """Test listing all users requires admin."""
        mock_users = [
            MagicMock(id="1", email="user1@test.com", first_name="User", last_name="One", admin=False, api_key="key1"),
            MagicMock(id="2", email="user2@test.com", first_name="User", last_name="Two", admin=True, api_key="key2"),
        ]
        
        with patch('routes.users.UsersDB.query', new_callable=AsyncMock) as mock_query:
            with patch('routes.users.UserService.transform_response', new_callable=AsyncMock) as mock_transform:
                mock_query.return_value = mock_users
                
                # Mock transform to return dict for each user
                async def transform_side_effect(user, current_user):
                    return {
                        "id": user.id,
                        "email": user.email,
                        "firstName": user.first_name,
                        "lastName": user.last_name,
                        "admin": user.admin
                    }
                mock_transform.side_effect = transform_side_effect
                
                response = await client_admin.get("/api/v1/users")
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["email"] == "user1@test.com"
                assert data[1]["email"] == "user2@test.com"

    @pytest.mark.asyncio
    async def test_list_users_non_admin_forbidden(self, client):
        """Test non-admin cannot list users."""
        response = await client.get("/api/v1/users")
        assert response.status_code == 403
        assert "not authorized to access" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_user_admin_only(self, client_admin):
        """Test creating a user requires admin."""
        new_user_data = {
            "email": "newuser@test.com",
            "firstName": "New",
            "lastName": "User",
            "admin": False
        }
        
        mock_user = MagicMock()
        mock_user.id = str(uuid.uuid4())
        mock_user.email = "newuser@test.com"
        mock_user.first_name = "New"
        mock_user.last_name = "User"
        mock_user.admin = False
        mock_user.api_key = "generated-key"
        
        with patch('routes.users.UsersDB.create', new_callable=AsyncMock) as mock_create:
            with patch('routes.users.UserService.transform_response', new_callable=AsyncMock) as mock_transform:
                mock_create.return_value = mock_user
                mock_transform.return_value = {
                    "id": mock_user.id,
                    "email": mock_user.email,
                    "firstName": mock_user.first_name,
                    "lastName": mock_user.last_name,
                    "admin": mock_user.admin
                }
                
                response = await client_admin.post("/api/v1/users", json=new_user_data)
                assert response.status_code == 201
                data = response.json()
                assert data["email"] == "newuser@test.com"
                assert data["firstName"] == "New"
                assert data["lastName"] == "User"

    @pytest.mark.asyncio
    async def test_get_user_by_id_admin_only(self, client_admin):
        """Test getting a specific user requires admin."""
        user_id = str(uuid.uuid4())
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "user@test.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.admin = False
        mock_user.api_key = "test-key"
        
        with patch('routes.users.UsersDB.get', new_callable=AsyncMock) as mock_get:
            # Patch db.refresh to do nothing with mock objects
            with patch.object(AsyncSession, 'refresh', new=AsyncMock(return_value=None)):
                with patch('routes.users.UserService.transform_response', new_callable=AsyncMock) as mock_transform:
                    mock_get.return_value = mock_user
                    mock_transform.return_value = {
                        "id": mock_user.id,
                        "email": mock_user.email,
                        "firstName": mock_user.first_name,
                        "lastName": mock_user.last_name,
                        "admin": mock_user.admin
                    }
                    
                    response = await client_admin.get(f"/api/v1/users/{user_id}")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["email"] == "user@test.com"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, client_admin):
        """Test getting a non-existent user returns 404."""
        with patch('routes.users.UsersDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            response = await client_admin.get("/api/v1/users/nonexistent")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_user_self(self, client, mock_auth_user):
        """Test users can update themselves."""
        user_id = mock_auth_user.id
        update_data = {
            "firstName": "Updated",
            "lastName": "Name"
        }
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = mock_auth_user.email
        mock_user.first_name = "Updated"
        mock_user.last_name = "Name"
        mock_user.admin = False
        mock_user.api_key = mock_auth_user.api_key
        # Mock the instance update method
        mock_user.update = AsyncMock()
        
        with patch('routes.users.UsersDB.get', new_callable=AsyncMock) as mock_get:
            # Patch db.refresh to do nothing with mock objects
            with patch.object(AsyncSession, 'refresh', new=AsyncMock(return_value=None)):
                with patch('routes.users.UserService.transform_response', new_callable=AsyncMock) as mock_transform:
                    mock_get.return_value = mock_user
                    
                    # Mock transform to handle both 1 and 2 arguments
                    async def transform_side_effect(*args):
                        return {
                            "id": mock_user.id,
                            "email": mock_user.email,
                            "firstName": mock_user.first_name,
                            "lastName": mock_user.last_name,
                            "admin": mock_user.admin
                        }
                    mock_transform.side_effect = transform_side_effect
                    
                    response = await client.patch(f"/api/v1/users/{user_id}", json=update_data)
                    assert response.status_code == 200
                    data = response.json()
                    assert data["firstName"] == "Updated"
                    assert data["lastName"] == "Name"
                    
                    # Verify update was called with correct data
                    mock_user.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_other_user_non_admin_forbidden(self, client):
        """Test non-admin cannot update other users."""
        other_user_id = str(uuid.uuid4())
        update_data = {"firstName": "Hacked"}
        
        response = await client.patch(f"/api/v1/users/{other_user_id}", json=update_data)
        assert response.status_code == 403
        assert "not authorized to update" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_user_admin_status_non_admin(self, client, mock_auth_user):
        """Test non-admin cannot change admin status."""
        user_id = mock_auth_user.id
        update_data = {
            "admin": True  # Try to make themselves admin
        }
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = mock_auth_user.email
        mock_user.first_name = mock_auth_user.first_name
        mock_user.last_name = mock_auth_user.last_name
        mock_user.admin = False  # Should remain False
        mock_user.api_key = mock_auth_user.api_key
        # Mock the instance update method
        mock_user.update = AsyncMock()
        
        with patch('routes.users.UsersDB.get', new_callable=AsyncMock) as mock_get:
            # Patch db.refresh to do nothing with mock objects
            with patch.object(AsyncSession, 'refresh', new=AsyncMock(return_value=None)):
                with patch('routes.users.UserService.transform_response', new_callable=AsyncMock) as mock_transform:
                    mock_get.return_value = mock_user
                    
                    # Mock transform to handle both 1 and 2 arguments
                    async def transform_side_effect(*args):
                        return {
                            "id": mock_user.id,
                            "email": mock_user.email,
                            "firstName": mock_user.first_name,
                            "lastName": mock_user.last_name,
                            "admin": mock_user.admin
                        }
                    mock_transform.side_effect = transform_side_effect
                    
                    response = await client.patch(f"/api/v1/users/{user_id}", json=update_data)
                    assert response.status_code == 200
                    
                    # Verify update was not called since admin field was removed and data became empty
                    mock_user.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_user_admin_only(self, client_admin):
        """Test deleting a user requires admin."""
        user_id = str(uuid.uuid4())
        
        mock_user = MagicMock()
        mock_user.id = user_id
        # Mock the instance delete method
        mock_user.delete = AsyncMock()
        
        with patch('routes.users.UsersDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            
            response = await client_admin.delete(f"/api/v1/users/{user_id}")
            assert response.status_code == 204
            mock_user.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, client_admin):
        """Test deleting non-existent user returns 404."""
        with patch('routes.users.UsersDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            response = await client_admin.delete("/api/v1/users/nonexistent")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_user_api_key_self(self, client, mock_auth_user):
        """Test users can get their own API key."""
        user_id = mock_auth_user.id
        
        mock_user = MagicMock()
        mock_user.api_key = "user-secret-key"
        
        with patch('routes.users.UsersDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            
            response = await client.get(f"/api/v1/users/{user_id}/api_key")
            assert response.status_code == 200
            data = response.json()
            assert data["apiKey"] == "user-secret-key"

    @pytest.mark.asyncio
    async def test_get_other_user_api_key_forbidden(self, client):
        """Test non-admin cannot get other users' API keys."""
        other_user_id = str(uuid.uuid4())
        
        response = await client.get(f"/api/v1/users/{other_user_id}/api_key")
        assert response.status_code == 403
        assert "not authorized to view" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_generate_api_key_self(self, client, mock_auth_user):
        """Test users can generate their own API key."""
        user_id = mock_auth_user.id
        
        mock_user = MagicMock()
        mock_user.id = user_id
        # Mock the instance update method
        mock_user.update = AsyncMock()
        
        with patch('routes.users.UsersDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            
            response = await client.post(f"/api/v1/users/{user_id}/api_key/generate")
            assert response.status_code == 200
            data = response.json()
            assert "apiKey" in data
            assert len(data["apiKey"]) == 36  # UUID format
            
            # Verify update was called with new key
            mock_user.update.assert_called_once()
            call_args = mock_user.update.call_args
            assert "api_key" in call_args[1]

    @pytest.mark.asyncio
    async def test_delete_api_key_self(self, client, mock_auth_user):
        """Test users can delete their own API key."""
        user_id = mock_auth_user.id
        
        mock_user = MagicMock()
        mock_user.id = user_id
        # Mock the instance update method
        mock_user.update = AsyncMock()
        
        with patch('routes.users.UsersDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            
            response = await client.delete(f"/api/v1/users/{user_id}/api_key")
            assert response.status_code == 200
            
            # Verify update was called with None
            mock_user.update.assert_called_once()
            call_args = mock_user.update.call_args
            assert call_args[1]["api_key"] is None

    @pytest.mark.asyncio
    async def test_admin_can_manage_other_users(self, client_admin):
        """Test admin can update/manage other users."""
        other_user_id = str(uuid.uuid4())
        update_data = {
            "firstName": "Admin",
            "lastName": "Updated",
            "admin": True
        }
        
        mock_user = MagicMock()
        mock_user.id = other_user_id
        mock_user.email = "other@test.com"
        mock_user.first_name = "Admin"
        mock_user.last_name = "Updated"
        mock_user.admin = True
        mock_user.api_key = "other-key"
        # Mock the instance update method
        mock_user.update = AsyncMock()
        
        with patch('routes.users.UsersDB.get', new_callable=AsyncMock) as mock_get:
            # Patch db.refresh to do nothing with mock objects
            with patch.object(AsyncSession, 'refresh', new=AsyncMock(return_value=None)):
                with patch('routes.users.UserService.transform_response', new_callable=AsyncMock) as mock_transform:
                    mock_get.return_value = mock_user
                    
                    # Mock transform to handle both 1 and 2 arguments
                    async def transform_side_effect(*args):
                        return {
                            "id": mock_user.id,
                            "email": mock_user.email,
                            "firstName": mock_user.first_name,
                            "lastName": mock_user.last_name,
                            "admin": mock_user.admin
                        }
                    mock_transform.side_effect = transform_side_effect
                    
                    response = await client_admin.patch(f"/api/v1/users/{other_user_id}", json=update_data)
                    assert response.status_code == 200
                    data = response.json()
                    assert data["admin"] is True
                    
                    # Admin should be able to update admin status
                    mock_user.update.assert_called_once()
                    call_args = mock_user.update.call_args
                    assert call_args[1]["admin"] is True