from __future__ import annotations

from typing import Dict, List, Any

from .base import BaseContextStore


class MemoryContextStore(BaseContextStore):
    """
    In-memory хранилище.
    На будущее: можно сделать RedisContextStore / PostgresContextStore
    с тем же интерфейсом.
    """

    def __init__(self, max_history: int = 10):
        self._store: Dict[int, List[Dict[str, Any]]] = {}
        self._max_history = max_history

    def get_history(self, user_id: int) -> List[Dict[str, Any]]:
        return self._store.get(user_id, [])

    def append_message(self, user_id: int, message: Dict[str, Any]) -> None:
        history = self._store.setdefault(user_id, [])
        history.append(message)
        if len(history) > self._max_history:
            self._store[user_id] = history[-self._max_history :]

    def reset(self, user_id: int) -> None:
        self._store.pop(user_id, None)
