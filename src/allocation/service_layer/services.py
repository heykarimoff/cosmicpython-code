from datetime import date
from typing import Optional

from allocation.domain import model
from allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


def add_batch(
    reference: str,
    sku: str,
    qty: int,
    eta: Optional[date],
    uow: unit_of_work.AbstractUnitOfWork,
):
    batch = model.Batch(reference, sku, qty, eta)
    with uow:
        product = uow.products.get(sku=sku)
        if product is None:
            product = model.Product(sku, [])
            uow.products.add(product)
        product.batches.append(batch)
        uow.commit()


def allocate(
    orderid: str, sku: str, qty: int, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = model.OrderLine(orderid, sku, qty)

    with uow:
        product = uow.products.get(sku=sku)

        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")

        batchref = product.allocate(line)
        uow.commit()

    return batchref


def deallocate(
    orderid: str, sku: str, qty: int, uow: unit_of_work.AbstractUnitOfWork
) -> None:
    line = model.OrderLine(orderid, sku, qty)
    with uow:
        product = uow.products.get(sku=sku)

        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")

        product.deallocate(line)
        uow.commit()
