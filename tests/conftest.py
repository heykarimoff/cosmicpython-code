import time
from pathlib import Path

import pytest
import requests
from allocation import config
from allocation.adapters.orm import metadata, start_mappers
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
def post_to_add_stock(url):
    def _add_stock(reference, sku, qty, eta):
        response = requests.post(
            f"{url}/add_batch",
            json={"reference": reference, "sku": sku, "qty": qty, "eta": eta},
        )
        assert response.status_code == 201

    return _add_stock


@pytest.fixture
def restart_api():
    (
        Path(__file__).parent / "../src/allocation/entrypoints/flask_app.py"
    ).touch()
    time.sleep(0.5)
    wait_for_webapp_to_come_up()
