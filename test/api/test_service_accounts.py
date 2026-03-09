"""Unit tests for service account API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from db.service_accounts import ServiceAccount as ServiceAccountDB
from dependencies.auth import AuthUser


class TestServiceAccountEndpoints:
    """Test service account API endpoints."""

    @pytest.mark.asyncio
    async def test_list_service_accounts_admin_only(self, client_admin):
        """Test listing service accounts requires admin."""
        mock_account1 = MagicMock()
        mock_account1.id = "1"
        mock_account1.name = "Service 1"
        mock_account1.admin = False
        mock_account1.api_key = "key1"
        
        mock_account2 = MagicMock()
        mock_account2.id = "2"
        mock_account2.name = "Service 2"
        mock_account2.admin = True
        mock_account2.api_key = "key2"
        
        mock_accounts = [mock_account1, mock_account2]
        
        with patch('routes.service_accounts.ServiceAccountsDB.list', new_callable=AsyncMock) as mock_list:
            with patch('routes.service_accounts.ServiceAccountService.transform_response', new_callable=AsyncMock) as mock_transform:
                mock_list.return_value = mock_accounts
                
                # Mock transform to return dict for each service account
                async def transform_side_effect(account):
                    return {
                        "id": account.id,
                        "name": account.name,
                        "admin": account.admin
                    }
                mock_transform.side_effect = transform_side_effect
                
                response = await client_admin.get("/api/v1/service_accounts")
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["name"] == "Service 1"
                assert data[1]["name"] == "Service 2"

    @pytest.mark.asyncio
    async def test_list_service_accounts_non_admin_forbidden(self, client):
        """Test non-admin cannot list service accounts."""
        response = await client.get("/api/v1/service_accounts")
        assert response.status_code == 403
        assert "not authorized to access" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_service_account_admin_only(self, client_admin):
        """Test creating a service account requires admin."""
        new_account_data = {
            "name": "New Service",
            "admin": False
        }
        
        mock_account = MagicMock()
        mock_account.id = str(uuid.uuid4())
        mock_account.name = "New Service"
        mock_account.admin = False
        mock_account.api_key = "generated-api-key"
        
        with patch('routes.service_accounts.ServiceAccountsDB.create', new_callable=AsyncMock) as mock_create:
            with patch('routes.service_accounts.ServiceAccountService.transform_response', new_callable=AsyncMock) as mock_transform:
                mock_create.return_value = mock_account
                mock_transform.return_value = {
                    "id": mock_account.id,
                    "name": mock_account.name,
                    "admin": mock_account.admin
                }
                
                response = await client_admin.post("/api/v1/service_accounts", json=new_account_data)
                assert response.status_code == 201
                data = response.json()
                assert data["name"] == "New Service"
                assert data["admin"] is False
                
                # Verify API key was generated
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert "api_key" in call_args[1]

    @pytest.mark.asyncio
    async def test_create_service_account_with_custom_api_key(self, client_admin):
        """Test creating a service account with custom API key."""
        custom_key = "custom-api-key-12345"
        new_account_data = {
            "name": "Custom Service",
            "admin": False,
            "apiKey": custom_key
        }
        
        mock_account = MagicMock()
        mock_account.id = str(uuid.uuid4())
        mock_account.name = "Custom Service"
        mock_account.admin = False
        mock_account.api_key = custom_key
        
        with patch('routes.service_accounts.ServiceAccountsDB.create', new_callable=AsyncMock) as mock_create:
            with patch('routes.service_accounts.ServiceAccountService.transform_response', new_callable=AsyncMock) as mock_transform:
                mock_create.return_value = mock_account
                mock_transform.return_value = {
                    "id": mock_account.id,
                    "name": mock_account.name,
                    "admin": mock_account.admin
                }
                
                response = await client_admin.post("/api/v1/service_accounts", json=new_account_data)
                assert response.status_code == 201
                data = response.json()
                
                # Verify custom API key was used
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert call_args[1]["api_key"] == custom_key

    @pytest.mark.asyncio
    async def test_get_service_account_admin_only(self, client_admin):
        """Test getting a specific service account requires admin."""
        account_id = str(uuid.uuid4())
        
        mock_account = MagicMock()
        mock_account.id = account_id
        mock_account.name = "Test Service"
        mock_account.admin = False
        mock_account.api_key = "test-key"
        
        with patch('routes.service_accounts.ServiceAccountsDB.get', new_callable=AsyncMock) as mock_get:
            with patch('routes.service_accounts.ServiceAccountService.transform_response', new_callable=AsyncMock) as mock_transform:
                mock_get.return_value = mock_account
                mock_transform.return_value = {
                    "id": mock_account.id,
                    "name": mock_account.name,
                    "admin": mock_account.admin
                }
                
                response = await client_admin.get(f"/api/v1/service_accounts/{account_id}")
                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "Test Service"

    @pytest.mark.asyncio
    async def test_get_nonexistent_service_account(self, client_admin):
        """Test getting non-existent service account returns 404."""
        with patch('routes.service_accounts.ServiceAccountsDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            response = await client_admin.get("/api/v1/service_accounts/nonexistent")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_service_account(self, client):
        """Test updating a service account."""
        account_id = str(uuid.uuid4())
        update_data = {
            "name": "Updated Service",
            "admin": True
        }
        
        mock_account = MagicMock()
        mock_account.id = account_id
        mock_account.name = "Updated Service"
        mock_account.admin = True
        mock_account.api_key = "test-key"
        
        # Mock the instance update method
        mock_account.update = AsyncMock()
        
        with patch('routes.service_accounts.ServiceAccountsDB.get', new_callable=AsyncMock) as mock_get:
            # Patch db.refresh to do nothing with mock objects
            with patch.object(AsyncSession, 'refresh', new=AsyncMock(return_value=None)):
                with patch('routes.service_accounts.ServiceAccountService.transform_response', new_callable=AsyncMock) as mock_transform:
                    mock_get.return_value = mock_account
                    
                    # Mock transform to handle both 1 and 2 arguments
                    async def transform_side_effect(*args):
                        return {
                            "id": mock_account.id,
                            "name": mock_account.name,
                            "admin": mock_account.admin
                        }
                    mock_transform.side_effect = transform_side_effect
                    
                    response = await client.patch(f"/api/v1/service_accounts/{account_id}", json=update_data)
                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "Updated Service"
                assert data["admin"] is True
                
                mock_account.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_nonexistent_service_account(self, client):
        """Test updating non-existent service account returns 404."""
        with patch('routes.service_accounts.ServiceAccountsDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            response = await client.patch("/api/v1/service_accounts/nonexistent", json={"name": "Updated"})
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_service_account_admin_only(self, client_admin):
        """Test deleting a service account requires admin."""
        account_id = str(uuid.uuid4())
        
        mock_account = MagicMock()
        mock_account.id = account_id
        
        # Mock the instance delete method
        mock_account.delete = AsyncMock()
        
        with patch('routes.service_accounts.ServiceAccountsDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_account
            
            response = await client_admin.delete(f"/api/v1/service_accounts/{account_id}")
            assert response.status_code == 204
            mock_account.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_service_account_non_admin_forbidden(self, client):
        """Test non-admin cannot delete service accounts."""
        response = await client.delete("/api/v1/service_accounts/some-id")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_generate_service_account_api_key(self, client):
        """Test generating new API key for service account."""
        account_id = str(uuid.uuid4())
        
        mock_account = MagicMock()
        mock_account.id = account_id
        
        # Mock the instance update method
        mock_account.update = AsyncMock()
        
        with patch('routes.service_accounts.ServiceAccountsDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_account
            
            response = await client.post(f"/api/v1/service_accounts/{account_id}/api_key/generate")
            assert response.status_code == 200
            data = response.json()
            assert "apiKey" in data
            assert len(data["apiKey"]) == 36  # UUID format
            
            # Verify update was called with new key
            mock_account.update.assert_called_once()
            call_args = mock_account.update.call_args
            assert "api_key" in call_args[1]

    @pytest.mark.asyncio
    async def test_generate_api_key_nonexistent_account(self, client):
        """Test generating API key for non-existent account returns 404."""
        with patch('routes.service_accounts.ServiceAccountsDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            response = await client.post("/api/v1/service_accounts/nonexistent/api_key/generate")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_service_account_api_key(self, client_admin):
        """Test deleting service account API key (admin only)."""
        account_id = str(uuid.uuid4())
        
        mock_account = MagicMock()
        mock_account.id = account_id
        
        # Mock the instance update method
        mock_account.update = AsyncMock()
        
        with patch('routes.service_accounts.ServiceAccountsDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_account
            
            response = await client_admin.delete(f"/api/v1/service_accounts/{account_id}/api_key")
            assert response.status_code == 204
            
            # Verify update was called with None
            mock_account.update.assert_called_once()
            call_args = mock_account.update.call_args
            assert call_args[1]["api_key"] is None

    @pytest.mark.asyncio
    async def test_delete_api_key_non_admin_forbidden(self, client):
        """Test non-admin cannot delete service account API keys."""
        account_id = str(uuid.uuid4())
        
        # Mock regular user (non-admin) in auth
        mock_account = MagicMock()
        mock_account.id = account_id
        
        with patch('routes.service_accounts.ServiceAccountsDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_account
            
            # Override the current user to be non-admin
            from api import api
            from dependencies.auth import require_user
            
            mock_user = AuthUser(
                id_="user-id",
                first_name="Regular",
                last_name="User",
                email="user@test.com",
                profile_pic=None,
                api_key="user-key",
                admin=False,  # Non-admin
                service_account=False,
                service_name=None
            )
            
            async def override_require_user():
                return mock_user
            
            api.dependency_overrides[require_user] = override_require_user
            
            response = await client.delete(f"/api/v1/service_accounts/{account_id}/api_key")
            assert response.status_code == 403
            assert "not authorized to delete" in response.json()["detail"].lower()
            
            # Clean up override
            del api.dependency_overrides[require_user]

    @pytest.mark.asyncio
    async def test_admin_can_delete_api_key(self, client_admin):
        """Test admin can delete service account API keys."""
        account_id = str(uuid.uuid4())
        
        mock_account = MagicMock()
        mock_account.id = account_id
        
        # Mock the instance update method
        mock_account.update = AsyncMock()
        
        with patch('routes.service_accounts.ServiceAccountsDB.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_account
            
            response = await client_admin.delete(f"/api/v1/service_accounts/{account_id}/api_key")
            assert response.status_code == 204
            
            # Admin should be able to delete
            mock_account.update.assert_called_once()
            call_args = mock_account.update.call_args
            assert call_args[1]["api_key"] is None