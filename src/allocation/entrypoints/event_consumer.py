import json
import logging

from allocation import config
from allocation.adapters import orm
from allocation.domain import commands
from allocation.service_layer import messagebus, unit_of_work
from redis import Redis

logger = logging.getLevelName(__name__)
redis_client = Redis(**config.get_redis_host_and_port())


def main():
    orm.start_mappers()
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("change_batch_quantity")

    for message in pubsub.listen():
        logger.debug(f"Received message: {message}")


def handle_change_batch_quantity(message):
    data = json.loads(message["data"])
    command = commands.ChangeBatchQuantity(data["reference"], data["qty"])
    messagebus.handle(message=command, uow=unit_of_work.SqlAlchemyUnitOfWork())
