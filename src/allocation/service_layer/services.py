from datetime import date
from typing import Optional

from allocation.domain import model
from allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches) -> bool:
    return sku in {b.sku for b in batches}


def add_batch(
    reference: str,
    sku: str,
    qty: int,
    eta: Optional[date],
    uow: unit_of_work.AbstractUnitOfWork,
):
    batch = model.Batch(reference, sku, qty, eta)
    with uow:
        uow.batches.add(batch)
        uow.commit()


def allocate(
    orderid: str, sku: str, qty: int, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = model.OrderLine(orderid, sku, qty)

    with uow:
        batches = uow.batches.list()

        if not is_valid_sku(line.sku, batches):
            raise InvalidSku(f"Invalid sku {line.sku}")

        product = model.Product(sku, batches)
        batchref = product.allocate(line)
        uow.commit()

    return batchref


def deallocate(
    orderid: str, sku: str, qty: int, uow: unit_of_work.AbstractUnitOfWork
) -> None:
    line = model.OrderLine(orderid, sku, qty)
    with uow:
        batches = uow.batches.list()
        product = model.Product(sku, batches)
        product.deallocate(line)
        uow.commit()
