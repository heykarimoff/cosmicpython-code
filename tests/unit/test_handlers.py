from datetime import date
from typing import List

import pytest
from allocation.adapters import repository
from allocation.domain import commands, events, model
from allocation.service_layer import handlers, messagebus, unit_of_work


class FakeRepository:
    def __init__(self, products: List[model.Product] = None):
        self._products = products or set()

    def add(self, product: model.Product):
        self._products.add(product)

    def get(self, sku: model.Sku) -> model.Product:
        return next((item for item in self._products if item.sku == sku), None)

    def get_by_batch_reference(
        self, reference: model.Reference
    ) -> model.Product:
        return next(
            (
                item
                for item in self._products
                for batch in item.batches
                if batch.reference == reference
            ),
            None,
        )

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
    message = commands.CreateBatch(
        reference="batch1", sku="COMPLICATED-LAMP", qty=100
    )

    messagebus.handle(message, uow)

    assert uow.products.get("COMPLICATED-LAMP") is not None
    product = uow.products.get("COMPLICATED-LAMP")
    assert "batch1" in [b.reference for b in product.batches]
    assert uow.committed


def test_add_batch_for_existing_product():
    uow = FakeUnitOfWork()
    history = [
        commands.CreateBatch(
            reference="batch1", sku="CRUNCHY-ARMCHAIR", qty=10
        ),
        commands.CreateBatch(
            reference="batch2", sku="CRUNCHY-ARMCHAIR", qty=15
        ),
    ]

    for message in history:
        messagebus.handle(message, uow)

    assert uow.products.get("CRUNCHY-ARMCHAIR") is not None
    product = uow.products.get("CRUNCHY-ARMCHAIR")
    assert "batch1" in [b.reference for b in product.batches]
    assert "batch2" in [b.reference for b in product.batches]
    assert uow.committed


def test_allocate_returns_allocation():
    uow = FakeUnitOfWork()
    message = commands.CreateBatch(
        reference="batch1", sku="COMPLICATED-LAMP", qty=100
    )
    messagebus.handle(message, uow)

    message = commands.Allocate(
        orderid="order1", sku="COMPLICATED-LAMP", qty=10
    )
    [batchref] = messagebus.handle(message, uow)

    assert batchref == "batch1"
    assert uow.committed


def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    message = commands.CreateBatch(reference="batch1", sku="AREALSKU", qty=100)
    messagebus.handle(message, uow)

    with pytest.raises(
        handlers.InvalidSku, match="Invalid sku NON-EXISTENTSKU"
    ):
        message = commands.Allocate(
            orderid="order1", sku="NON-EXISTENTSKU", qty=10
        )
        messagebus.handle(message, uow)


def test_deallocate():
    uow = FakeUnitOfWork()
    message = commands.CreateBatch(
        reference="batch1", sku="COMPLICATED-LAMP", qty=100
    )
    messagebus.handle(message, uow)

    message = commands.Allocate(
        orderid="order1", sku="COMPLICATED-LAMP", qty=10
    )
    [batchref] = messagebus.handle(message, uow)
    assert batchref == "batch1"
    product = uow.products.get("COMPLICATED-LAMP")
    batch = product.batches[0]
    assert batch.reference == "batch1"
    assert batch.allocated_quaitity == 10

    message = commands.Deallocate(
        orderid="order1", sku="COMPLICATED-LAMP", qty=10
    )
    messagebus.handle(message, uow)

    assert batch.allocated_quaitity == 0
    assert uow.committed


def test_changes_available_quantity():
    uow = FakeUnitOfWork()
    message = commands.CreateBatch(
        reference="batch1", sku="ADORABLE-SETTEE", qty=100
    )
    messagebus.handle(message, uow)
    [batch] = uow.products.get("ADORABLE-SETTEE").batches

    assert batch.available_quantity == 100

    message = commands.ChangeBatchQuantity(reference="batch1", qty=50)
    messagebus.handle(message, uow)

    assert batch.available_quantity == 50


def test_realocates_batch_if_nessesary_when_available_quantity_reduces():
    uow = FakeUnitOfWork()
    history = [
        commands.CreateBatch(
            reference="batch1", sku="INDIFFERENT-TABLE", qty=100
        ),
        commands.CreateBatch(
            reference="batch2",
            sku="INDIFFERENT-TABLE",
            qty=100,
            eta=date.today(),
        ),
        commands.Allocate(orderid="order1", sku="INDIFFERENT-TABLE", qty=50),
        commands.Allocate(orderid="order2", sku="INDIFFERENT-TABLE", qty=50),
    ]
    for message in history:
        messagebus.handle(message, uow)
    [batch1, batch2] = uow.products.get("INDIFFERENT-TABLE").batches

    assert batch1.available_quantity == 0
    assert batch2.available_quantity == 100

    message = commands.ChangeBatchQuantity(reference="batch1", qty=55)
    messagebus.handle(message, uow)

    assert batch1.available_quantity == 5
    assert batch2.available_quantity == 50
