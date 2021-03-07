from datetime import date, timedelta

import pytest

from domain.model import Batch, OrderLine, OutOfStock, allocate

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def test_prefers_warehouse_batches_to_shipments():
    in_stock_batch = Batch("batch-001", "BIG-SOFA", qty=20, eta=None)
    shipment_batch = Batch("batch-002", "BIG-SOFA", qty=20, eta=today)
    line = OrderLine("order-123", "BIG-SOFA", 5)

    allocate(line, [in_stock_batch, shipment_batch])

    assert in_stock_batch.available_quantity == 15
    assert shipment_batch.available_quantity == 20


def test_returns_allocated_batch_reference():
    in_stock_batch = Batch("batch-001", "BIG-SOFA", qty=20, eta=None)
    shipment_batch = Batch("batch-002", "BIG-SOFA", qty=20, eta=today)
    line = OrderLine("order-123", "BIG-SOFA", 5)

    allocation = allocate(line, [in_stock_batch, shipment_batch])

    assert allocation == in_stock_batch.reference


def test_prefers_earlier_batches():
    tomorrows_batch = Batch("batch-001", "BIG-SOFA", qty=20, eta=tomorrow)
    upcoming_batch = Batch("batch-001", "BIG-SOFA", qty=20, eta=later)
    line = OrderLine("order-123", "BIG-SOFA", 5)

    allocation = allocate(line, [tomorrows_batch, upcoming_batch])

    assert allocation == tomorrows_batch.reference
    assert tomorrows_batch.available_quantity == 15
    assert upcoming_batch.available_quantity == 20


def test_raises_out_of_stock_exception_if_cannot_allocate():
    batch = Batch("batch-001", "SMALL-TABLE", qty=5, eta=today)
    line1 = OrderLine("order-1", "SMALL-TABLE", 5)
    line2 = OrderLine("order-2", "SMALL-TABLE", 5)

    allocate(line1, [batch])

    with pytest.raises(OutOfStock, match="SMALL-TABLE"):
        allocate(line2, [batch])
