from allocation.adapters import email
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


def change_batch_quantity(message: commands.ChangeBatchQuantity, uow):
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


def send_out_of_stock_notification(
    message: events.OutOfStock, uow: unit_of_work.AbstractUnitOfWork
):
    email.send_mail("stock-admin@made.com", f"Out of stock: {message.sku}")
