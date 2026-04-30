"""SQLAlchemy DeclarativeBase. 모든 ORM 모델은 본 Base를 상속한다."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
