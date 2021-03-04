import uuid

import pytest
import requests

import config

pytestmark = pytest.mark.e2e


def random_suffix():
    return uuid.uuid4().hex[:6]


def random_sku(name=""):
    return f"sku-{name}-{random_suffix()}"


def random_batchref(name=""):
    return f"batch-{name}-{random_suffix()}"


def random_orderid(name=""):
    return f"order-{name}-{random_suffix()}"


@pytest.mark.usefixtures("restart_api")
def test_returns_200_and_allocated_batch(add_stock):
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref(1)
    laterbatch = random_batchref(2)
    otherbatch = random_batchref(3)
    add_stock(
        [
            (laterbatch, sku, 100, "2011-01-02"),
            (earlybatch, sku, 100, "2011-01-01"),
            (otherbatch, othersku, 100, None),
        ]
    )

    data = {"orderid": random_orderid(), "sku": sku, "qty": 3}
    url = config.get_api_url()
    response = requests.post(f"{url}/allocate", json=data)

    assert response.status_code == 201
    assert response.json()["batchref"] == earlybatch


@pytest.mark.usefixtures("restart_api")
def test_retuns_400_and_out_of_stock_message(add_stock):
    sku, small_batch, large_order = (
        random_sku(),
        random_batchref(),
        random_orderid(),
    )
    add_stock(
        [
            (small_batch, sku, 10, "2011-01-01"),
        ]
    )

    data = {"orderid": large_order, "sku": sku, "qty": 20}
    url = config.get_api_url()
    response = requests.post(f"{url}/allocate", json=data)

    assert response.status_code == 400
    assert response.json()["message"] == f"Out of stock for sku {sku}"


@pytest.mark.usefixtures("restart_api")
def test_returns_400_invalid_sku_message():
    unknown_sku, orderid = random_sku(), random_orderid()

    data = {"orderid": orderid, "sku": unknown_sku, "qty": 20}
    url = config.get_api_url()
    response = requests.post(f"{url}/allocate", json=data)

    assert response.status_code == 400
    assert response.json()["message"] == f"Invalid sku {unknown_sku}"
