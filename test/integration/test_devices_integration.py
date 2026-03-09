"""
Integration tests for device API endpoints.
These tests run against a real API server to validate actual HTTP behavior.
"""

import pytest
import httpx


class TestDeviceEndpointsIntegration:
    """Test device API endpoints against running API."""
    
    def test_get_devices_empty(self, api_client):
        """Test getting devices when none exist."""
        response = api_client.get("/api/v1/devices")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_create_and_get_device(self, api_client, sample_device_data):
        """Test creating a new device and retrieving it."""
        # Create device
        response = api_client.post("/api/v1/devices", json=sample_device_data)
        assert response.status_code == 201
        assert response.json() == {"created": True}
        
        # Get all devices
        response = api_client.get("/api/v1/devices")
        assert response.status_code == 200
        devices = response.json()
        assert len(devices) == 1
        assert devices[0]["id"] == sample_device_data["id"]
        assert devices[0]["name"] == sample_device_data["name"]
        
        # Get specific device
        response = api_client.get(f"/api/v1/devices/{sample_device_data['id']}")
        assert response.status_code == 200
        device = response.json()
        assert device["id"] == sample_device_data["id"]
        assert device["mac"] == sample_device_data["mac"]
        assert "ports" in device
        assert "0" in device["ports"]
    
    def test_create_device_without_id_fails(self, api_client, sample_device_data):
        """Test that creating a device without an ID fails."""
        device_data = sample_device_data.copy()
        del device_data["id"]
        
        response = api_client.post("/api/v1/devices", json=device_data)
        assert response.status_code == 422  # Validation error
    
    def test_create_duplicate_device_fails(self, api_client, sample_device_data):
        """Test that creating a duplicate device fails."""
        # Create first device
        response = api_client.post("/api/v1/devices", json=sample_device_data)
        assert response.status_code == 201
        
        # Try to create duplicate
        response = api_client.post("/api/v1/devices", json=sample_device_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_create_duplicate_mac_fails(self, api_client, sample_device_data):
        """Test that creating a device with duplicate MAC address fails."""
        # Create first device
        response = api_client.post("/api/v1/devices", json=sample_device_data)
        assert response.status_code == 201
        
        # Try to create device with same MAC but different ID
        device_data = sample_device_data.copy()
        device_data["id"] = "different-id"
        response = api_client.post("/api/v1/devices", json=device_data)
        assert response.status_code == 400
        assert "mac address" in response.json()["detail"].lower()
    
    def test_get_nonexistent_device(self, api_client):
        """Test getting a device that doesn't exist."""
        response = api_client.get("/api/v1/devices/nonexistent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_update_device_with_auth(self, api_client, create_test_user, sample_device_data):
        """Test updating a device with proper authentication."""
        # Create user
        user = create_test_user(api_key="test-update-key")
        
        # Create device
        response = api_client.post("/api/v1/devices", json=sample_device_data)
        assert response.status_code == 201
        
        # Update device with authentication
        headers = {"Authorization": f"Bearer {user.api_key}"}
        update_data = {
            "id": sample_device_data["id"],
            "name": "Updated Device Name"
        }
        response = api_client.put(
            f"/api/v1/devices/{sample_device_data['id']}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200
        assert response.json() == {"updated": True}
        
        # Verify update
        response = api_client.get(f"/api/v1/devices/{sample_device_data['id']}")
        assert response.status_code == 200
        device = response.json()
        assert device["name"] == "Updated Device Name"
    
    def test_patch_device_with_auth(self, api_client, create_test_user, sample_device_data):
        """Test partially updating a device with PATCH."""
        # Create user
        user = create_test_user(api_key="test-patch-key")
        
        # Create device
        response = api_client.post("/api/v1/devices", json=sample_device_data)
        assert response.status_code == 201
        
        # Patch device with authentication
        headers = {"Authorization": f"Bearer {user.api_key}"}
        update_data = {"name": "Patched Device Name"}
        response = api_client.patch(
            f"/api/v1/devices/{sample_device_data['id']}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200
        assert response.json() == {"updated": True}
        
        # Verify update - other fields should be unchanged
        response = api_client.get(f"/api/v1/devices/{sample_device_data['id']}")
        assert response.status_code == 200
        device = response.json()
        assert device["name"] == "Patched Device Name"
        assert device["model"] == sample_device_data["model"]  # Unchanged
    
    def test_create_kt200_device(self, api_client):
        """Test creating a KT-200 device with two ports."""
        kt200_data = {
            "id": "test-kt200",
            "name": "Test KT-200",
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
        
        response = api_client.post("/api/v1/devices", json=kt200_data)
        assert response.status_code == 201
        
        # Verify device and ports were created
        response = api_client.get(f"/api/v1/devices/{kt200_data['id']}")
        assert response.status_code == 200
        device = response.json()
        assert device["model"] == "KT-200"
        assert device["portCnt"] == 2
        assert len(device["ports"]) == 2
        assert "0" in device["ports"]
        assert "1" in device["ports"]
        assert device["ports"]["0"]["portName"] == "Port 0"
        assert device["ports"]["1"]["portName"] == "Port 1"


class TestDeviceConcurrency:
    """Test concurrent device operations against running API."""
    
    def test_concurrent_device_creation(self, api_client):
        """Test creating multiple devices concurrently."""
        import concurrent.futures
        
        def create_device(device_id, mac_suffix):
            """Helper to create a device."""
            device_data = {
                "id": f"concurrent-{device_id}",
                "name": f"Device {device_id}",
                "model": "KT-100",
                "mac": f"AA:BB:CC:DD:EE:{mac_suffix:02X}",
                "portCnt": 1,
                "ports": {
                    "0": {
                        "portIndex": 0,
                        "portName": f"Port for Device {device_id}",
                        "kegSize": 19000,
                        "startVolume": 19000,
                        "volumeDispensed": 0,
                        "displayUnit": "mL",
                        "configured": True
                    }
                }
            }
            response = api_client.post("/api/v1/devices", json=device_data)
            return response.status_code == 201
        
        # Create 5 devices concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(create_device, i, i)
                for i in range(5)
            ]
            results = [f.result() for f in futures]
        
        # All should succeed
        assert all(results)
        
        # Verify all were created
        response = api_client.get("/api/v1/devices")
        assert response.status_code == 200
        devices = response.json()
        assert len(devices) == 5
        device_ids = {d["id"] for d in devices}
        expected_ids = {f"concurrent-{i}" for i in range(5)}
        assert device_ids == expected_ids
    
    def test_concurrent_reads(self, api_client, sample_device_data):
        """Test reading device data concurrently."""
        import concurrent.futures
        
        # Create a device
        response = api_client.post("/api/v1/devices", json=sample_device_data)
        assert response.status_code == 201
        
        def read_device():
            """Helper to read device data."""
            response = api_client.get(f"/api/v1/devices/{sample_device_data['id']}")
            return response.status_code == 200 and response.json()["id"] == sample_device_data["id"]
        
        # Read device 10 times concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_device) for _ in range(10)]
            results = [f.result() for f in futures]
        
        # All reads should succeed
        assert all(results)