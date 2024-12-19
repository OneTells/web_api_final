from typing import AsyncIterator

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from core.methods import async_engine
from core.model import Event
from modules.api.schemes import EventModel


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(async_engine)() as session:
        yield session


async def create_event(content: any, description: str) -> None:
    async with async_sessionmaker(async_engine)() as session:
        await session.execute(
            insert(Event)
            .values(data=EventModel(content=content, description=description).model_dump_json())
        )

        await session.commit()
