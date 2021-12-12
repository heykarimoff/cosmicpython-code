from typing import List

import pytest
from allocation.adapters import repository
from allocation.domain import model
from allocation.service_layer import services, unit_of_work


class FakeRepository(repository.AbstractRepository):
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
        self.products = FakeRepository()
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_add_batch_for_new_product():
    uow = FakeUnitOfWork()

    services.add_batch(
        reference="batch1", sku="COMPLICATED-LAMP", qty=100, eta=None, uow=uow
    )

    assert uow.products.get("COMPLICATED-LAMP") is not None
    product = uow.products.get("COMPLICATED-LAMP")
    assert "batch1" in [b.reference for b in product.batches]
    assert uow.committed


def test_add_batch_for_existing_product():
    uow = FakeUnitOfWork()

    services.add_batch(
        reference="batch1", sku="CRUNCHY-ARMCHAIR", qty=10, eta=None, uow=uow
    )
    services.add_batch(
        reference="batch2", sku="CRUNCHY-ARMCHAIR", qty=15, eta=None, uow=uow
    )

    assert uow.products.get("CRUNCHY-ARMCHAIR") is not None
    product = uow.products.get("CRUNCHY-ARMCHAIR")
    assert "batch1" in [b.reference for b in product.batches]
    assert "batch2" in [b.reference for b in product.batches]
    assert uow.committed


def test_allocate_returns_allocation():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "COMPLICATED-LAMP", 100, None, uow)

    result = services.allocate(
        orderid="order1", sku="COMPLICATED-LAMP", qty=10, uow=uow
    )

    assert result == "batch1"
    assert uow.committed


def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "AREALSKU", 100, None, uow)

    with pytest.raises(
        services.InvalidSku, match="Invalid sku NON-EXISTENTSKU"
    ):
        services.allocate(
            orderid="order1", sku="NON-EXISTENTSKU", qty=10, uow=uow
        )


def test_deallocate():
    uow = FakeUnitOfWork()
    services.add_batch("batch1", "COMPLICATED-LAMP", 100, None, uow)

    result = services.allocate(
        orderid="order1", sku="COMPLICATED-LAMP", qty=10, uow=uow
    )
    assert result == "batch1"
    product = uow.products.get("COMPLICATED-LAMP")
    batch = product.batches[0]
    assert batch.reference == "batch1"
    assert batch.allocated_quaitity == 10

    services.deallocate("order1", "COMPLICATED-LAMP", 10, uow)

    assert batch.allocated_quaitity == 0
    assert uow.committed
