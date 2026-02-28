#!/usr/bin/env python3
"""
Seed data script to populate the database with sample Kegtron devices.
Creates:
- 3 devices with KT-200 model (2 ports each)
- 1 device with KT-100 model (1 port)
"""

import sys
import os
import random
from datetime import datetime, timedelta

from lib import logging
from lib.config import Config

CONFIG = Config(config_files=["default.json", "api.default.json"], env_prefix="KEGTRON_PROXY")
logging.init(config=CONFIG)
LOGGER = logging.getLogger(__name__)

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')

# Add src directory to path
sys.path.insert(0, SRC_DIR)

# Change to src directory so config files are found
os.chdir(SRC_DIR)


from db import init_db_sync, SessionLocal
from db.devices import Device
from db.ports import Port

# Initialize configuration and logging



def generate_mac_address():
    """Generate a random MAC address"""
    return ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])


def generate_device_data():
    """Generate sample device data"""
    devices = []
    
    # Generate 3 KT-200 devices (2 ports each)
    kt200_names = [
        "Garage Kegerator",
        "Basement Bar",
        "Patio Cooler"
    ]
    
    for i, name in enumerate(kt200_names, 1):
        device = {
            "id": f"kegtron-kt200-{i:03d}",
            "name": name,
            "mac": generate_mac_address(),
            "model": "KT-200",
            "port_cnt": 2,
            "rssi": random.randint(-70, -40),
            "last_advertisement_timestamp_utc": datetime.utcnow() - timedelta(minutes=random.randint(0, 60)),
            "ports": []
        }
        
        # Port 0 - Main keg (half barrel - 15.5 gallons)
        port_0_total = round(random.uniform(0.5, 15.0), 2)
        device["ports"].append({
            "port_index": 0,
            "keg_size": 15.5,  # Half barrel in gallons
            "total_volume": port_0_total,
            "start_volume": 15.5,
            "pulse_count": int(port_0_total * 1000)  # Approximate pulse count
        })
        
        # Port 1 - Secondary keg (sixth barrel - 5.16 gallons)
        port_1_total = round(random.uniform(0.2, 5.0), 2)
        device["ports"].append({
            "port_index": 1,
            "keg_size": 5.16,  # Sixth barrel in gallons
            "total_volume": port_1_total,
            "start_volume": 5.16,
            "pulse_count": int(port_1_total * 1000)
        })
        
        devices.append(device)
    
    # Generate 1 KT-100 device (1 port)
    kt100_device = {
        "id": "kegtron-kt100-001",
        "mac": generate_mac_address(),
        "model": "KT-100",
        "port_cnt": 1,
        "rssi": random.randint(-65, -45),
        "last_advertisement_timestamp_utc": datetime.utcnow() - timedelta(minutes=random.randint(0, 30)),
        "ports": []
    }
    
    # Single port - Mini keg (1.32 gallons / 5 liters)
    port_total = round(random.uniform(0.1, 1.2), 2)
    kt100_device["ports"].append({
        "port_index": 0,
        "keg_size": 1.32,  # Mini keg
        "total_volume": port_total,
        "start_volume": 1.32,
        "pulse_count": int(port_total * 1000)
    })
    
    devices.append(kt100_device)
    
    return devices


def seed_database():
    """Seed the database with sample data"""
    LOGGER.info("Starting database seeding...")
    
    # Initialize database tables
    init_db_sync()
    
    # Generate device data
    devices_data = generate_device_data()
    
    # Create database session
    with SessionLocal() as db:
        # Check if database already has data
        existing_count = db.query(Device).count()
        if existing_count > 0:
            LOGGER.warning(f"Database already contains {existing_count} devices. Skipping seed to avoid duplicates.")
            user_input = input("Do you want to continue and add more devices? (y/N): ")
            if user_input.lower() != 'y':
                LOGGER.info("Seeding cancelled by user.")
                return
        
        # Add devices to database
        for device_data in devices_data:
            try:
                # Extract ports data
                ports_data = device_data.pop("ports", [])
                
                # Create device
                device = Device(**device_data)
                db.add(device)
                db.flush()  # Flush to get the device ID
                
                # Create ports
                for port_data in ports_data:
                    port = Port(
                        device_id=device.id,
                        **port_data
                    )
                    db.add(port)
                
                LOGGER.info(f"Created device: {device.name} ({device.id}) with {len(ports_data)} port(s)")
                
            except Exception as e:
                LOGGER.error(f"Error creating device {device_data.get('id')}: {e}")
                db.rollback()
                raise
        
        # Commit all changes
        db.commit()
        LOGGER.info(f"Successfully seeded {len(devices_data)} devices")
    
    # Display summary
    with SessionLocal() as db:
        total_devices = db.query(Device).count()
        total_ports = db.query(Port).count()
        LOGGER.info(f"Database now contains {total_devices} devices with {total_ports} total ports")
        
        # Show sample data
        LOGGER.info("\nSample device data:")
        devices = db.query(Device).limit(5).all()
        for device in devices:
            ports_info = db.query(Port).filter(Port.device_id == device.id).all()
            port_summary = ", ".join([f"Port {p.port_index}: {p.start_volume - p.total_volume:.1f}gal left" 
                                     for p in ports_info])
            LOGGER.info(f"  {device.name or device.model} ({device.id}): {port_summary}")


if __name__ == "__main__":
    try:
        seed_database()
    except KeyboardInterrupt:
        LOGGER.info("Seeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        LOGGER.error(f"Seeding failed: {e}")
        sys.exit(1)