# pylint: disable=wrong-import-position
from argon2 import PasswordHasher
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.schema import Index

from db import Base, CRUDMixin, DictifiableMixin

TABLE_NAME = "users"

class User(Base, CRUDMixin, DictifiableMixin):

    __tablename__ = TABLE_NAME

    id = Column(Integer, server_default=func.uuid_generate_v4(), primary_key=True)
    email = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    profile_pic = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    admin = Column(Boolean, nullable=False, default=False)
    api_key = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_user_email", email, unique=True),
        Index("ix_user_api_key", api_key, unique=True),
    )

    @classmethod
    async def get_by_email(cls, db, email, **kwargs):
        res = await super().query(db, email=email, **kwargs)
        if not res:
            return None
        return res[0]

    @classmethod
    async def get_by_api_key(cls, db, api_key, **kwargs):
        res = await super().query(db, api_key=api_key, **kwargs)
        if not res:
            return None
        return res[0]

    async def update(self, db, password=None, **kwargs):  # pylint: disable=arguments-renamed
        if password and not kwargs.get("password_hash"):
            ph = PasswordHasher()
            kwargs["password_hash"] = ph.hash(password)
        return await super().update(db, **kwargs)

    @classmethod
    async def create(cls, db, password=None, **kwargs):  # pylint: disable=arguments-renamed
        if password and not kwargs.get("password_hash"):
            ph = PasswordHasher()
            kwargs["password_hash"] = ph.hash(password)
        return await super().create(db, **kwargs)
