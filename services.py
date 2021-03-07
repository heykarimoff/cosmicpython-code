import model
import repository


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches) -> bool:
    return sku in {b.sku for b in batches}


def add_batch(batch: model.Batch, repo: repository.AbstractRepository, session):
    repo.add(batch)
    session.commit()


def allocate(
    line: model.OrderLine, repo: repository.AbstractRepository, session
) -> str:
    batches = repo.list()

    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")

    batchref = model.allocate(line, batches)
    session.commit()

    return batchref


def deallocate(
    line: model.OrderLine, repo: repository.AbstractRepository, session
) -> None:
    batches = repo.list()

    model.deallocate(line, batches)
    session.commit()
