from dataclasses import dataclass
from datetime import date
from typing import Optional


class Event:
    pass


@dataclass
class OutOfStock(Event):
    sku: str
