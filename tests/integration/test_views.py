from datetime import date

from allocation import views
from allocation.domain import commands
from allocation.service_layer import messagebus, unit_of_work

today = date.today()


def test_allocations_view(session_factory, random_orderid):
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    orderid = random_orderid()
    messagebus.handle(commands.CreateBatch("sku1batch", "sku1", 50, None), uow)
    messagebus.handle(commands.CreateBatch("sku2batch", "sku2", 50, today), uow)
    messagebus.handle(commands.Allocate(orderid, "sku1", 20), uow)
    messagebus.handle(commands.Allocate(orderid, "sku2", 20), uow)
    # add a spurious batch and order to make sure we're getting the right ones
    messagebus.handle(
        commands.CreateBatch("sku1batch-later", "sku1", 50, today), uow
    )
    messagebus.handle(commands.Allocate(random_orderid(), "sku1", 30), uow)
    messagebus.handle(commands.Allocate(random_orderid(), "sku2", 10), uow)

    assert views.allocations(orderid, uow) == [
        {"sku": "sku1", "batchref": "sku1batch", "qty": 20},
        {"sku": "sku2", "batchref": "sku2batch", "qty": 20},
    ]


def test_deallocation(session_factory, random_orderid):
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    orderid = random_orderid()
    messagebus.handle(commands.CreateBatch("sku1batch", "sku1", 50, None), uow)
    messagebus.handle(commands.CreateBatch("sku2batch", "sku1", 50, today), uow)
    messagebus.handle(commands.Allocate(orderid, "sku1", 20), uow)
    assert views.allocations(orderid, uow) == [
        {"sku": "sku1", "qty": 20, "batchref": "sku1batch"},
    ]
    messagebus.handle(commands.ChangeBatchQuantity("sku1batch", 10), uow)

    assert views.allocations(orderid, uow) == [
        {"sku": "sku1", "qty": 20, "batchref": "sku2batch"},
    ]
