from typing import Optional

from schemas import CamelCaseModel


class ServiceAccountBase(CamelCaseModel):
    api_key: Optional[str] = None
    description: Optional[str] = None


class ServiceAccountCreate(ServiceAccountBase):
    name: str


class ServiceAccountUpdate(ServiceAccountBase):
    name: Optional[str] = None
