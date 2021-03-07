from datetime import date
from typing import Optional

from adapters import repository
from domain import model


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches) -> bool:
    return sku in {b.sku for b in batches}


def add_batch(
    reference: str,
    sku: str,
    qty: int,
    eta: Optional[date],
    repo: repository.AbstractRepository,
    session,
):
    batch = model.Batch(reference, sku, qty, eta)
    repo.add(batch)
    session.commit()


def allocate(
    orderid: str,
    sku: str,
    qty: int,
    repo: repository.AbstractRepository,
    session,
) -> str:
    line = model.OrderLine(orderid, sku, qty)
    batches = repo.list()

    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")

    batchref = model.allocate(line, batches)
    session.commit()

    return batchref


def deallocate(
    orderid: str,
    sku: str,
    qty: int,
    repo: repository.AbstractRepository,
    session,
) -> None:
    line = model.OrderLine(orderid, sku, qty)
    batches = repo.list()

    model.deallocate(line, batches)
    session.commit()
