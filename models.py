from dataclasses import dataclass, field
from typing import List


@dataclass
class ProductSize:
    chrt_id: int
    tech_size: str
    price: float = 0.0
    discount: int = 0


@dataclass
class Product:
    nm_id: int
    vendor_code: str
    brand: str
    title: str
    sizes: List[ProductSize] = field(default_factory=list)


@dataclass
class Sale:
    g_number: str
    nm_id: int
    subject: str
    brand: str
    for_pay: float = 0.0
    is_return: bool = False


@dataclass
class Stock:
    nm_id: int
    vendor_code: str
    subject: str
    quantity: int
    warehouse_name: str


@dataclass
class Order:
    order_id: int
    nm_id: int
    status: int
    created_at: str


@dataclass
class Campaign:
    campaign_id: int
    name: str
    status: int
    campaign_type: int
    budget: float = 0.0
