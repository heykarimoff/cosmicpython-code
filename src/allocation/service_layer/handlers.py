from datetime import date
from typing import Optional

from allocation.adapters import email
from allocation.domain import events, model
from allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


def add_batch(event: events.BatchCreated, uow: unit_of_work.AbstractUnitOfWork):
    sku = event.sku
    batch = model.Batch(event.reference, event.sku, event.qty, event.eta)
    with uow:
        product = uow.products.get(sku=sku)
        if product is None:
            product = model.Product(sku, [])
            uow.products.add(product)
        product.batches.append(batch)
        uow.commit()


def allocate(
    event: events.AllocationRequired, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = model.OrderLine(event.orderid, event.sku, event.qty)

    with uow:
        product = uow.products.get(sku=event.sku)

        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")

        batchref = product.allocate(line)
        uow.commit()

    return batchref


def deallocate(
    event: events.DeallocationRequired, uow: unit_of_work.AbstractUnitOfWork
) -> None:
    line = model.OrderLine(event.orderid, event.sku, event.qty)
    with uow:
        product = uow.products.get(sku=event.sku)

        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")

        product.deallocate(line)
        uow.commit()


def send_out_of_stock_notification(
    event: events.OutOfStock, uow: unit_of_work.AbstractUnitOfWork
):
    email.send_mail("stock-admin@made.com", f"Out of stock: {event.sku}")
