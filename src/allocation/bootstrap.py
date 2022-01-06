import inspect
from typing import Callable

from allocation.adapters import email, event_publisher, orm
from allocation.service_layer import messagebus, unit_of_work, handlers


def bootstrap(
    start_orm: bool = True,
    uow: unit_of_work.AbstractUnitOfWork = unit_of_work.SqlAlchemyUnitOfWork(),
    send_mail: Callable = email.send_mail,
    publish: Callable = event_publisher.publish,
) -> messagebus.MessageBus:

    if start_orm:
        orm.start_mappers()

    dependencies = {"uow": uow, "send_mail": send_mail, "publish": publish}
    injected_event_handlers = {
        event_type: [
            inject_dependencies(event_handler, dependencies)
            for event_handler in event_handlers
        ]
        for event_type, event_handlers in handlers.EVENT_HANDLERS.items()
    }
    injected_commans_handlers = {
        command_type: inject_dependencies(command_handler, dependencies)
        for command_type, command_handler in handlers.COMMAND_HANDLERS.items()
    }
    return messagebus.MessageBus(
        uow=uow,
        event_handlers=injected_event_handlers,
        command_handlers=injected_commans_handlers,
    )


def inject_dependencies(handler: Callable, dependencies: dict) -> Callable:
    params = inspect.signature(handler).parameters
    deps = {
        name: dependency
        for name, dependency in dependencies.items()
        if name in params
    }
    return lambda *args, **kwargs: handler(*args, **{**deps, **kwargs})
