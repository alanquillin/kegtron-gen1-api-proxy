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


class TestRPCEndpoints:
    """Test RPC API endpoints."""
    
    @pytest.mark.asyncio
    async def test_unlock_write_all(self, client, async_db_session, sample_device_data, mock_gatt):
        """Test unlocking all ports for writing."""
        # Create a device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Call unlock write all
        response = await client.post(f"/api/v1/devices/{device.id}/rpc/Kegtron.UnlockWriteAll")
        assert response.status_code == 200
        assert response.json() == {"success": True}
        
        # Verify gatt.unlock_all was called
        mock_gatt.unlock_all.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_unlock_write_all_nonexistent_device(self, client, mock_gatt):
        """Test unlocking write all for a device that doesn't exist."""
        response = await client.post("/api/v1/devices/nonexistent/rpc/Kegtron.UnlockWriteAll")
        assert response.status_code == 404
        assert "Unknown device" in response.json()["detail"]
        mock_gatt.unlock_all.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_unlock_write_single_port(self, client, async_db_session, sample_device_data, mock_gatt):
        """Test unlocking a single port for writing."""
        # Create a device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Call unlock write for port 0
        response = await client.post(f"/api/v1/devices/{device.id}/port/0/rpc/Kegtron.UnlockWrite")
        assert response.status_code == 200
        assert response.json() == {"success": True}
        
        # Verify gatt.unlock was called with correct port
        mock_gatt.unlock.assert_called_once()
        call_args = mock_gatt.unlock.call_args
        assert call_args[0][1] == 0  # port_index
    
    @pytest.mark.asyncio
    async def test_unlock_write_kt200_ports(self, client, async_db_session, sample_device_kt200_data, mock_gatt):
        """Test unlocking ports on a KT-200 device."""
        # Create KT-200 device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_kt200_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Unlock port 0
        response = await client.post(f"/api/v1/devices/{device.id}/port/0/rpc/Kegtron.UnlockWrite")
        assert response.status_code == 200
        
        # Unlock port 1
        response = await client.post(f"/api/v1/devices/{device.id}/port/1/rpc/Kegtron.UnlockWrite")
        assert response.status_code == 200
        
        # Verify both calls were made
        assert mock_gatt.unlock.call_count == 2
    
    @pytest.mark.asyncio
    async def test_reset_volume_basic(self, client, async_db_session, sample_device_data, mock_gatt):
        """Test resetting volume on a port."""
        # Create a device with initial volume dispensed
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        db_ports_data[0]["volume_dispensed"] = 5000  # Start with some volume dispensed
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Mock the gatt write_chars
        with patch('routes.rpc.gatt.write_chars', new_callable=AsyncMock) as mock_write:
            # Reset volume
            reset_data = {
                "keg_size": 19000,
                "start_volume": 19000,
                "unit": "mL"
            }
            
            response = await client.post(
                f"/api/v1/devices/{device.id}/port/0/rpc/Kegtron.ResetVolume",
                json=reset_data
            )
            assert response.status_code == 200
            assert response.json() == {"success": True}
            
            # Verify unlock was called
            mock_gatt.unlock.assert_called_once()
            
            # Verify write_chars was called
            mock_write.assert_called_once()
        
        # Verify database was updated
        port = await PortDB.get_by_device_id_and_index(device.id, 0, async_db_session)
        assert port.volume_dispensed == 0
        assert port.keg_size == 19000
        assert port.start_volume == 19000
    
    @pytest.mark.asyncio
    async def test_reset_volume_with_units(self, client, async_db_session, sample_device_data, mock_gatt):
        """Test resetting volume with different units."""
        # Create a device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        with patch('routes.rpc.gatt.write_chars', new_callable=AsyncMock):
            # Reset volume with gallons
            reset_data = {
                "keg_size": 5,
                "start_volume": 5,
                "unit": "gal"
            }
            
            response = await client.post(
                f"/api/v1/devices/{device.id}/port/0/rpc/Kegtron.ResetVolume",
                json=reset_data
            )
            assert response.status_code == 200
        
        # Verify conversion to mL
        port = await PortDB.get_by_device_id_and_index(device.id, 0, async_db_session)
        assert port.keg_size > 18900  # ~5 gallons in mL
        assert port.keg_size < 19000
    
    @pytest.mark.asyncio
    async def test_reset_volume_invalid_port(self, client, async_db_session, sample_device_data, mock_gatt):
        """Test resetting volume on invalid port index."""
        # Create a KT-100 device (single port)
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        # Try to reset volume on port 1 (doesn't exist on KT-100)
        reset_data = {"keg_size": 19000, "unit": "mL"}
        
        response = await client.post(
            f"/api/v1/devices/{device.id}/port/1/rpc/Kegtron.ResetVolume",
            json=reset_data
        )
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_reset_volume_nonexistent_device(self, client, mock_gatt):
        """Test resetting volume for a device that doesn't exist."""
        reset_data = {"keg_size": 19000, "unit": "mL"}
        
        response = await client.post(
            "/api/v1/devices/nonexistent/port/0/rpc/Kegtron.ResetVolume",
            json=reset_data
        )
        assert response.status_code == 404
        assert "Unknown device" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_reset_volume_partial_update(self, client, async_db_session, sample_device_data, mock_gatt):
        """Test resetting volume with only some fields updated."""
        # Create a device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_data)
        original_keg_size = db_ports_data[0]["keg_size"]
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        with patch('routes.rpc.gatt.write_chars', new_callable=AsyncMock):
            # Reset only start_volume
            reset_data = {"start_volume": 15000, "unit": "mL"}
            
            response = await client.post(
                f"/api/v1/devices/{device.id}/port/0/rpc/Kegtron.ResetVolume",
                json=reset_data
            )
            assert response.status_code == 200
        
        # Verify only specified field was updated through API
        response = await client.get(f"/api/v1/devices/{device.id}")
        assert response.status_code == 200
        device_data = response.json()
        port_data = device_data["ports"]["0"]
        assert port_data["volumeDispensed"] == 0  # Always reset
        assert port_data["startVolume"] == 15000  # Updated
        assert port_data["kegSize"] == original_keg_size  # Unchanged
    
    @pytest.mark.asyncio
    async def test_reset_volume_kt200_both_ports(self, client, async_db_session, sample_device_kt200_data, mock_gatt):
        """Test resetting volume on both ports of a KT-200 device."""
        # Create KT-200 device
        db_device_data, db_ports_data = convert_device_data_for_db(sample_device_kt200_data)
        
        device = await DeviceDB.create(async_db_session, **db_device_data)
        for port_data in db_ports_data:
            port_data["device_id"] = device.id
            await PortDB.create(async_db_session, **port_data)
        await async_db_session.commit()
        
        with patch('routes.rpc.gatt.write_chars', new_callable=AsyncMock):
            # Reset port 0
            reset_data_0 = {
                "keg_size": 20000,
                "start_volume": 20000,
                "unit": "mL"
            }
            response = await client.post(
                f"/api/v1/devices/{device.id}/port/0/rpc/Kegtron.ResetVolume",
                json=reset_data_0
            )
            assert response.status_code == 200
            
            # Reset port 1
            reset_data_1 = {
                "keg_size": 40000,
                "start_volume": 40000,
                "unit": "mL"
            }
            response = await client.post(
                f"/api/v1/devices/{device.id}/port/1/rpc/Kegtron.ResetVolume",
                json=reset_data_1
            )
            assert response.status_code == 200
        
        # Verify both ports were updated
        port_0 = await PortDB.get_by_device_id_and_index(device.id, 0, async_db_session)
        assert port_0.keg_size == 20000
        assert port_0.volume_dispensed == 0
        
        port_1 = await PortDB.get_by_device_id_and_index(device.id, 1, async_db_session)
        assert port_1.keg_size == 40000
        assert port_1.volume_dispensed == 0