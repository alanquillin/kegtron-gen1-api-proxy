# pylint: disable=wrong-import-position
from argon2 import PasswordHasher
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.schema import Index

from db import Base, CRUDMixin, DictifiableMixin

TABLE_NAME = "service_accounts"

class ServiceAccount(Base, CRUDMixin, DictifiableMixin):

    __tablename__ = TABLE_NAME

    id = Column(Integer, server_default=func.uuid_generate_v4(), primary_key=True)
    api_key = Column(String, nullable=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_service_account_api_key", api_key, unique=True),
    )

    @classmethod
    async def get_by_api_key(cls, db, api_key, **kwargs):
        res = await super().query(db, api_key=api_key, **kwargs)
        if not res:
            return None
        return res[0]
