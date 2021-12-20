import logging
from typing import Union

from allocation.domain import commands, events
from allocation.service_layer import handlers, unit_of_work

Message = Union[commands.Command, events.Event]
logger = logging.getLogger(__name__)


def handle(message: Message, uow: unit_of_work.AbstractUnitOfWork):
    results = []
    queue = [message]
    while queue:
        message = queue.pop(0)
        if isinstance(message, events.Event):
            for handler in EVENT_HANDLERS[type(message)]:
                try:
                    logger.debug(f"Handling event: {message}")
                    handler(message, uow)
                    queue.extend(uow.collect_new_events())
                except Exception:
                    logger.exception(f"Error handling event: {message}")
                    continue
        elif isinstance(message, commands.Command):
            try:
                logger.debug(f"Handling command: {message}")
                handler = COMMAND_HANDLERS[type(message)]
                result = handler(message, uow)
                results.append(result)
                queue.extend(uow.collect_new_events())
            except Exception:
                logger.exception(f"Error handling command: {message}")
                raise
        else:
            raise TypeError(f"Unknown message type {type(message)}")

    return results


EVENT_HANDLERS = {
    events.OutOfStock: [handlers.send_out_of_stock_notification],
}


COMMAND_HANDLERS = {
    commands.CreateBatch: handlers.add_batch,
    commands.ChangeBatchQuantity: handlers.change_batch_quantity,
    commands.Allocate: handlers.allocate,
    commands.Deallocate: handlers.deallocate,
}
