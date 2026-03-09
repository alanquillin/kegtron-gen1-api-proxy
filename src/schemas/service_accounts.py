from typing import List, Optional

from schemas import CamelCaseModel


class ServiceAccountBase(CamelCaseModel):
    api_key: Optional[str] = None
    admin: Optional[bool] = None


class ServiceAccountCreate(ServiceAccountBase):
    name: str


class ServiceAccountUpdate(ServiceAccountBase):
    name: Optional[str] = None
