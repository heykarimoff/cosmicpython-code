from datetime import date, timedelta

from allocation.domain.model import Batch, OrderLine

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def make_batch_and_line(sku, batch_qty, line_qty):
    return (
        Batch("batch-001", sku, batch_qty, eta=today),
        OrderLine("order-123", sku, line_qty),
    )


def test_allocating_to_a_batch_reduces_the_available_quantity():
    batch, line = make_batch_and_line("SMALL-TABLE", 20, 10)

    batch.allocate(line)

    assert batch.available_quantity == 10


def test_can_allocate_if_available_greater_than_required():
    large_batch, small_line = make_batch_and_line("SMALL-TABLE", 20, 2)

    assert large_batch.can_allocate(small_line)


def test_cannot_allocate_if_available_smaller_than_required():
    small_batch, large_line = make_batch_and_line("SMALL-TABLE", 10, 20)

    assert not small_batch.can_allocate(large_line)


def test_can_allocate_if_available_equal_to_required():
    batch, line = make_batch_and_line("SMALL-TABLE", 20, 20)

    assert batch.can_allocate(line)


def test_cannot_allocate_if_skus_do_not_match():
    batch = Batch("batch-001", "SMALL-TABLE", qty=20, eta=today)
    line = OrderLine("order-123", "BIG-SOFA", 2)

    assert not batch.can_allocate(line)


def test_can_only_deallocate_allocated_lines():
    batch, unallocated_line = make_batch_and_line("ARM-CHAIR", 20, 5)

    batch.deallocate(unallocated_line)

    assert batch.available_quantity == 20


def test_allocation_is_idempotent():
    batch, line = make_batch_and_line("ARM-CHAIR", 20, 5)

    batch.allocate(line)
    batch.allocate(line)
    batch.allocate(line)

    assert batch.available_quantity == 15
