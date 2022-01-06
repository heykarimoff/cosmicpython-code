from datetime import date
from typing import List

import pytest
from allocation import bootstrap
from allocation.adapters import repository
from allocation.domain import commands, model
from allocation.service_layer import handlers, unit_of_work


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


@pytest.fixture
def messagebus():
    bus = bootstrap.bootstrap(
        start_orm=False,
        uow=FakeUnitOfWork(),
        send_mail=lambda *args, **kwargs: None,
        publish=lambda *args, **kwargs: None,
    )
    return bus


@pytest.mark.smoke
def test_add_batch_for_new_product(messagebus):
    message = commands.CreateBatch(
        reference="batch1", sku="COMPLICATED-LAMP", qty=100
    )

    messagebus.handle(message)

    assert messagebus.uow.products.get("COMPLICATED-LAMP") is not None
    product = messagebus.uow.products.get("COMPLICATED-LAMP")
    assert "batch1" in [b.reference for b in product.batches]
    assert messagebus.uow.committed


@pytest.mark.smoke
def test_add_batch_for_existing_product(messagebus):
    history = [
        commands.CreateBatch(
            reference="batch1", sku="CRUNCHY-ARMCHAIR", qty=10
        ),
        commands.CreateBatch(
            reference="batch2", sku="CRUNCHY-ARMCHAIR", qty=15
        ),
    ]

    for message in history:
        messagebus.handle(message)

    assert messagebus.uow.products.get("CRUNCHY-ARMCHAIR") is not None
    product = messagebus.uow.products.get("CRUNCHY-ARMCHAIR")
    assert "batch1" in [b.reference for b in product.batches]
    assert "batch2" in [b.reference for b in product.batches]
    assert messagebus.uow.committed


@pytest.mark.smoke
def test_allocate_returns_allocation(messagebus):
    message = commands.CreateBatch(
        reference="batch1", sku="COMPLICATED-LAMP", qty=100
    )
    messagebus.handle(message)

    message = commands.Allocate(
        orderid="order1", sku="COMPLICATED-LAMP", qty=10
    )
    [batchref] = messagebus.handle(message)

    assert batchref == "batch1"
    assert messagebus.uow.committed


def test_allocate_errors_for_invalid_sku(messagebus):
    message = commands.CreateBatch(reference="batch1", sku="AREALSKU", qty=100)
    messagebus.handle(message)

    with pytest.raises(
        handlers.InvalidSku, match="Invalid sku NON-EXISTENTSKU"
    ):
        message = commands.Allocate(
            orderid="order1", sku="NON-EXISTENTSKU", qty=10
        )
        messagebus.handle(message)


@pytest.mark.smoke
def test_deallocate(messagebus):
    message = commands.CreateBatch(
        reference="batch1", sku="COMPLICATED-LAMP", qty=100
    )
    messagebus.handle(message)

    message = commands.Allocate(
        orderid="order1", sku="COMPLICATED-LAMP", qty=10
    )
    [batchref] = messagebus.handle(message)
    assert batchref == "batch1"
    product = messagebus.uow.products.get("COMPLICATED-LAMP")
    batch = product.batches[0]
    assert batch.reference == "batch1"
    assert batch.allocated_quaitity == 10

    message = commands.Deallocate(
        orderid="order1", sku="COMPLICATED-LAMP", qty=10
    )
    messagebus.handle(message)

    assert batch.allocated_quaitity == 0
    assert messagebus.uow.committed


@pytest.mark.smoke
def test_changes_available_quantity(messagebus):
    message = commands.CreateBatch(
        reference="batch1", sku="ADORABLE-SETTEE", qty=100
    )
    messagebus.handle(message)
    [batch] = messagebus.uow.products.get("ADORABLE-SETTEE").batches

    assert batch.available_quantity == 100

    message = commands.ChangeBatchQuantity(reference="batch1", qty=50)
    messagebus.handle(message)

    assert batch.available_quantity == 50


def test_realocates_batch_if_nessesary_when_available_quantity_reduces(
    messagebus,
):
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
        messagebus.handle(message)
    [batch1, batch2] = messagebus.uow.products.get("INDIFFERENT-TABLE").batches

    assert batch1.available_quantity == 0
    assert batch2.available_quantity == 100

    message = commands.ChangeBatchQuantity(reference="batch1", qty=55)
    messagebus.handle(message)

    assert batch1.available_quantity == 5
    assert batch2.available_quantity == 50
