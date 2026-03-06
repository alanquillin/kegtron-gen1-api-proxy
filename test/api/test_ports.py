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


class TestPortEndpoints:
    """Test port API endpoints."""
    
    @pytest.mark.asyncio
    async def test_update_port(self, client, async_db_session, sample_device_data):
        """Test updating a port."""
        # Create a device with ports
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Update port
        update_data = {
            "port_name": "Updated Port Name",
            "display_unit": "gal"
        }
        
        response = await client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json=update_data
        )
        assert response.status_code == 200
        assert response.json() == {"updated": True}
        
        # Verify update through API (different session)
        response = await client.get(f"/api/v1/devices/{device.id}")
        assert response.status_code == 200
        device_data = response.json()
        # Ports are returned as a dict with string keys in the API response
        port_data = device_data["ports"]["0"]
        assert port_data["portName"] == "Updated Port Name"
        assert port_data["displayUnit"] == "gal"
    
    @pytest.mark.asyncio
    async def test_update_port_normalize_units(self, client, async_db_session, sample_device_data):
        """Test that display units are normalized (ml -> mL, l -> L)."""
        # Create a device with ports
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Test ml -> mL normalization
        update_data = {"display_unit": "ml"}
        response = await client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json=update_data
        )
        assert response.status_code == 200
        
        # Verify through API
        response = await client.get(f"/api/v1/devices/{device.id}")
        device_data = response.json()
        assert device_data["ports"]["0"]["displayUnit"] == "mL"
        
        # Test l -> L normalization  
        update_data = {"display_unit": "l"}
        response = await client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json=update_data
        )
        assert response.status_code == 200
        
        # Verify through API
        response = await client.get(f"/api/v1/devices/{device.id}")
        device_data = response.json()
        assert device_data["ports"]["0"]["displayUnit"] == "L"
    
    @pytest.mark.asyncio
    async def test_update_port_invalid_unit(self, client, async_db_session, sample_device_data):
        """Test updating a port with invalid display unit."""
        # Create a device with ports
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Try to update with invalid unit
        update_data = {"display_unit": "invalid"}
        
        response = await client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json=update_data
        )
        assert response.status_code == 404  # Note: API returns 404 for invalid unit
        assert "Invalid display unit" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_port(self, client, async_db_session, sample_device_data):
        """Test updating a port that doesn't exist."""
        # Create a device with ports
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Try to update non-existent port index
        update_data = {"port_name": "Updated"}
        
        response = await client.patch(
            f"/api/v1/devices/{device.id}/ports/99",
            json=update_data
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_update_port_nonexistent_device(self, client):
        """Test updating a port for a device that doesn't exist."""
        update_data = {"port_name": "Updated"}
        
        response = await client.patch(
            "/api/v1/devices/nonexistent-device/ports/0",
            json=update_data
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_kt200_ports(self, client, async_db_session, sample_device_kt200_data):
        """Test updating ports on a KT-200 device."""
        # Create KT-200 device with two ports
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_kt200_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Update port 0
        update_data_0 = {
            "port_name": "Beer Keg",
            "display_unit": "oz"
        }
        response = await client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json=update_data_0
        )
        assert response.status_code == 200
        
        # Update port 1
        update_data_1 = {
            "port_name": "Cider Keg",
            "display_unit": "L"
        }
        response = await client.patch(
            f"/api/v1/devices/{device.id}/ports/1",
            json=update_data_1
        )
        assert response.status_code == 200
        
        # Verify both updates through API
        response = await client.get(f"/api/v1/devices/{device.id}")
        assert response.status_code == 200
        device_data = response.json()
        
        port_0_data = device_data["ports"]["0"]
        assert port_0_data["portName"] == "Beer Keg"
        assert port_0_data["displayUnit"] == "oz"
        
        port_1_data = device_data["ports"]["1"]
        assert port_1_data["portName"] == "Cider Keg"
        assert port_1_data["displayUnit"] == "L"
    
    @pytest.mark.asyncio 
    async def test_update_port_volume_values(self, client, async_db_session, sample_device_data):
        """Test updating port volume values."""
        # Create a device with ports
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Update volume values
        update_data = {
            "keg_size": 20000,
            "start_volume": 20000,
            "volume_dispensed": 1500
        }
        
        response = await client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json=update_data
        )
        assert response.status_code == 200
        
        # Verify update through API
        response = await client.get(f"/api/v1/devices/{device.id}")
        assert response.status_code == 200
        device_data = response.json()
        port_data = device_data["ports"]["0"]
        assert port_data["kegSize"] == 20000
        assert port_data["startVolume"] == 20000
        assert port_data["volumeDispensed"] == 1500
    
    @pytest.mark.asyncio
    async def test_update_port_partial(self, client, async_db_session, sample_device_data):
        """Test partial update of port (only some fields)."""
        # Create a device with ports
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Get original values from what we created
        original_name = db_ports_data[0]["port_name"]
        original_keg_size = db_ports_data[0]["keg_size"]
        
        # Update only volume_dispensed
        update_data = {"volume_dispensed": 2000}
        
        response = await client.patch(
            f"/api/v1/devices/{device.id}/ports/0",
            json=update_data
        )
        assert response.status_code == 200
        
        # Verify only specified field was updated through API
        response = await client.get(f"/api/v1/devices/{device.id}")
        assert response.status_code == 200
        device_data = response.json()
        port_data = device_data["ports"]["0"]
        assert port_data["volumeDispensed"] == 2000
        assert port_data["portName"] == original_name  # Unchanged
        assert port_data["kegSize"] == original_keg_size  # Unchanged