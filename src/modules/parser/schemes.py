from pydantic import BaseModel


class ProductModel(BaseModel):
    name: str
    url: str
    price: int
