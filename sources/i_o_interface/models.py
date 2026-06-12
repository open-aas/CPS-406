"""Modelos Pydantic compartilhados entre as extensões IOInterface."""

from datetime import datetime
from typing import Optional
import enum
import pydantic


class ProductType(enum.IntEnum):
    single     = 1
    industrial = 2
    complete   = 3


class Product(pydantic.BaseModel):
    id:           Optional[int] = pydantic.Field(default=None)
    product_id:   str
    product_type: ProductType
    product_name: Optional[str] = None
    defect:       bool = False

    @pydantic.model_validator(mode="after")
    def _set_name(self) -> "Product":
        names = {
            ProductType.single:     "Produto Simples (Base + Medição)",
            ProductType.industrial: "Produto Industrial (Base + Furo)",
            ProductType.complete:   "Produto Completo (Base + Furo + Tampa)",
        }
        self.product_name = names.get(self.product_type, "Desconhecido")
        return self


class Order(pydantic.BaseModel):
    id:         Optional[int] = pydantic.Field(default=None)
    order_id:   str
    product:    Product
    quantity:   int
    production: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
