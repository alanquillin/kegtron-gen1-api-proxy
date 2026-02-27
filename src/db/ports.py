from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any

from db import Base, CRUDMixin

TABLE_NAME = "ports"
class Port(Base, CRUDMixin):
    __tablename__ = TABLE_NAME

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

    def to_dict(self) -> Dict[str, Any]:
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

    # TODO override create method to check conditions: 
    # - Device_id + port_index - must be unique 