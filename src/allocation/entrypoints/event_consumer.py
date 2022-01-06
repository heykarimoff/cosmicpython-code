import json
import logging

from allocation import bootstrap, config
from allocation.domain import commands
from redis import Redis

logger = logging.getLogger(__name__)
redis_client = Redis(**config.get_redis_host_and_port())


def main():
    messagebus = bootstrap.bootstrap()
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("change_batch_quantity")

    for message in pubsub.listen():
        logger.debug(f"Received message: {message}")
        handle_change_batch_quantity(message, messagebus)


def handle_change_batch_quantity(message, messagebus):
    data = json.loads(message["data"])
    command = commands.ChangeBatchQuantity(data["batchref"], data["qty"])
    messagebus.handle(message=command)


if __name__ == "__main__":
    main()
