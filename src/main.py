from asyncio import new_event_loop, Runner
from multiprocessing import Process

import uvicorn

from core.methods import async_engine
from core.model import Product
from modules.api.api import app
from modules.parser.methods import run_process


async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Product.metadata.create_all)


def main():
    # Создание таблиц
    with Runner(loop_factory=new_event_loop) as runner:
        runner.run(create_tables())

    # Запуск парсера
    parse_process = Process(target=run_process)
    parse_process.start()

    # Запуск api
    uvicorn.run(app)

    # Закрытие парсера
    parse_process.terminate()
    parse_process.join()


if __name__ == '__main__':
    main()
