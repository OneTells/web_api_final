from typing import AsyncIterator

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from core.methods import async_engine
from core.model import Event


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(async_engine)() as session:
        yield session


async def create_event(description: str) -> None:
    async with async_sessionmaker(async_engine)() as session:
        await session.execute(insert(Event).values(description=description))
        await session.commit()
