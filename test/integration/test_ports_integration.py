"""
Integration tests for port API endpoints.
These tests run against a real API server to validate actual HTTP behavior.
"""

import pytest
import httpx


class TestPortEndpointsIntegration:
    """Test port API endpoints against running API."""
    
    def test_update_port_with_auth(self, api_client, create_test_user, create_test_device):
        """Test updating a port with authentication."""
        # Create user
        user = create_test_user(api_key="port-update-key")
        
        # Create device with port
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
        
        # Update port with authentication
        headers = {"Authorization": f"Bearer {user.api_key}"}
        update_data = {
            "port_name": "Updated Port Name",
            "display_unit": "gal"
        }
        response = api_client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200
        assert response.json() == {"updated": True}

        # Verify update
        response = api_client.get(f"/api/v1/devices/{device.id}", headers=headers)
        assert response.status_code == 200
        device_data = response.json()
        port_data = device_data["ports"]["0"]
        assert port_data["portName"] == "Updated Port Name"
        assert port_data["displayUnit"] == "gal"
    
    def test_update_port_normalize_units(self, api_client, create_test_user, create_test_device):
        """Test that display units are normalized (ml -> mL, l -> L)."""
        # Create user
        user = create_test_user(api_key="normalize-key")
        
        # Create device with port
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
        
        headers = {"Authorization": f"Bearer {user.api_key}"}
        
        # Test ml -> mL normalization
        response = api_client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json={"display_unit": "ml"},
            headers=headers
        )
        assert response.status_code == 200

        # Verify normalization
        response = api_client.get(f"/api/v1/devices/{device.id}", headers=headers)
        device_data = response.json()
        assert device_data["ports"]["0"]["displayUnit"] == "mL"

        # Test l -> L normalization
        response = api_client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json={"display_unit": "l"},
            headers=headers
        )
        assert response.status_code == 200

        # Verify normalization
        response = api_client.get(f"/api/v1/devices/{device.id}", headers=headers)
        device_data = response.json()
        assert device_data["ports"]["0"]["displayUnit"] == "L"

    def test_update_port_invalid_unit(self, api_client, create_test_user, create_test_device):
        """Test updating a port with invalid display unit."""
        # Create user
        user = create_test_user(api_key="invalid-unit-key")
        
        # Create device with port
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
        
        # Try to update with invalid unit
        headers = {"Authorization": f"Bearer {user.api_key}"}
        response = api_client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json={"display_unit": "invalid"},
            headers=headers
        )
        assert response.status_code == 404  # API returns 404 for invalid unit
        assert "Invalid display unit" in response.json()["detail"]
    
    def test_update_nonexistent_port(self, api_client, create_test_user, create_test_device):
        """Test updating a port that doesn't exist."""
        # Create user
        user = create_test_user(api_key="nonexistent-port-key")
        
        # Create device with one port
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
        
        # Try to update non-existent port index
        headers = {"Authorization": f"Bearer {user.api_key}"}
        response = api_client.patch(
            f"/api/v1/devices/{device.id}/ports/99",
            json={"port_name": "Should Fail"},
            headers=headers
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_update_port_nonexistent_device(self, api_client, create_test_user):
        """Test updating a port for a device that doesn't exist."""
        # Create user
        user = create_test_user(api_key="no-device-key")
        
        # Try to update port on non-existent device
        headers = {"Authorization": f"Bearer {user.api_key}"}
        response = api_client.patch(
            "/api/v1/devices/nonexistent-device/ports/0",
            json={"port_name": "Should Fail"},
            headers=headers
        )
        assert response.status_code == 404
    
    def test_update_kt200_ports(self, api_client, create_test_user, create_test_device):
        """Test updating ports on a KT-200 device."""
        # Create user
        user = create_test_user(api_key="kt200-key")
        
        # Create KT-200 device with two ports
        device = create_test_device(
            device_id="kt200-test",
            model="KT-200",
            port_cnt=2,
            ports=[
                {
                    "port_index": 0,
                    "port_name": "Port 0",
                    "keg_size": 19000,
                    "start_volume": 19000,
                    "volume_dispensed": 500,
                    "display_unit": "mL",
                    "configured": True
                },
                {
                    "port_index": 1,
                    "port_name": "Port 1",
                    "keg_size": 38000,
                    "start_volume": 38000,
                    "volume_dispensed": 1000,
                    "display_unit": "mL",
                    "configured": True
                }
            ]
        )
        
        headers = {"Authorization": f"Bearer {user.api_key}"}
        
        # Update port 0
        response = api_client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json={"port_name": "Beer Keg", "display_unit": "oz"},
            headers=headers
        )
        assert response.status_code == 200
        
        # Update port 1
        response = api_client.patch(
            f"/api/v1/devices/{device.id}/ports/1",
            json={"port_name": "Cider Keg", "display_unit": "L"},
            headers=headers
        )
        assert response.status_code == 200

        # Verify both updates
        response = api_client.get(f"/api/v1/devices/{device.id}", headers=headers)
        assert response.status_code == 200
        device_data = response.json()

        assert device_data["ports"]["0"]["portName"] == "Beer Keg"
        assert device_data["ports"]["0"]["displayUnit"] == "oz"
        assert device_data["ports"]["1"]["portName"] == "Cider Keg"
        assert device_data["ports"]["1"]["displayUnit"] == "L"
    
    def test_update_port_volume_values(self, api_client, create_test_user, create_test_device):
        """Test updating port volume values."""
        # Create user
        user = create_test_user(api_key="volume-key")
        
        # Create device with port
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
        
        # Update volume values
        headers = {"Authorization": f"Bearer {user.api_key}"}
        update_data = {
            "keg_size": 20000,
            "start_volume": 20000,
            "volume_dispensed": 1500
        }
        response = api_client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200

        # Verify update
        response = api_client.get(f"/api/v1/devices/{device.id}", headers=headers)
        assert response.status_code == 200
        device_data = response.json()
        port_data = device_data["ports"]["0"]
        assert port_data["kegSize"] == 20000
        assert port_data["startVolume"] == 20000
        assert port_data["volumeDispensed"] == 1500
    
    def test_partial_port_update(self, api_client, create_test_user, create_test_device):
        """Test partial update of port (only some fields)."""
        # Create user
        user = create_test_user(api_key="partial-key")
        
        # Create device with port
        device = create_test_device(
            ports=[{
                "port_index": 0,
                "port_name": "Original Name",
                "keg_size": 19000,
                "start_volume": 19000,
                "volume_dispensed": 0,
                "display_unit": "mL",
                "configured": True
            }]
        )
        
        # Update only volume_dispensed
        headers = {"Authorization": f"Bearer {user.api_key}"}
        response = api_client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json={"volume_dispensed": 2000},
            headers=headers
        )
        assert response.status_code == 200

        # Verify only specified field was updated
        response = api_client.get(f"/api/v1/devices/{device.id}", headers=headers)
        assert response.status_code == 200
        device_data = response.json()
        port_data = device_data["ports"]["0"]
        assert port_data["volumeDispensed"] == 2000
        assert port_data["portName"] == "Original Name"  # Unchanged
        assert port_data["kegSize"] == 19000  # Unchanged


