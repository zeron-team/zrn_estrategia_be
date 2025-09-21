# app/db/base_class.py
from __future__ import annotations

from sqlalchemy import MetaData
try:
    # SQLAlchemy 2.x
    from sqlalchemy.orm import DeclarativeBase

    NAMING_CONVENTION = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }

    class Base(DeclarativeBase):
        metadata = MetaData(naming_convention=NAMING_CONVENTION)

except Exception:
    # SQLAlchemy 1.4 fallback
    from sqlalchemy.orm import declarative_base

    NAMING_CONVENTION = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
    _metadata = MetaData(naming_convention=NAMING_CONVENTION)
    Base = declarative_base(metadata=_metadata)

__all__ = ["Base"]