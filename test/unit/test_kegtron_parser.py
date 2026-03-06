import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from struct import pack

from kegtron.parser import parse, parse_advertisement, parse_scan, parse_scan_short
from lib.exceptions import InvalidKegtronAdvertisementData


class TestParse:
    def test_parse_with_22_byte_data(self):
        data = b'\x00' * 22
        result = parse(data)
        assert result == {}
        
    def test_parse_with_31_byte_data(self):
        data = pack(">BBHHHHB20s", 0x1E, 0xFF, 0xFFFF, 1000, 500, 100, 0x01, b"Test Port")
        with patch('kegtron.parser.utcnow_aware') as mock_utcnow:
            mock_utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = parse(data)
            assert result["model"] == "Kegtron KT-100"
            assert result["port_cnt"] == 1
            assert result["port_data"]["keg_size"] == 1000
            
    def test_parse_with_27_byte_data(self):
        data = pack(">HHHB20s", 1000, 500, 100, 0x01, b"Test Port")
        with patch('kegtron.parser.utcnow_aware') as mock_utcnow:
            mock_utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = parse(data)
            assert result["model"] == "Kegtron KT-100"
            assert result["port_cnt"] == 1
            
    def test_parse_with_invalid_length(self):
        data = b'\x00' * 10
        with pytest.raises(InvalidKegtronAdvertisementData, match="Invalid packet length"):
            parse(data)


class TestParseScan:
    def test_parse_scan_valid_kt100(self):
        data = pack(">BBHHHHB20s", 0x1E, 0xFF, 0xFFFF, 1000, 500, 100, 0x01, b"Test Port\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        
        with patch('kegtron.parser.utcnow_aware') as mock_utcnow:
            mock_utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = parse_scan(data)
            
            assert result["model"] == "Kegtron KT-100"
            assert result["port_cnt"] == 1
            assert result["port_data"]["keg_size"] == 1000
            assert result["port_data"]["start_volume"] == 500
            assert result["port_data"]["volume_dispensed"] == 100
            assert result["port_data"]["port_name"].startswith("Test Port")
            assert result["port_data"]["configured"] == True
            assert result["port_data"]["port_index"] == 0
            
    def test_parse_scan_valid_kt200_port0(self):
        data = pack(">BBHHHHB20s", 0x1E, 0xFF, 0xFFFF, 1000, 500, 100, 0x41, b"Test Port 0")
        
        with patch('kegtron.parser.utcnow_aware') as mock_utcnow:
            mock_utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = parse_scan(data)
            
            assert result["model"] == "Kegtron KT-200"
            assert result["port_cnt"] == 2
            assert result["port_data"]["port_index"] == 0
            assert result["port_data"]["configured"] == True
            
    def test_parse_scan_valid_kt200_port1(self):
        data = pack(">BBHHHHB20s", 0x1E, 0xFF, 0xFFFF, 1000, 500, 100, 0x51, b"Test Port 1")
        
        with patch('kegtron.parser.utcnow_aware') as mock_utcnow:
            mock_utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = parse_scan(data)
            
            assert result["model"] == "Kegtron KT-200"
            assert result["port_cnt"] == 2
            assert result["port_data"]["port_index"] == 1
            assert result["port_data"]["configured"] == True
            
    def test_parse_scan_not_configured(self):
        data = pack(">BBHHHHB20s", 0x1E, 0xFF, 0xFFFF, 1000, 500, 100, 0x00, b"Test Port")
        
        with patch('kegtron.parser.utcnow_aware') as mock_utcnow:
            mock_utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = parse_scan(data)
            
            assert result["port_data"]["configured"] == False
            
    def test_parse_scan_invalid_ttl_len(self):
        data = pack(">BBHHHHB20s", 0x10, 0xFF, 0xFFFF, 1000, 500, 100, 0x01, b"Test Port")
        with pytest.raises(InvalidKegtronAdvertisementData, match="Total Length should be"):
            parse_scan(data)
            
    def test_parse_scan_invalid_type(self):
        data = pack(">BBHHHHB20s", 0x1E, 0xAA, 0xFFFF, 1000, 500, 100, 0x01, b"Test Port")
        with pytest.raises(InvalidKegtronAdvertisementData, match="Type byte should be"):
            parse_scan(data)
            
    def test_parse_scan_invalid_cic(self):
        data = pack(">BBHHHHB20s", 0x1E, 0xFF, 0xAAAA, 1000, 500, 100, 0x01, b"Test Port")
        with pytest.raises(InvalidKegtronAdvertisementData, match="Company Identifier Code"):
            parse_scan(data)


class TestParseScanShort:
    def test_parse_scan_short_valid_kt100(self):
        data = pack(">HHHB20s", 1000, 500, 100, 0x01, b"Test Port\x00\x00\x00")
        
        with patch('kegtron.parser.utcnow_aware') as mock_utcnow:
            mock_utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = parse_scan_short(data)
            
            assert result["model"] == "Kegtron KT-100"
            assert result["port_cnt"] == 1
            assert result["port_data"]["keg_size"] == 1000
            assert result["port_data"]["start_volume"] == 500
            assert result["port_data"]["volume_dispensed"] == 100
            assert result["port_data"]["port_name"] == "Test Port"
            assert result["port_data"]["configured"] == True
            assert result["port_data"]["port_index"] == 0
            
    def test_parse_scan_short_valid_kt200_port0(self):
        data = pack(">HHHB20s", 1000, 500, 100, 0x41, b"Test Port 0\x00\x00\x00")
        
        with patch('kegtron.parser.utcnow_aware') as mock_utcnow:
            mock_utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = parse_scan_short(data)
            
            assert result["model"] == "Kegtron KT-200"
            assert result["port_cnt"] == 2
            assert result["port_data"]["port_index"] == 0
            
    def test_parse_scan_short_valid_kt200_port1(self):
        data = pack(">HHHB20s", 1000, 500, 100, 0x51, b"Test Port 1\x00\x00\x00")
        
        with patch('kegtron.parser.utcnow_aware') as mock_utcnow:
            mock_utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = parse_scan_short(data)
            
            assert result["model"] == "Kegtron KT-200"
            assert result["port_cnt"] == 2
            assert result["port_data"]["port_index"] == 1
            
    def test_parse_scan_short_strips_null_bytes(self):
        data = pack(">HHHB20s", 1000, 500, 100, 0x01, b"Test\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        
        with patch('kegtron.parser.utcnow_aware') as mock_utcnow:
            mock_utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = parse_scan_short(data)
            
            assert result["port_data"]["port_name"] == "Test"