class TestPortConcurrency:
    """Test concurrent port operations against running API."""
    
    def test_concurrent_port_updates(self, api_client, create_test_user, create_test_device):
        """Test updating multiple ports concurrently."""
        import concurrent.futures
        
        # Create users
        users = [
            create_test_user(email=f"port-user{i}@example.com", api_key=f"port-key-{i}")
            for i in range(3)
        ]
        
        # Create device with multiple ports
        device = create_test_device(
            device_id="concurrent-ports",
            model="KT-200",
            port_cnt=3,
            ports=[
                {
                    "port_index": i,
                    "port_name": f"Port {i}",
                    "keg_size": 19000,
                    "start_volume": 19000,
                    "volume_dispensed": 0,
                    "display_unit": "mL",
                    "configured": True
                }
                for i in range(3)
            ]
        )
        
        def update_port(user_key, port_index, name):
            """Helper to update a port."""
            headers = {"Authorization": f"Bearer {user_key}"}
            response = api_client.patch(
                f"/api/v1/devices/{device.id}/ports/{port_index}",
                json={"port_name": name},
                headers=headers
            )
            return response.status_code == 200
        
        # Update ports concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(update_port, users[i].api_key, i, f"Updated Port {i}")
                for i in range(3)
            ]
            results = [f.result() for f in futures]
        
        # All updates should succeed
        assert all(results)

        # Verify all updates were applied
        headers = {"Authorization": f"Bearer {users[0].api_key}"}
        response = api_client.get(f"/api/v1/devices/{device.id}", headers=headers)
        assert response.status_code == 200
        device_data = response.json()
        for i in range(3):
            assert device_data["ports"][str(i)]["portName"] == f"Updated Port {i}"