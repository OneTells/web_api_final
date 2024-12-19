from datetime import datetime

from sqlalchemy import Integer, Text, UniqueConstraint, TIMESTAMP, text
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(Integer, primary_key=True, autoincrement=True)

    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    # noinspection PyTypeChecker
    __table_args__ = (
        UniqueConstraint(slug, name='products_uc'),
    )


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(Integer, primary_key=True, autoincrement=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=text("(STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW'))")
    )
