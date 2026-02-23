from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Device(Base):
    __tablename__ = 'devices'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    mac = Column(String, unique=True, nullable=True)
    model = Column(String, nullable=True)
    port_cnt = Column(Integer, default=1)
    rssi = Column(Integer, nullable=True)
    last_advertisement_timestamp_utc = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to ports
    ports = relationship("Port", back_populates="device", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "mac": self.mac,
            "model": self.model,
            "port_cnt": self.port_cnt,
            "rssi": self.rssi,
            "last_advertisement_timestamp_utc": self.last_advertisement_timestamp_utc.isoformat() if self.last_advertisement_timestamp_utc else None,
            "ports": {str(port.port_index): port.to_dict() for port in self.ports}
        }


class Port(Base):
    __tablename__ = 'ports'

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.id'))
    port_index = Column(Integer, nullable=False)
    keg_size = Column(Float, nullable=True)
    total_volume = Column(Float, nullable=True)
    start_volume = Column(Float, nullable=True)
    pulse_count = Column(Integer, nullable=True)
    data = Column(JSON, nullable=True)  # Store any additional port data as JSON
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship back to device
    device = relationship("Device", back_populates="ports")

    def to_dict(self):
        result = {
            "port_index": self.port_index,
            "keg_size": self.keg_size,
            "total_volume": self.total_volume,
            "start_volume": self.start_volume,
            "pulse_count": self.pulse_count
        }
        if self.data:
            result.update(self.data)
        return result