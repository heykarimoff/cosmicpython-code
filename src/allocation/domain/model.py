from dataclasses import dataclass
from datetime import date
from typing import List, NewType, Optional, Set

from allocation.domain.events import Allocated, Deallocated, Event, OutOfStock

Reference = NewType("Reference", str)
Sku = NewType("Sku", str)
Quantity = NewType("Quantity", int)


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

    def allocate(self, line: OrderLine) -> None:
        if self.can_allocate(line):
            self._allocations.add(line)

    def deallocate(self, line: OrderLine) -> None:
        if line in self._allocations:
            self._allocations.remove(line)

    def can_allocate(self, line: OrderLine) -> bool:
        return self.sku == line.sku and 0 < line.qty <= self.available_quantity

    def deallocate_one(self) -> Optional[OrderLine]:
        if self._allocations:
            return self._allocations.pop()


class Product:
    events: List[Event] = []

    def __init__(self, sku: Sku, batches: List[Batch]):
        self.sku = sku
        self.batches = batches
        self.events = []  # type: List[Event]

    def __repr__(self):
        return f"<Product {self.sku}>"

    def __hash__(self):
        return hash(self.sku)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Product):
            return False
        return self.sku == other.sku and self.batches == other.batches

    def __gt__(self, other) -> bool:
        return len(self.batches) > len(other.batches)

    def allocate(self, line: OrderLine) -> Reference:
        try:
            batch = next(
                b for b in sorted(self.batches) if b.can_allocate(line)
            )
        except StopIteration:
            self.events.append(OutOfStock(line.sku))
            return None

        batch.allocate(line)
        self.events.append(
            Allocated(line.orderid, line.sku, line.qty, batch.reference)
        )

        return batch.reference

    def deallocate(self, line: OrderLine) -> None:
        for batch in self.batches:
            batch.deallocate(line)

    def change_batch_quantity(
        self, reference: Reference, qty: Quantity
    ) -> None:
        batch = next(b for b in self.batches if b.reference == reference)
        batch._purchased_quantity = qty
        while batch.allocated_quaitity > qty:
            line = batch.deallocate_one()
            self.events.append(Deallocated(line.orderid, line.sku, line.qty))
