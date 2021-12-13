import uuid

import pytest
import requests
from allocation import config

pytestmark = pytest.mark.e2e


def random_suffix():
    return uuid.uuid4().hex[:6]


def random_sku(name=""):
    return f"sku-{name}-{random_suffix()}"


def random_batchref(name=""):
    return f"batch-{name}-{random_suffix()}"


def random_orderid(name=""):
    return f"order-{name}-{random_suffix()}"


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_add_batch(url):
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

    assert response.status_code == 201

    response = requests.post(
        f"{url}/add_batch",
        json={
            "reference": laterbatch,
            "sku": othersku,
            "qty": 50,
            "eta": "2021-01-01",
        },
    )
    assert response.status_code == 201


@pytest.mark.usefixtures("restart_api")
def test_returns_200_and_allocated_batch(url, post_to_add_stock):
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref(1)
    laterbatch = random_batchref(2)
    otherbatch = random_batchref(3)

    post_to_add_stock(laterbatch, sku, 100, "2011-01-02")
    post_to_add_stock(earlybatch, sku, 100, "2011-01-01")
    post_to_add_stock(otherbatch, othersku, 100, None)

    data = {"orderid": random_orderid(), "sku": sku, "qty": 3}
    response = requests.post(f"{url}/allocate", json=data)

    assert response.status_code == 201
    assert response.json()["batchref"] == earlybatch


@pytest.mark.usefixtures("restart_api")
def test_retuns_400_and_out_of_stock_message(url, post_to_add_stock):
    sku, small_batch, large_order = (
        random_sku(),
        random_batchref(),
        random_orderid(),
    )
    post_to_add_stock(small_batch, sku, 10, "2011-01-01")

    data = {"orderid": large_order, "sku": sku, "qty": 20}
    response = requests.post(f"{url}/allocate", json=data)

    assert response.status_code == 400
    assert response.json()["message"] == f"Out of stock"


@pytest.mark.usefixtures("restart_api")
def test_returns_400_invalid_sku_message(url):
    unknown_sku, orderid = random_sku(), random_orderid()

    data = {"orderid": orderid, "sku": unknown_sku, "qty": 20}
    response = requests.post(f"{url}/allocate", json=data)

    assert response.status_code == 400
    assert response.json()["message"] == f"Invalid sku {unknown_sku}"


@pytest.mark.usefixtures("restart_api")
def test_deallocate(url, post_to_add_stock):
    sku, order1, order2 = random_sku(), random_orderid(), random_orderid()
    batch = random_batchref()
    post_to_add_stock(batch, sku, 100, "2011-01-01")

    # fully allocate
    response = requests.post(
        f"{url}/allocate", json={"orderid": order1, "sku": sku, "qty": 100}
    )

    assert response.json()["batchref"] == batch

    # cannot allocate second order
    response = requests.post(
        f"{url}/allocate", json={"orderid": order2, "sku": sku, "qty": 100}
    )

    assert response.status_code == 400

    # deallocate
    response = requests.post(
        f"{url}/deallocate", json={"orderid": order1, "sku": sku, "qty": 100}
    )
    assert response.ok

    # now we can allocate second order
    response = requests.post(
        f"{url}/allocate", json={"orderid": order2, "sku": sku, "qty": 100}
    )
    assert response.ok
    assert response.json()["batchref"] == batch
