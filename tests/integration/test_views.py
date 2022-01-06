from datetime import date

import pytest
from allocation import bootstrap, views
from allocation.domain import commands
from allocation.service_layer import unit_of_work

today = date.today()


@pytest.fixture
def messagebus(session_factory):
    bus = bootstrap.bootstrap(
        start_orm=False,
        uow=unit_of_work.SqlAlchemyUnitOfWork(session_factory),
        send_mail=lambda *args, **kwargs: None,
        publish=lambda *args, **kwargs: None,
    )
    return bus


def test_allocations_view(messagebus, random_orderid):
    orderid = random_orderid()
    messagebus.handle(commands.CreateBatch("sku1batch", "sku1", 50, None))
    messagebus.handle(commands.CreateBatch("sku2batch", "sku2", 50, today))
    messagebus.handle(commands.Allocate(orderid, "sku1", 20))
    messagebus.handle(commands.Allocate(orderid, "sku2", 20))
    # add a spurious batch and order to make sure we're getting the right ones
    messagebus.handle(
        commands.CreateBatch("sku1batch-later", "sku1", 50, today)
    )
    messagebus.handle(commands.Allocate(random_orderid(), "sku1", 30))
    messagebus.handle(commands.Allocate(random_orderid(), "sku2", 10))

    assert views.allocations(orderid, messagebus.uow) == [
        {"sku": "sku1", "batchref": "sku1batch", "qty": 20},
        {"sku": "sku2", "batchref": "sku2batch", "qty": 20},
    ]


def test_deallocation(messagebus, random_orderid):
    orderid = random_orderid()
    messagebus.handle(commands.CreateBatch("sku1batch", "sku1", 50, None))
    messagebus.handle(commands.CreateBatch("sku2batch", "sku1", 50, today))
    messagebus.handle(commands.Allocate(orderid, "sku1", 20))
    assert views.allocations(orderid, messagebus.uow) == [
        {"sku": "sku1", "qty": 20, "batchref": "sku1batch"},
    ]
    messagebus.handle(commands.ChangeBatchQuantity("sku1batch", 10))

    assert views.allocations(orderid, messagebus.uow) == [
        {"sku": "sku1", "qty": 20, "batchref": "sku2batch"},
    ]
