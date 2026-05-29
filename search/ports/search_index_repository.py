from abc import ABC, abstractmethod


class SearchIndexRepository(ABC):
    @abstractmethod
    def index(self, doc: dict) -> bool: ...

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[dict]: ...

    @abstractmethod
    def delete(self, doc_id: str) -> bool: ...

    @abstractmethod
    def clear(self) -> None: ...

    @property
    @abstractmethod
    def doc_count(self) -> int: ...
