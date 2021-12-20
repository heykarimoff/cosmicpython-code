from dataclasses import dataclass
from datetime import date
from typing import Optional


class Command:
    pass


@dataclass
class CreateBatch(Command):
    reference: str
    sku: str
    qty: int
    eta: Optional[date] = None


@dataclass
class ChangeBatchQuantity(Command):
    reference: str
    qty: int


@dataclass
class Allocate(Command):
    orderid: str
    sku: str
    qty: int


@dataclass
class Deallocate(Command):
    orderid: str
    sku: str
    qty: int
