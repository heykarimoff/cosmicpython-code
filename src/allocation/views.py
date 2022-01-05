from allocation.service_layer import unit_of_work
from typing import List, Dict


def allocations(
    orderid: str, uow: unit_of_work.SqlAlchemyUnitOfWork
) -> List[Dict]:
    with uow:
        results = list(
            uow.session.execute(
                "SELECT ol.sku, ol.qty, b.reference"
                " FROM allocations AS a"
                " JOIN batches AS b ON a.batch_id = b.id"
                " JOIN order_lines AS ol ON a.orderline_id = ol.id"
                " WHERE ol.orderid = :orderid",
                {"orderid": orderid},
            )
        )

    return [
        {"sku": sku, "batchref": batchref, "qty": qty}
        for sku, qty, batchref in results
    ]
