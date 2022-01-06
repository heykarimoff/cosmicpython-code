from allocation.service_layer import unit_of_work
from typing import List, Dict


def allocations(
    orderid: str, uow: unit_of_work.SqlAlchemyUnitOfWork
) -> List[Dict]:
    with uow:
        results = list(
            uow.session.execute(
                "SELECT sku, qty, batchref"
                " FROM allocations_view"
                " WHERE orderid = :orderid",
                {"orderid": orderid},
            )
        )

    return [
        {"sku": sku, "batchref": batchref, "qty": qty}
        for sku, qty, batchref in results
    ]
