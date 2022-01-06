from datetime import date, timedelta

import pytest
from allocation.domain.events import OutOfStock
from allocation.domain.model import Batch, OrderLine, Product

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


@pytest.mark.smoke
def test_prefers_warehouse_batches_to_shipments():
    in_stock_batch = Batch("batch-001", "BIG-SOFA", qty=20, eta=None)
    shipment_batch = Batch("batch-002", "BIG-SOFA", qty=20, eta=today)
    product = Product(sku="BIG-SOFA", batches=[in_stock_batch, shipment_batch])
    line = OrderLine("order-123", "BIG-SOFA", 5)

    product.allocate(line)

    assert in_stock_batch.available_quantity == 15
    assert shipment_batch.available_quantity == 20


def test_returns_allocated_batch_reference():
    in_stock_batch = Batch("batch-001", "BIG-SOFA", qty=20, eta=None)
    shipment_batch = Batch("batch-002", "BIG-SOFA", qty=20, eta=today)
    product = Product(sku="BIG-SOFA", batches=[in_stock_batch, shipment_batch])
    line = OrderLine("order-123", "BIG-SOFA", 5)

    allocation = product.allocate(line)

    assert allocation == in_stock_batch.reference


@pytest.mark.smoke
def test_prefers_earlier_batches():
    tomorrows_batch = Batch("batch-001", "MINI-SPOON", qty=20, eta=tomorrow)
    upcoming_batch = Batch("batch-001", "MINI-SPOON", qty=20, eta=later)
    product = Product(
        sku="MINI-SPOON", batches=[tomorrows_batch, upcoming_batch]
    )
    line = OrderLine("order-123", "MINI-SPOON", 5)

    allocation = product.allocate(line)

    assert allocation == tomorrows_batch.reference
    assert tomorrows_batch.available_quantity == 15
    assert upcoming_batch.available_quantity == 20


def test_raises_out_of_stock_exception_if_cannot_allocate():
    batch = Batch("batch-001", "SMALL-TABLE", qty=5, eta=today)
    line1 = OrderLine("order-1", "SMALL-TABLE", 5)
    line2 = OrderLine("order-2", "SMALL-TABLE", 5)

    product = Product(sku="SMALL-TABLE", batches=[batch])
    product.allocate(line1)

    allocation = product.allocate(line2)
    assert product.events[-1] == OutOfStock(sku="SMALL-TABLE")
    assert allocation is None
