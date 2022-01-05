import json

import pytest
import requests
from tenacity import Retrying, stop_after_delay

pytestmark = pytest.mark.e2e


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_add_batch(url, random_sku, random_batchref):
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref(1)
    laterbatch = random_batchref(2)

    response = requests.post(
        f"{url}/add_batch",
        json={
            "reference": earlybatch,
            "sku": sku,
            "qty": 100,
        },
    )

    assert response.status_code == 201, response.text

    response = requests.post(
        f"{url}/add_batch",
        json={
            "reference": laterbatch,
            "sku": othersku,
            "qty": 50,
            "eta": "2021-01-01",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["message"] == "OK"


@pytest.mark.usefixtures("restart_api")
def test_allocate_returns_200_and_allocated_batchref(
    url,
    post_to_add_batch,
    get_allocation,
    random_sku,
    random_batchref,
    random_orderid,
):
    orderid = random_orderid()
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref(1)
    laterbatch = random_batchref(2)
    otherbatch = random_batchref(3)

    post_to_add_batch(laterbatch, sku, 100, "2011-01-02")
    post_to_add_batch(earlybatch, sku, 100, "2011-01-01")
    post_to_add_batch(otherbatch, othersku, 100, None)

    data = {"orderid": orderid, "sku": sku, "qty": 3}
    response = requests.post(f"{url}/allocate", json=data)

    assert response.status_code == 202, response.text
    assert response.json()["message"] == "OK"

    response = get_allocation(orderid)
    assert response.status_code == 200, response.text
    assert response.json() == [
        {"batchref": earlybatch, "sku": sku, "qty": 3},
    ]


@pytest.mark.usefixtures("restart_api")
def test_allocate_retuns_400_and_out_of_stock_message(
    url,
    post_to_add_batch,
    get_allocation,
    random_sku,
    random_batchref,
    random_orderid,
):
    sku, small_batch, large_order = (
        random_sku(),
        random_batchref(),
        random_orderid(),
    )
    response = post_to_add_batch(small_batch, sku, 10, "2011-01-01")
    assert response.status_code == 201, response.text

    data = {"orderid": large_order, "sku": sku, "qty": 20}
    response = requests.post(f"{url}/allocate", json=data)

    assert response.status_code == 400, response.text
    assert response.json()["message"] == "Out of stock"

    response = get_allocation(large_order)
    assert response.status_code == 404, response.text


@pytest.mark.usefixtures("restart_api")
def test_allocate_returns_400_invalid_sku_message(
    url, get_allocation, random_sku, random_orderid
):
    unknown_sku, orderid = random_sku(), random_orderid()

    data = {"orderid": orderid, "sku": unknown_sku, "qty": 20}
    response = requests.post(f"{url}/allocate", json=data)

    assert response.status_code == 400, response.text
    assert response.json()["message"] == f"Invalid sku {unknown_sku}"

    response = get_allocation(orderid)
    assert response.status_code == 404, response.text


@pytest.mark.usefixtures("restart_api")
def test_deallocate(
    url,
    post_to_add_batch,
    post_to_allocate,
    get_allocation,
    random_sku,
    random_batchref,
    random_orderid,
):
    sku, order1, order2 = random_sku(), random_orderid(), random_orderid()
    batch = random_batchref()
    post_to_add_batch(batch, sku, 100, "2011-01-01")

    # fully allocate
    response = post_to_allocate(order1, sku, 100)
    assert response.status_code == 202, response.text
    assert response.json()["message"] == "OK"
    response = get_allocation(order1)
    assert response.status_code == 200, response.text

    # cannot allocate second order
    response = post_to_allocate(order2, sku, 100)
    assert response.status_code == 400, response.text
    response = get_allocation(order2)
    assert response.status_code == 404, response.text

    # deallocate
    response = requests.post(
        f"{url}/deallocate", json={"orderid": order1, "sku": sku, "qty": 100}
    )
    assert response.status_code == 200, response.text
    assert response.json()["message"] == "OK"

    # now we can allocate second order
    response = post_to_allocate(order2, sku, 100)
    assert response.status_code == 202, response.text
    assert response.json()["message"] == "OK"
    response = get_allocation(order2)
    assert response.status_code == 200, response.text


@pytest.mark.usefixtures("restart_api")
def test_change_batch_quantity_leading_to_reallocation(
    post_to_add_batch,
    post_to_allocate,
    random_sku,
    random_batchref,
    random_orderid,
    subscribe,
    publish,
):
    orderid, sku = random_orderid(), random_sku()
    earlier_batch, later_batch = random_batchref("old"), random_batchref("new")
    post_to_add_batch(earlier_batch, sku, 100, "2011-01-01")
    post_to_add_batch(later_batch, sku, 100, "2011-01-02")

    response = post_to_allocate(orderid, sku, 100)
    assert response.status_code == 202, response.text

    subscription = subscribe("line_allocated")

    publish("change_batch_quantity", {"batchref": earlier_batch, "qty": 50})

    for attempt in Retrying(stop=stop_after_delay(3), reraise=True):
        with attempt:
            message = subscription.get_message(timeout=1)
            if message:
                data = json.loads(message["data"])
                assert data["orderid"] == orderid
                assert data["batchref"] == later_batch
