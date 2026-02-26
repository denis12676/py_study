from typing import List, Optional
from pydantic import BaseModel, Field


class ProductSize(BaseModel):
    """Информация о размере товара"""
    chrt_id: Optional[int] = Field(None, alias="chrtId")
    tech_size: Optional[str] = Field(None, alias="techSize")
    wb_size: Optional[str] = Field(None, alias="wbSize")
    price: float = 0.0
    discount: int = 0
    discounted_price: float = Field(0.0, alias="discountedPrice")


class Product(BaseModel):
    """Карточка товара"""
    nm_id: int = Field(..., alias="nmID")
    vendor_code: str = Field(..., alias="vendorCode")
    brand: Optional[str] = None
    title: Optional[str] = ""
    subject_name: Optional[str] = Field(None, alias="subjectName")
    photo_url: Optional[str] = None
    sizes: List[ProductSize] = []


class Sale(BaseModel):
    """Продажа или возврат из финансового отчета"""
    g_number: str = Field(..., alias="gNumber")
    date: str
    last_change_date: str = Field(..., alias="lastChangeDate")
    supplier_oper_name: str = Field(..., alias="supplierOperName")
    nm_id: int = Field(..., alias="nmId")
    barcode: str
    category: str
    subject: str
    brand: str
    vendor_code: str = Field(..., alias="supplierArticle")
    retail_price: float = Field(0.0, alias="totalPrice")
    for_pay: float = Field(0.0, alias="forPay")
    finished_price: float = Field(0.0, alias="finishedPrice")
    is_return: bool = False

    @property
    def is_real_sale(self) -> bool:
        return "Продажа" in self.supplier_oper_name and not self.is_return


class Order(BaseModel):
    """Заказ покупателя"""
    order_id: int = Field(..., alias="id")
    nm_id: int = Field(..., alias="nmId")
    vendor_code: str = Field(..., alias="article")
    created_at: str = Field(..., alias="createdAt")
    status: int = 0
    price: float = 0.0


class Stock(BaseModel):
    """Остаток товара на складе"""
    nm_id: int = Field(..., alias="nmId")
    vendor_code: str = Field(..., alias="supplierArticle")
    subject: Optional[str] = None
    brand: Optional[str] = None
    tech_size: Optional[str] = Field(None, alias="techSize")
    quantity: int = Field(0, alias="quantity")
    quantity_full: int = Field(0, alias="quantityFull")
    warehouse_name: str = Field(..., alias="warehouseName")


class Campaign(BaseModel):
    """Рекламная кампания"""
    advert_id: int = Field(..., alias="advertId")
    name: str = ""
    status: int = 0
    type: int = 0
    cpm: float = 0.0
    subject_id: Optional[int] = Field(None, alias="subjectId")
