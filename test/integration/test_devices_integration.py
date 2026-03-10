"""
Integration tests for device API endpoints.
These tests run against a real API server to validate actual HTTP behavior.
All device endpoints require authentication; tests use test_user's api_key.
"""

import pytest
import httpx


def _auth_params(api_key):
    """Query params for API key authentication."""
    return {"api_key": api_key}


class TestDeviceEndpointsIntegration:
    """Test device API endpoints against running API."""

    def test_get_devices_empty(self, api_client, test_user):
        """Test getting devices when none exist."""
        response = api_client.get("/api/v1/devices", params=_auth_params(test_user["api_key"]))
        assert response.status_code == 200
        assert response.json() == []

    def test_create_and_get_device(self, api_client, test_user, sample_device_data):
        """Test creating a new device and retrieving it."""
        params = _auth_params(test_user["api_key"])
        response = api_client.post("/api/v1/devices", json=sample_device_data, params=params)
        assert response.status_code == 201
        assert response.json() == {"created": True}

        response = api_client.get("/api/v1/devices", params=params)
        assert response.status_code == 200
        devices = response.json()
        assert len(devices) == 1
        assert devices[0]["id"] == sample_device_data["id"]
        assert devices[0]["name"] == sample_device_data["name"]

        response = api_client.get(f"/api/v1/devices/{sample_device_data['id']}", params=params)
        assert response.status_code == 200
        device = response.json()
        assert device["id"] == sample_device_data["id"]
        assert device["mac"] == sample_device_data["mac"]
        assert "ports" in device
        assert "0" in device["ports"]

    def test_create_device_without_id_fails(self, api_client, test_user, sample_device_data):
        """Test that creating a device without an ID fails."""
        device_data = sample_device_data.copy()
        del device_data["id"]

        response = api_client.post(
            "/api/v1/devices", json=device_data, params=_auth_params(test_user["api_key"])
        )
        assert response.status_code == 422  # Validation error

    def test_create_duplicate_device_fails(self, api_client, test_user, sample_device_data):
        """Test that creating a duplicate device fails."""
        params = _auth_params(test_user["api_key"])
        response = api_client.post("/api/v1/devices", json=sample_device_data, params=params)
        assert response.status_code == 201

        response = api_client.post("/api/v1/devices", json=sample_device_data, params=params)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_duplicate_mac_fails(self, api_client, test_user, sample_device_data):
        """Test that creating a device with duplicate MAC address fails."""
        params = _auth_params(test_user["api_key"])
        response = api_client.post("/api/v1/devices", json=sample_device_data, params=params)
        assert response.status_code == 201

        device_data = sample_device_data.copy()
        device_data["id"] = "different-id"
        response = api_client.post("/api/v1/devices", json=device_data, params=params)
        assert response.status_code == 400
        assert "mac address" in response.json()["detail"].lower()

    def test_get_nonexistent_device(self, api_client, test_user):
        """Test getting a device that doesn't exist."""
        response = api_client.get(
            "/api/v1/devices/nonexistent-id", params=_auth_params(test_user["api_key"])
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_device_with_auth(self, api_client, create_test_user, sample_device_data):
        """Test updating a device with proper authentication."""
        user = create_test_user(api_key="test-update-key")
        params = _auth_params(user.api_key)
        headers = {"Authorization": f"Bearer {user.api_key}"}

        response = api_client.post("/api/v1/devices", json=sample_device_data, params=params)
        assert response.status_code == 201

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

        response = api_client.get(f"/api/v1/devices/{sample_device_data['id']}", headers=headers)
        assert response.status_code == 200
        device = response.json()
        assert device["name"] == "Updated Device Name"

    def test_patch_device_with_auth(self, api_client, create_test_user, sample_device_data):
        """Test partially updating a device with PATCH."""
        user = create_test_user(api_key="test-patch-key")
        params = _auth_params(user.api_key)
        headers = {"Authorization": f"Bearer {user.api_key}"}

        response = api_client.post("/api/v1/devices", json=sample_device_data, params=params)
        assert response.status_code == 201

        update_data = {"name": "Patched Device Name"}
        response = api_client.patch(
            f"/api/v1/devices/{sample_device_data['id']}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200
        assert response.json() == {"updated": True}

        response = api_client.get(f"/api/v1/devices/{sample_device_data['id']}", headers=headers)
        assert response.status_code == 200
        device = response.json()
        assert device["name"] == "Patched Device Name"
        assert device["model"] == sample_device_data["model"]  # Unchanged

    def test_create_kt200_device(self, api_client, test_user):
        """Test creating a KT-200 device with two ports."""
        params = _auth_params(test_user["api_key"])
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

        response = api_client.post("/api/v1/devices", json=kt200_data, params=params)
        assert response.status_code == 201

        response = api_client.get(f"/api/v1/devices/{kt200_data['id']}", params=params)
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

    def test_concurrent_device_creation(self, api_client, test_user):
        """Test creating multiple devices concurrently."""
        import concurrent.futures

        params = _auth_params(test_user["api_key"])

        def create_device(device_id, mac_suffix):
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
            response = api_client.post("/api/v1/devices", json=device_data, params=params)
            return response.status_code == 201

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(create_device, i, i)
                for i in range(5)
            ]
            results = [f.result() for f in futures]

        assert all(results)

        response = api_client.get("/api/v1/devices", params=params)
        assert response.status_code == 200
        devices = response.json()
        assert len(devices) == 5
        device_ids = {d["id"] for d in devices}
        expected_ids = {f"concurrent-{i}" for i in range(5)}
        assert device_ids == expected_ids

    def test_concurrent_reads(self, api_client, test_user, sample_device_data):
        """Test reading device data concurrently."""
        import concurrent.futures

        params = _auth_params(test_user["api_key"])
        response = api_client.post("/api/v1/devices", json=sample_device_data, params=params)
        assert response.status_code == 201

        def read_device():
            response = api_client.get(
                f"/api/v1/devices/{sample_device_data['id']}", params=params
            )
            return response.status_code == 200 and response.json()["id"] == sample_device_data["id"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_device) for _ in range(10)]
            results = [f.result() for f in futures]

        assert all(results)