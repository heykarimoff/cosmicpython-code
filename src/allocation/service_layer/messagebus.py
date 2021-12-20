import logging
from typing import Any, List, Union

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
            handle_event(message, queue, uow)
        elif isinstance(message, commands.Command):
            result = handle_command(message, queue, uow)
            results.append(result)
        else:
            raise TypeError(f"Unknown message type {type(message)}")

    return results


def handle_event(
    event: events.Event,
    queue: List[Message],
    uow: unit_of_work.AbstractUnitOfWork,
) -> None:
    for handler in EVENT_HANDLERS[type(event)]:
        try:
            logger.debug(f"Handling event: {event}")
            handler(event, uow)
            queue.extend(uow.collect_new_events())
        except Exception:
            logger.exception(f"Error handling event: {event}")
            continue


def handle_command(
    command: commands.Command,
    queue: List[Message],
    uow: unit_of_work.AbstractUnitOfWork,
) -> Any:
    try:
        logger.debug(f"Handling command: {command}")
        handler = COMMAND_HANDLERS[type(command)]
        result = handler(command, uow)
        queue.extend(uow.collect_new_events())
        return result
    except Exception:
        logger.exception(f"Error handling command: {command}")
        raise


EVENT_HANDLERS = {
    events.OutOfStock: [handlers.send_out_of_stock_notification],
}


COMMAND_HANDLERS = {
    commands.CreateBatch: handlers.add_batch,
    commands.ChangeBatchQuantity: handlers.change_batch_quantity,
    commands.Allocate: handlers.allocate,
    commands.Deallocate: handlers.deallocate,
}
