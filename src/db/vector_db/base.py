from typing import Any, Dict, Iterable, Protocol


class VectorDB(Protocol):
    def __init__(self) -> None:
        pass

    def bulk(self, actions: Iterable[Dict[str, Any]]) -> None:
        raise NotImplementedError

    def query(self, index_name: str, query: Any) -> Any:
        raise NotImplementedError
