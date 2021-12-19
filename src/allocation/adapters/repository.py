import abc
from typing import List, Protocol, Set

from allocation.domain import model
from sqlalchemy.orm.session import Session


class AbstractRepository(Protocol):
    @abc.abstractmethod
    def add(self, product: model.Product):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, sku: model.Sku) -> model.Product:
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_batch_reference(
        self, reference: model.Reference
    ) -> model.Product:
        raise NotImplementedError

    @abc.abstractmethod
    def list(self) -> List[model.Product]:
        raise NotImplementedError


class TrackingRepository:
    seen = Set[model.Product]

    def __init__(self, repo: AbstractRepository):
        self._repo = repo
        self.seen = set()  # type: Set[model.Product]

    def add(self, product: model.Product):
        self._repo.add(product)
        self.seen.add(product)

    def get(self, sku: model.Sku) -> model.Product:
        product = self._repo.get(sku)
        if product:
            self.seen.add(product)
        return product

    def get_by_batch_reference(
        self, reference: model.Reference
    ) -> model.Product:
        product = self._repo.get_by_batch_reference(reference)
        if product:
            self.seen.add(product)
        return product

    def list(self) -> List[model.Product]:
        return self._repo.list()


class SqlAlchemyRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, product: model.Product):
        self.session.add(product)

    def get(self, sku: model.Sku) -> model.Product:
        return self.session.query(model.Product).filter_by(sku=sku).first()

    def get_by_batch_reference(
        self, reference: model.Reference
    ) -> model.Product:
        return (
            self.session.query(model.Product)
            .join(model.Batch)
            .filter(model.Batch.reference == reference)
            .first()
        )

    def list(self):
        return self.session.query(model.Product).all()
