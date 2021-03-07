import pytest

from domain import model
from adapters import repository
from service_layer import services


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


class FakeSession:
    committed = False

    def commit(self):
        self.committed = True


def test_add_batch():
    repo, session = FakeRepository(), FakeSession()

    services.add_batch(
        reference="batch1",
        sku="COMPLICATED-LAMP",
        qty=100,
        eta=None,
        repo=repo,
        session=session,
    )

    assert repo.get("batch1") is not None
    assert session.committed


def test_allocate_returns_allocation():
    repo = FakeRepository.for_batch("batch1", "COMPLICATED-LAMP", 100)
    session = FakeSession()

    result = services.allocate(
        orderid="order1",
        sku="COMPLICATED-LAMP",
        qty=10,
        repo=repo,
        session=session,
    )

    assert result == "batch1"
    assert session.committed


def test_allocate_errors_for_invalid_sku():
    repo = FakeRepository.for_batch("batch1", "AREALSKU", 100, eta=None)

    with pytest.raises(
        services.InvalidSku, match="Invalid sku NON-EXISTENTSKU"
    ):
        services.allocate(
            orderid="order1",
            sku="NON-EXISTENTSKU",
            qty=10,
            repo=repo,
            session=FakeSession(),
        )


def test_deallocate():
    repo = FakeRepository.for_batch("batch1", "COMPLICATED-LAMP", 100)
    batch = repo.get("batch1")
    session = FakeSession()

    result = services.allocate(
        orderid="order1",
        sku="COMPLICATED-LAMP",
        qty=10,
        repo=repo,
        session=session,
    )
    assert result == "batch1"
    assert batch.allocated_quaitity == 10

    services.deallocate("order1", "COMPLICATED-LAMP", 10, repo, session)

    assert batch.allocated_quaitity == 0
    assert session.committed
