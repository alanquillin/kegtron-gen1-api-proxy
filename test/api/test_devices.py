import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from db.devices import Device as DeviceDB
from db.ports import Port as PortDB


def convert_device_data_for_db(device_data):
    """Convert API device data to database format."""
    device_copy = device_data.copy()
    ports_data = device_copy.pop("ports", {})
    
    # Convert camelCase to snake_case for database
    db_device_data = {
        "id": device_copy["id"],
        "name": device_copy.get("name"),
        "model": device_copy.get("model"),
        "mac": device_copy["mac"],
        "port_cnt": device_copy.get("portCnt", 1)
    }
    
    db_ports_data = []
    for port_idx, port in ports_data.items():
        db_port_data = {
            "port_index": port["portIndex"],
            "port_name": port.get("portName"),
            "keg_size": port.get("kegSize", 0),
            "start_volume": port.get("startVolume", 0),
            "volume_dispensed": port.get("volumeDispensed", 0),
            "display_unit": port.get("displayUnit", "mL"),
            "configured": port.get("configured", True)
        }
        db_ports_data.append(db_port_data)
    
    return db_device_data, db_ports_data


class TestDeviceEndpoints:
    """Test device API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_devices_empty(self, client):
        """Test getting devices when none exist."""
        response = await client.get("/api/v1/devices")
        assert response.status_code == 200
        assert response.json() == []
    
    @pytest.mark.asyncio
    async def test_get_devices_with_data(self, client, async_db_session, sample_device_data):
        """Test getting devices when they exist."""
        # Create a device in the database
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        response = await client.get("/api/v1/devices")
        assert response.status_code == 200
        devices = response.json()
        assert len(devices) == 1
        assert devices[0]["id"] == sample_device_data["id"]
    
    @pytest.mark.asyncio
    async def test_create_device(self, client, sample_device_data):
        """Test creating a new device."""
        response = await client.post("/api/v1/devices", json=sample_device_data)
        assert response.status_code == 201
        assert response.json() == {"created": True}
        
        # Verify device was created
        response = await client.get(f"/api/v1/devices/{sample_device_data['id']}")
        assert response.status_code == 200
        device = response.json()
        assert device["id"] == sample_device_data["id"]
        assert device["name"] == sample_device_data["name"]
        assert "ports" in device
    
    @pytest.mark.asyncio
    async def test_create_device_without_id(self, client, sample_device_data):
        """Test creating a device without an ID fails."""
        device_data = sample_device_data.copy()
        del device_data["id"]
        
        response = await client.post("/api/v1/devices", json=device_data)
        assert response.status_code == 422  # Pydantic validation error
        # The error detail will be in validation error format
        assert "id" in str(response.json()).lower()
    
    @pytest.mark.asyncio
    async def test_create_duplicate_device(self, client, sample_device_data):
        """Test creating a duplicate device fails."""
        # Create first device
        response = await client.post("/api/v1/devices", json=sample_device_data)
        assert response.status_code == 201
        
        # Try to create duplicate
        response = await client.post("/api/v1/devices", json=sample_device_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_device_duplicate_mac(self, client, sample_device_data):
        """Test creating a device with duplicate MAC address fails."""
        # Create first device
        response = await client.post("/api/v1/devices", json=sample_device_data)
        assert response.status_code == 201
        
        # Try to create device with same MAC
        device_data = sample_device_data.copy()
        device_data["id"] = "different-id"
        response = await client.post("/api/v1/devices", json=device_data)
        assert response.status_code == 400
        assert "mac address" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_device_by_id(self, client, async_db_session, sample_device_data):
        """Test getting a specific device by ID."""
        # Create a device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        response = await client.get(f"/api/v1/devices/{sample_device_data['id']}")
        assert response.status_code == 200
        device = response.json()
        assert device["id"] == sample_device_data["id"]
        assert device["mac"] == sample_device_data["mac"]
        assert "ports" in device
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_device(self, client):
        """Test getting a device that doesn't exist."""
        response = await client.get("/api/v1/devices/nonexistent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_update_device_put(self, client, async_db_session, sample_device_data):
        """Test updating a device with PUT."""
        # Create a device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Update the device
        update_data = {
            "id": sample_device_data["id"],
            "name": "Updated Name"
        }
        
        response = await client.put(f"/api/v1/devices/{sample_device_data['id']}", json=update_data)
        assert response.status_code == 200
        assert response.json() == {"updated": True}
        
        # Verify update
        response = await client.get(f"/api/v1/devices/{sample_device_data['id']}")
        device = response.json()
        assert device["name"] == "Updated Name"
    
    @pytest.mark.asyncio
    async def test_update_device_patch(self, client, async_db_session, sample_device_data):
        """Test partially updating a device with PATCH."""
        # Create a device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Partial update
        update_data = {"name": "Partially Updated"}
        
        response = await client.patch(f"/api/v1/devices/{sample_device_data['id']}", json=update_data)
        assert response.status_code == 200
        assert response.json() == {"updated": True}
        
        # Verify update
        response = await client.get(f"/api/v1/devices/{sample_device_data['id']}")
        device = response.json()
        assert device["name"] == "Partially Updated"
        assert device["model"] == sample_device_data["model"]  # Unchanged
    
    @pytest.mark.asyncio
    async def test_patch_nonexistent_device(self, client):
        """Test patching a device that doesn't exist."""
        update_data = {"name": "Updated"}
        response = await client.patch("/api/v1/devices/nonexistent-id", json=update_data)
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_kt200_device(self, client, sample_device_kt200_data):
        """Test creating a KT-200 device with two ports."""
        response = await client.post("/api/v1/devices", json=sample_device_kt200_data)
        assert response.status_code == 201
        
        # Verify device and ports were created
        response = await client.get(f"/api/v1/devices/{sample_device_kt200_data['id']}")
        assert response.status_code == 200
        device = response.json()
        assert device["model"] == "KT-200"
        assert device["portCnt"] == 2
        assert len(device["ports"]) == 2
        
        # Verify port indices
        port_indices = [port["portIndex"] for port in device["ports"].values()]
        assert 0 in port_indices
        assert 1 in port_indices