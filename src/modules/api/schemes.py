from typing import Any

from pydantic import BaseModel


class NewProduct(BaseModel):
    name: str
    url: str
    price: int


class ProductModel(BaseModel):
    id: int
    name: str
    url: str
    price: int


class UpdateProduct(BaseModel):
    name: str | None = None
    url: str | None = None
    price: int | None = None


class EventModel(BaseModel):
    description: str
    content: Any
