import json
import time
import uuid
from pathlib import Path

import pytest
import requests
from allocation import config
from allocation.adapters.orm import metadata, start_mappers
from redis import Redis
from requests.exceptions import ConnectionError
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import clear_mappers, sessionmaker


@pytest.fixture
def url():
    return config.get_api_url()


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(in_memory_db):
    start_mappers()
    yield sessionmaker(bind=in_memory_db)
    clear_mappers()


@pytest.fixture
def session(session_factory):
    return session_factory()


def wait_for_postgres_to_come_up(engine):
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            return engine.connect()
        except OperationalError:
            time.sleep(0.5)
    pytest.fail("Postgres never came up")


def wait_for_webapp_to_come_up():
    deadline = time.time() + 10
    url = config.get_api_url()
    while time.time() < deadline:
        try:
            return requests.get(url)
        except ConnectionError:
            time.sleep(0.5)
    pytest.fail("API never came up")


@pytest.fixture(scope="session")
def postgres_db():
    engine = create_engine(config.get_postgres_uri())
    wait_for_postgres_to_come_up(engine)
    metadata.create_all(engine)
    return engine


@pytest.fixture
def postgres_session_factory(postgres_db):
    start_mappers()
    yield sessionmaker(bind=postgres_db)
    clear_mappers()


@pytest.fixture
def postgres_session(postgres_session_factory):
    return postgres_session_factory()


@pytest.fixture
def restart_api():
    (
        Path(__file__).parent / "../src/allocation/entrypoints/flask_app.py"
    ).touch()
    time.sleep(0.5)
    wait_for_webapp_to_come_up()


@pytest.fixture
def post_to_add_batch(url):
    def _add_batch(reference, sku, qty, eta):
        response = requests.post(
            f"{url}/add_batch",
            json={"reference": reference, "sku": sku, "qty": qty, "eta": eta},
        )
        return response

    return _add_batch


@pytest.fixture
def post_to_allocate(url):
    def _allocate(orderid, sku, qty):
        response = requests.post(
            f"{url}/allocate",
            json={"orderid": orderid, "sku": sku, "qty": qty},
        )
        return response

    return _allocate


@pytest.fixture(scope="session")
def redis_client():
    return Redis(**config.get_redis_host_and_port())


@pytest.fixture
def subscribe(redis_client):
    def _subscribe(channel):
        pubsub = redis_client.pubsub()
        pubsub.subscribe(channel)
        confirmation = pubsub.get_message(timeout=3)
        assert confirmation.get("type") == "subscribe"
        return pubsub

    return _subscribe


@pytest.fixture
def publish(redis_client):
    def _publish(channel, message):
        redis_client.publish(channel, json.dumps(message))

    return _publish


@pytest.fixture
def random_suffix():
    def _random_suffix():
        return uuid.uuid4().hex[:6]

    return _random_suffix


@pytest.fixture
def random_sku(random_suffix):
    def _random_sku(name=""):
        return f"sku-{name}-{random_suffix()}"

    return _random_sku


@pytest.fixture
def random_batchref(random_suffix):
    def _random_batchref(name=""):
        return f"batch-{name}-{random_suffix()}"

    return _random_batchref


@pytest.fixture
def random_orderid(random_suffix):
    def _random_orderid(name=""):
        return f"order-{name}-{random_suffix()}"

    return _random_orderid
