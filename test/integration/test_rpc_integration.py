import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from db.devices import Device as DeviceDB
from db.ports import Port as PortDB
from db.users import User as UserDB


class TestRPCIntegration:
    """Integration tests for RPC endpoints."""
    
    @pytest.mark.asyncio
    async def test_reset_volume_full_flow(self, async_api_client, db_session, admin_user):
        """Test full flow of resetting volume on a device."""
        # Login as admin
        login_data = {"email": admin_user.email, "password": "admin123"}
        login_response = await async_api_client.post("/login", json=login_data)
        assert login_response.status_code == 200
        
        # Create a device
        device_data = {
            "id": "TEST001",
            "mac": "AA:BB:CC:DD:EE:FF",
            "portCnt": 1,
            "ports": {
                "0": {
                    "portIndex": 0,
                    "portName": "Original Name",
                    "displayUnit": "mL",
                    "kegSize": 10000,
                    "startVolume": 10000,
                    "volumeDispensed": 5000
                }
            }
        }
        
        create_response = await async_api_client.post("/api/v1/devices", json=device_data)
        assert create_response.status_code == 201
        
        # Mock the GATT operations
        with patch('kegtron.gatt.unlock', new_callable=AsyncMock) as mock_unlock, \
                patch('kegtron.gatt.write_chars', new_callable=AsyncMock) as mock_write:
            
            # Reset the volume
            reset_data = {
                "keg_size": 19000,  # ~5 gallons
                "start_volume": 19000,
                "unit": "mL"
            }
            
            reset_response = await async_api_client.post(
                "/api/v1/devices/TEST001/ports/0/rpc/Kegtron.ResetVolume",
                json=reset_data
            )
            assert reset_response.status_code == 200
            assert reset_response.json() == {"success": True}
            
            # Verify GATT operations were called
            mock_unlock.assert_called_once()
            mock_write.assert_called_once()
        
        # Verify the device was updated
        get_response = await async_api_client.get("/api/v1/devices/TEST001")
        assert get_response.status_code == 200
        device = get_response.json()
        port = device["ports"]["0"]
        assert port["kegSize"] == 19000
        assert port["startVolume"] == 19000
        assert port["volumeDispensed"] == 0
    
    @pytest.mark.asyncio
    async def test_set_port_name_full_flow(self, async_api_client, db_session, admin_user):
        """Test full flow of setting port name on a device."""
        # Login as admin
        login_data = {"email": admin_user.email, "password": "admin123"}
        login_response = await async_api_client.post("/login", json=login_data)
        assert login_response.status_code == 200
        
        # Create a device
        device_data = {
            "id": "TEST002",
            "mac": "11:22:33:44:55:66",
            "portCnt": 1,
            "ports": {
                "0": {
                    "portIndex": 0,
                    "portName": "",
                    "displayUnit": "mL"
                }
            }
        }
        
        create_response = await async_api_client.post("/api/v1/devices", json=device_data)
        assert create_response.status_code == 201
        
        # Mock the GATT operations
        with patch('kegtron.gatt.unlock', new_callable=AsyncMock) as mock_unlock, \
                patch('kegtron.gatt.write_chars', new_callable=AsyncMock) as mock_write:
            
            # Set the port name
            name_data = {"name": "IPA Keg"}
            
            name_response = await async_api_client.post(
                "/api/v1/devices/TEST002/ports/0/rpc/Kegtron.SetPortName",
                json=name_data
            )
            assert name_response.status_code == 200
            assert name_response.json() == {"success": True}
            
            # Verify GATT operations were called
            mock_unlock.assert_called_once()
            mock_write.assert_called_once()
            
            # Verify the correct data was written
            call_args = mock_write.call_args[0]
            write_data = call_args[1]
            assert 21 in write_data  # Port 0 name handle
            assert write_data[21] == b"IPA Keg             "
        
        # Verify the device was updated
        get_response = await async_api_client.get("/api/v1/devices/TEST002")
        assert get_response.status_code == 200
        device = get_response.json()
        port = device["ports"]["0"]
        assert port["portName"] == "IPA Keg"
    
    @pytest.mark.asyncio
    async def test_kt200_dual_port_operations(self, async_api_client, db_session, admin_user):
        """Test RPC operations on both ports of a KT-200 device."""
        # Login as admin
        login_data = {"email": admin_user.email, "password": "admin123"}
        login_response = await async_api_client.post("/login", json=login_data)
        assert login_response.status_code == 200
        
        # Create a KT-200 device
        device_data = {
            "id": "KT200-TEST",
            "mac": "99:88:77:66:55:44",
            "model": "KT-200",
            "portCnt": 2,
            "ports": {
                "0": {
                    "portIndex": 0,
                    "portName": "",
                    "displayUnit": "mL",
                    "kegSize": 0,
                    "startVolume": 0,
                    "volumeDispensed": 0
                },
                "1": {
                    "portIndex": 1,
                    "portName": "",
                    "displayUnit": "mL",
                    "kegSize": 0,
                    "startVolume": 0,
                    "volumeDispensed": 0
                }
            }
        }
        
        create_response = await async_api_client.post("/api/v1/devices", json=device_data)
        assert create_response.status_code == 201
        
        # Mock the GATT operations
        with patch('kegtron.gatt.unlock', new_callable=AsyncMock) as mock_unlock, \
                patch('kegtron.gatt.write_chars', new_callable=AsyncMock) as mock_write:
            
            # Set name on port 0
            name_data_0 = {"name": "Lager"}
            name_response_0 = await async_api_client.post(
                "/api/v1/devices/KT200-TEST/ports/0/rpc/Kegtron.SetPortName",
                json=name_data_0
            )
            assert name_response_0.status_code == 200
            
            # Set name on port 1
            name_data_1 = {"name": "Stout"}
            name_response_1 = await async_api_client.post(
                "/api/v1/devices/KT200-TEST/ports/1/rpc/Kegtron.SetPortName",
                json=name_data_1
            )
            assert name_response_1.status_code == 200
            
            # Verify correct handles were used
            assert mock_write.call_count == 2
            
            # Check port 0 write
            call_args_0 = mock_write.call_args_list[0][0]
            write_data_0 = call_args_0[1]
            assert 21 in write_data_0  # Port 0 handle
            assert write_data_0[21] == b"Lager               "
            
            # Check port 1 write  
            call_args_1 = mock_write.call_args_list[1][0]
            write_data_1 = call_args_1[1]
            assert 84 in write_data_1  # Port 1 handle
            assert write_data_1[84] == b"Stout               "
            
            # Reset volume on port 0
            mock_write.reset_mock()
            reset_data_0 = {"keg_size": 20000, "start_volume": 20000, "unit": "mL"}
            reset_response_0 = await async_api_client.post(
                "/api/v1/devices/KT200-TEST/ports/0/rpc/Kegtron.ResetVolume",
                json=reset_data_0
            )
            assert reset_response_0.status_code == 200
            
            # Reset volume on port 1
            reset_data_1 = {"keg_size": 40000, "start_volume": 40000, "unit": "mL"}
            reset_response_1 = await async_api_client.post(
                "/api/v1/devices/KT200-TEST/ports/1/rpc/Kegtron.ResetVolume",
                json=reset_data_1
            )
            assert reset_response_1.status_code == 200
        
        # Verify both ports were updated
        get_response = await async_api_client.get("/api/v1/devices/KT200-TEST")
        assert get_response.status_code == 200
        device = get_response.json()
        
        port_0 = device["ports"]["0"]
        assert port_0["portName"] == "Lager"
        assert port_0["kegSize"] == 20000
        assert port_0["startVolume"] == 20000
        
        port_1 = device["ports"]["1"]
        assert port_1["portName"] == "Stout"
        assert port_1["kegSize"] == 40000
        assert port_1["startVolume"] == 40000
    
    @pytest.mark.asyncio
    async def test_rpc_authentication_required(self, async_api_client, db_session):
        """Test that RPC endpoints require authentication."""
        # Create a device first (as admin)
        admin = await UserDB.create(
            db_session,
            email="temp_admin@test.com",
            password_hash="hashed",
            admin=True
        )
        await db_session.commit()
        
        login_data = {"email": "temp_admin@test.com", "password": "admin123"}
        # Mock password verification
        with patch('db.users.User.verify_password', return_value=True):
            login_response = await async_api_client.post("/login", json=login_data)
            assert login_response.status_code == 200
            
            device_data = {
                "id": "AUTH-TEST",
                "mac": "FF:EE:DD:CC:BB:AA",
                "portCnt": 1,
                "ports": {
                    "0": {"portIndex": 0, "portName": "Test", "displayUnit": "mL"}
                }
            }
            
            create_response = await async_api_client.post("/api/v1/devices", json=device_data)
            assert create_response.status_code == 201
            
            # Logout
            logout_response = await async_api_client.post("/logout")
            assert logout_response.status_code == 200
            
            # Try to reset volume without authentication
            reset_data = {"keg_size": 10000, "unit": "mL"}
            reset_response = await async_api_client.post(
                "/api/v1/devices/AUTH-TEST/ports/0/rpc/Kegtron.ResetVolume",
                json=reset_data
            )
            assert reset_response.status_code == 401
            
            # Try to set port name without authentication
            name_data = {"name": "New Name"}
            name_response = await async_api_client.post(
                "/api/v1/devices/AUTH-TEST/ports/0/rpc/Kegtron.SetPortName",
                json=name_data
            )
            assert name_response.status_code == 401

    @pytest.mark.asyncio
    async def test_rpc_with_different_units(self, async_api_client, db_session, admin_user):
        """Test RPC operations with different unit conversions."""
        # Login as admin
        login_data = {"email": admin_user.email, "password": "admin123"}
        login_response = await async_api_client.post("/login", json=login_data)
        if login_response.status_code != 200:
            raise Exception(f"Failed to login: {login_response.json()}")
        assert login_response.status_code == 200
        
        # Create a device
        device_data = {
            "id": "UNIT-TEST",
            "mac": "12:34:56:78:90:AB",
            "portCnt": 1,
            "ports": {
                "0": {
                    "portIndex": 0,
                    "portName": "Test Port",
                    "displayUnit": "gal",  # Set to gallons
                    "kegSize": 0,
                    "startVolume": 0,
                    "volumeDispensed": 0
                }
            }
        }
        
        create_response = await async_api_client.post("/api/v1/devices", json=device_data)
        assert create_response.status_code == 201
        
        # Mock the GATT operations
        with patch('kegtron.gatt.unlock', new_callable=AsyncMock), \
                patch('kegtron.gatt.write_chars', new_callable=AsyncMock) as mock_write:
            
            # Reset volume with gallons
            reset_data = {
                "keg_size": 5,  # 5 gallons
                "start_volume": 5,
                "unit": "gal"
            }
            
            reset_response = await async_api_client.post(
                "/api/v1/devices/UNIT-TEST/ports/0/rpc/Kegtron.ResetVolume",
                json=reset_data
            )
            assert reset_response.status_code == 200
            
            # Verify the conversion to mL was done correctly
            call_args = mock_write.call_args[0]
            write_data = call_args[1]
            # 5 gallons = ~18927 mL
            # Check that the values written are in the expected range
            assert any(18900 < int.from_bytes(value, 'little') < 19000 
                        for value in write_data.values() if len(value) == 2)
        
        # Verify the database stores values in mL
        get_response = await async_api_client.get("/api/v1/devices/UNIT-TEST")
        assert get_response.status_code == 200
        device = get_response.json()
        port = device["ports"]["0"]
        # Values should be stored in mL
        assert 18900 < port["kegSize"] < 19000  # ~5 gallons in mL
        assert 18900 < port["startVolume"] < 19000
    
    @pytest.mark.asyncio
    async def test_rpc_error_handling(self, async_api_client, db_session, admin_user):
        """Test error handling in RPC endpoints."""
        # Login as admin
        login_data = {"email": admin_user.email, "password": "admin123"}
        login_response = await async_api_client.post("/login", json=login_data)
        assert login_response.status_code == 200
        
        # Test non-existent device
        reset_data = {"keg_size": 10000, "unit": "mL"}
        response = await async_api_client.post(
            "/api/v1/devices/NONEXISTENT/ports/0/rpc/Kegtron.ResetVolume",
            json=reset_data
        )
        assert response.status_code == 404
        
        # Create a single-port device
        device_data = {
            "id": "SINGLE-PORT",
            "mac": "AB:CD:EF:12:34:56",
            "portCnt": 1,
            "ports": {
                "0": {
                    "portIndex": 0,
                    "portName": "Port 0",
                    "displayUnit": "mL"
                }
            }
        }
        
        create_response = await async_api_client.post("/api/v1/devices", json=device_data)
        assert create_response.status_code == 201
        
        # Test invalid port index
        response = await async_api_client.post(
            "/api/v1/devices/SINGLE-PORT/ports/1/rpc/Kegtron.ResetVolume",
            json=reset_data
        )
        assert response.status_code == 400
        assert "out of range" in response.json()["detail"]
        
        # Test invalid port index for SetPortName
        name_data = {"name": "Invalid"}
        response = await async_api_client.post(
            "/api/v1/devices/SINGLE-PORT/ports/2/rpc/Kegtron.SetPortName",
            json=name_data
        )
        assert response.status_code == 400
        assert "out of range" in response.json()["detail"]
        
        # Test missing required fields
        response = await async_api_client.post(
            "/api/v1/devices/SINGLE-PORT/ports/0/rpc/Kegtron.SetPortName",
            json={}
        )
        assert response.status_code == 422  # Validation error
        
        # Test invalid data types
        invalid_data = {"keg_size": "not_a_number", "unit": "mL"}
        response = await async_api_client.post(
            "/api/v1/devices/SINGLE-PORT/ports/0/rpc/Kegtron.ResetVolume",
            json=invalid_data
        )
        assert response.status_code == 422  # Validation error