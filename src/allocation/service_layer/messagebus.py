from typing import Union

from allocation.domain import commands, events
from allocation.service_layer import handlers, unit_of_work

Message = Union[commands.Command, events.Event]


def handle(message: Message, uow: unit_of_work.AbstractUnitOfWork):
    results = []
    queue = [message]
    while queue:
        message = queue.pop(0)
        if isinstance(message, events.Event):
            for handler in EVENT_HANDLERS[type(message)]:
                results.append(handler(message, uow))
                queue.extend(uow.collect_new_events())
        elif isinstance(message, commands.Command):
            handler = COMMAND_HANDLERS[type(message)]
            results.append(handler(message, uow))
            queue.extend(uow.collect_new_events())
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
