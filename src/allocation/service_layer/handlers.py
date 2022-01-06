from dataclasses import asdict
from typing import Callable

from allocation.domain import commands, events, model
from allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


def add_batch(
    message: commands.CreateBatch, uow: unit_of_work.AbstractUnitOfWork
):
    sku = message.sku
    batch = model.Batch(
        message.reference, message.sku, message.qty, message.eta
    )
    with uow:
        product = uow.products.get(sku=sku)
        if product is None:
            product = model.Product(sku, [])
            uow.products.add(product)
        product.batches.append(batch)
        uow.commit()


def change_batch_quantity(
    message: commands.ChangeBatchQuantity, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        product = uow.products.get_by_batch_reference(
            reference=message.reference
        )
        product.change_batch_quantity(
            reference=message.reference, qty=message.qty
        )
        uow.commit()


def allocate(
    message: commands.Allocate, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = model.OrderLine(message.orderid, message.sku, message.qty)

    with uow:
        product = uow.products.get(sku=message.sku)

        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")

        batchref = product.allocate(line)
        uow.commit()

    return batchref


def reallocate(
    message: events.Deallocated, uow: unit_of_work.AbstractUnitOfWork
) -> None:
    allocate(commands.Allocate(**asdict(message)), uow)


def deallocate(
    message: commands.Deallocate, uow: unit_of_work.AbstractUnitOfWork
) -> None:
    line = model.OrderLine(message.orderid, message.sku, message.qty)
    with uow:
        product = uow.products.get(sku=message.sku)

        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")

        product.deallocate(line)
        uow.commit()


def publish_allocated_event(
    message: events.Allocated, publish: Callable
) -> None:
    publish("line_allocated", message)


def send_out_of_stock_notification(
    message: events.OutOfStock, send_mail: Callable
) -> None:
    send_mail("stock-admin@made.com", f"Out of stock: {message.sku}")


def add_allocation_to_read_model(
    message: events.Allocated, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        uow.session.execute(
            "INSERT INTO allocations_view (orderid, sku, qty, batchref)"
            " VALUES (:orderid, :sku, :qty, :batchref)",
            {
                "orderid": message.orderid,
                "sku": message.sku,
                "qty": message.qty,
                "batchref": message.batchref,
            },
        )
        uow.commit()


def remove_allocation_from_read_model(
    message: events.Deallocated, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        uow.session.execute(
            "DELETE FROM allocations_view"
            " WHERE orderid = :orderid AND sku = :sku",
            {
                "orderid": message.orderid,
                "sku": message.sku,
            },
        )
        uow.commit()


EVENT_HANDLERS = {
    events.Allocated: [
        publish_allocated_event,
        add_allocation_to_read_model,
    ],
    events.Deallocated: [
        reallocate,
        remove_allocation_from_read_model,
    ],
    events.OutOfStock: [send_out_of_stock_notification],
}


COMMAND_HANDLERS = {
    commands.CreateBatch: add_batch,
    commands.ChangeBatchQuantity: change_batch_quantity,
    commands.Allocate: allocate,
    commands.Deallocate: deallocate,
}
