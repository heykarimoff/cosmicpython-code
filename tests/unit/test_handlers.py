from typing import List

import pytest
from allocation.adapters import repository
from allocation.domain import events, model
from allocation.service_layer import handlers, unit_of_work


class FakeRepository:
    def __init__(self, products: List[model.Product] = None):
        self._products = products or set()

    def add(self, product: model.Product):
        self._products.add(product)

    def get(self, sku: model.Sku) -> model.Product:
        return next((item for item in self._products if item.sku == sku), None)

    def list(self):
        return list(self._products)

    @staticmethod
    def for_batch(reference, sku, qty, eta=None):
        batch = model.Batch(reference, sku, qty, eta)
        return FakeRepository([model.Product(sku, [batch])])


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.products = repository.TrackingRepository(FakeRepository())
        self.committed = False

    def _commit(self):
        self.committed = True

    def _rollback(self):
        pass


def test_add_batch_for_new_product():
    uow = FakeUnitOfWork()
    event = events.BatchCreated(
        reference="batch1", sku="COMPLICATED-LAMP", qty=100
    )
    handlers.add_batch(event=event, uow=uow)

    assert uow.products.get("COMPLICATED-LAMP") is not None
    product = uow.products.get("COMPLICATED-LAMP")
    assert "batch1" in [b.reference for b in product.batches]
    assert uow.committed


def test_add_batch_for_existing_product():
    uow = FakeUnitOfWork()
    event1 = events.BatchCreated(
        reference="batch1", sku="CRUNCHY-ARMCHAIR", qty=10
    )
    event2 = events.BatchCreated(
        reference="batch2", sku="CRUNCHY-ARMCHAIR", qty=15
    )
    handlers.add_batch(event=event1, uow=uow)
    handlers.add_batch(event=event2, uow=uow)

    assert uow.products.get("CRUNCHY-ARMCHAIR") is not None
    product = uow.products.get("CRUNCHY-ARMCHAIR")
    assert "batch1" in [b.reference for b in product.batches]
    assert "batch2" in [b.reference for b in product.batches]
    assert uow.committed


def test_allocate_returns_allocation():
    uow = FakeUnitOfWork()
    event = events.BatchCreated(
        reference="batch1", sku="COMPLICATED-LAMP", qty=100
    )
    handlers.add_batch(event, uow)

    event = events.AllocationRequired(
        orderid="order1", sku="COMPLICATED-LAMP", qty=10
    )
    result = handlers.allocate(event=event, uow=uow)

    assert result == "batch1"
    assert uow.committed


def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    event = events.BatchCreated(reference="batch1", sku="AREALSKU", qty=100)
    handlers.add_batch(event, uow)

    with pytest.raises(
        handlers.InvalidSku, match="Invalid sku NON-EXISTENTSKU"
    ):
        event = events.AllocationRequired(
            orderid="order1", sku="NON-EXISTENTSKU", qty=10
        )
        handlers.allocate(event=event, uow=uow)


def test_deallocate():
    uow = FakeUnitOfWork()
    event = events.BatchCreated(
        reference="batch1", sku="COMPLICATED-LAMP", qty=100
    )
    handlers.add_batch(event, uow)

    event = events.AllocationRequired(
        orderid="order1", sku="COMPLICATED-LAMP", qty=10
    )
    result = handlers.allocate(event=event, uow=uow)
    assert result == "batch1"
    product = uow.products.get("COMPLICATED-LAMP")
    batch = product.batches[0]
    assert batch.reference == "batch1"
    assert batch.allocated_quaitity == 10

    event = events.DeallocationRequired(
        orderid="order1", sku="COMPLICATED-LAMP", qty=10
    )
    handlers.deallocate(event, uow)

    assert batch.allocated_quaitity == 0
    assert uow.committed
