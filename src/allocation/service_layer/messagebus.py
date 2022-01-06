import logging
from typing import Any, Callable, Dict, List, Type, Union

from allocation.domain import commands, events
from allocation.service_layer import unit_of_work
from tenacity import RetryError, Retrying, stop_after_attempt, wait_exponential

Message = Union[commands.Command, events.Event]
logger = logging.getLogger(__name__)


class MessageBus:
    def __init__(
        self,
        uow: unit_of_work.AbstractUnitOfWork,
        event_handlers: Dict[Type[events.Event], List[Callable]],
        command_handlers: Dict[Type[commands.Command], Callable],
    ) -> None:
        self.uow = uow
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers
        self.queue = []  # type: List[Message]

    def handle(self, message: Message) -> List:
        results = []
        self.queue = [message]
        while self.queue:
            message = self.queue.pop(0)
            if isinstance(message, events.Event):
                self.handle_event(message)
            elif isinstance(message, commands.Command):
                result = self.handle_command(message)
                results.append(result)
            else:
                raise TypeError(f"Unknown message type {type(message)}")

        return results

    def handle_event(self, event: events.Event) -> None:
        for handler in self.event_handlers[type(event)]:
            try:
                for attempt in Retrying(
                    stop=stop_after_attempt(3),
                    wait=wait_exponential(multiplier=2),
                ):
                    with attempt:
                        logger.debug(f"Handling event: {event}")
                        handler(event)
                        self.queue.extend(self.uow.collect_new_events())
            except RetryError as retry_failure:
                logger.error(f"Retry error: {retry_failure}")
                continue

    def handle_command(self, command: commands.Command) -> Any:
        try:
            logger.debug(f"Handling command: {command}")
            handler = self.command_handlers[type(command)]
            result = handler(command)
            self.queue.extend(self.uow.collect_new_events())
            return result
        except Exception:
            logger.exception(f"Error handling command: {command}")
            raise
