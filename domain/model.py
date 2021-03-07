from dataclasses import dataclass
from datetime import date
from typing import List, NewType, Optional, Set

Reference = NewType("Reference", str)
Sku = NewType("Sku", str)
Quantity = NewType("Quantity", int)


class OutOfStock(Exception):
    pass


@dataclass(unsafe_hash=True)
class OrderLine:
    orderid: str
    sku: Sku
    qty: Quantity


class Batch:
    def __init__(
        self, reference: Reference, sku: Sku, qty: Quantity, eta: Optional[date]
    ):
        self.reference = reference
        self.sku = sku
        self.eta = eta
        self._purchased_quantity = qty
        self._allocations: Set[OrderLine] = set()

    def __repr__(self):
        return f"<Batch {self.reference}>"

    def __hash__(self):
        return hash(self.reference)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Batch):
            return False
        return self.reference == other.reference

    def __gt__(self, other) -> bool:
        if self.eta is None:
            return False
        if other.eta is None:
            return True

        return self.eta > other.eta

    @property
    def allocated_quaitity(self) -> Quantity:
        return Quantity(sum(line.qty for line in self._allocations))

    @property
    def available_quantity(self) -> Quantity:
        return Quantity(self._purchased_quantity - self.allocated_quaitity)

    def allocate(self, line: OrderLine):
        if self.can_allocate(line):
            self._allocations.add(line)

    def deallocate(self, line: OrderLine):
        if line in self._allocations:
            self._allocations.remove(line)

    def can_allocate(self, line: OrderLine) -> bool:
        return self.sku == line.sku and line.qty <= self.available_quantity


def allocate(line: OrderLine, batches: List[Batch]):
    try:
        batch = next(b for b in sorted(batches) if b.can_allocate(line))
    except StopIteration:
        raise OutOfStock(f"Out of stock for sku {line.sku}")

    batch.allocate(line)

    return batch.reference


def deallocate(line: OrderLine, batches: List[Batch]):
    for batch in batches:
        batch.deallocate(line)
