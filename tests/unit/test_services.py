import pytest
from adapters import repository
from domain import model
from service_layer import services, unit_of_work


class FakeRepository(repository.AbstractRepository):
    def __init__(self, batches=None):
        self._batches = batches or set()

    def add(self, batch):
        self._batches.add(batch)

    def get(self, reference):
        return next(b for b in self._batches if b.reference == reference)

    def list(self):
        return list(self._batches)

    @staticmethod
    def for_batch(reference, sku, qty, eta=None):
        return FakeRepository([model.Batch(reference, sku, qty, eta)])


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.batches = FakeRepository()
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_add_batch():
    uow = FakeUnitOfWork()

    services.add_batch(
        reference="batch1", sku="COMPLICATED-LAMP", qty=100, eta=None, uow=uow
    )

    assert uow.batches.get("batch1") is not None
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
    batch = uow.batches.get("batch1")
    assert batch.allocated_quaitity == 10

    services.deallocate("order1", "COMPLICATED-LAMP", 10, uow)

    assert batch.allocated_quaitity == 0
    assert uow.committed
