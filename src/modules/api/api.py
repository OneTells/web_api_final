from asyncio import sleep
from datetime import datetime, UTC
from typing import Annotated

from fastapi import FastAPI, Depends, WebSocket
from sqlalchemy import select, delete, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse
from starlette.websockets import WebSocketDisconnect

from core.model import Product, Event
from modules.api.methods import get_async_session, create_event
from modules.api.schemes import ProductModel, NewProduct, UpdateProduct

app = FastAPI()


@app.post("/products", status_code=201)
async def create_product(product: NewProduct, session: Annotated[AsyncSession, Depends(get_async_session)]):
    obj = dict(
        slug=product.url.removeprefix('https://www.maxidom.ru/catalog/').removesuffix('/'),
        name=product.name,
        price=product.price
    )

    request = (
        insert(Product)
        .values(**obj)
    )

    response = await session.execute(
        request
        .on_conflict_do_update(
            index_elements=[Product.slug],
            set_=dict(name=request.excluded.name, price=request.excluded.price)
        )
        .returning(Product.id)
    )
    await session.commit()

    id_ = response.first()[0]

    return JSONResponse(
        content={"message": "Продукт добавлен", "id": id_},
        background=BackgroundTask(create_event, {'id': id_, **obj}, 'Создание нового продукта')
    )


@app.get("/products")
async def get_products(session: Annotated[AsyncSession, Depends(get_async_session)]):
    response = await session.execute(
        select(Product.id, Product.slug, Product.name, Product.price)
        .order_by(Product.name)
    )

    return [
        ProductModel(
            id=product_id,
            name=name,
            price=price,
            url=f'https://www.maxidom.ru/catalog/{slug}/'
        ) for product_id, slug, name, price in response.all()
    ]


@app.delete("/products")
async def delete_products(session: Annotated[AsyncSession, Depends(get_async_session)]):
    await session.execute(delete(Product))
    await session.commit()

    return JSONResponse(
        content={"message": "Все данные удалены"},
        background=BackgroundTask(create_event, None, 'Удаление всех продуктов')
    )


@app.get("/products/{product_id}")
async def get_product(product_id: int, session: Annotated[AsyncSession, Depends(get_async_session)]):
    response = await session.execute(
        select(Product.id, Product.slug, Product.name, Product.price)
        .where(product_id == Product.id)
    )

    result = response.first()

    if not result:
        return JSONResponse({"message": "Продукт не найден"}, status_code=404)

    return ProductModel(
        id=result[0],
        name=result[2],
        price=result[3],
        url=f'https://www.maxidom.ru/catalog/{result[1]}/'
    )


@app.put("/products/{product_id}")
async def update_product(
    product_id: int,
    product: UpdateProduct,
    session: Annotated[AsyncSession, Depends(get_async_session)]
):
    response = await session.execute(
        select(Product.id, Product.slug, Product.name, Product.price)
        .where(product_id == Product.id)
    )

    result = response.first()

    if not result:
        return JSONResponse({"message": "Продукт не найден"}, status_code=404)

    obj = dict(
        slug=product.url.removeprefix('https://www.maxidom.ru/catalog/').removesuffix('/') if product.url else result[1],
        name=product.name or result[2],
        price=product.price or result[3]
    )

    await session.execute(
        update(Product)
        .values(**obj)
        .where(product_id == Product.id)
    )
    await session.commit()

    return JSONResponse(
        content={"message": "Продукт обновлен", "id": product_id},
        background=BackgroundTask(create_event, {'id': product_id, **obj}, 'Обновление продукта')
    )


@app.delete("/products/{product_id}")
async def delete_product(product_id: int, session: Annotated[AsyncSession, Depends(get_async_session)]):
    response = await session.execute(
        select(Product.id)
        .where(product_id == Product.id)
    )

    if not response.first():
        return JSONResponse({"message": "Продукт не найден"}, status_code=404)

    await session.execute(delete(Product).where(product_id == Product.id))
    await session.commit()

    return JSONResponse(
        content={"message": "Продукт удален"},
        background=BackgroundTask(create_event, {'id': product_id}, 'Удаление продукта')
    )


@app.websocket('/events/ws')
async def ws_events(websocket: WebSocket, session: Annotated[AsyncSession, Depends(get_async_session)]):
    await websocket.accept()

    last_time_point = datetime.now(UTC)

    try:
        while True:
            response = await session.execute(
                select(Event.created_at, Event.data)
                .where(last_time_point <= Event.created_at)
            )

            for created_at, data in response.all():
                await websocket.send_text(data)
                last_time_point = created_at

            await sleep(0.1)
    except WebSocketDisconnect:
        pass
