import json
import logging
from dataclasses import asdict

from allocation import config
from redis import Redis

logger = logging.getLogger(__name__)
redis_client = Redis(**config.get_redis_host_and_port())


def publish(channel, event):
    logger.debug(f"Publishing channel: {channel}, event: {event}")
    redis_client.publish(channel, json.dumps(asdict(event)))
