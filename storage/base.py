from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseContextStore(ABC):
    """Базовый интерфейс для хранилища контекста (память, Redis, БД и т.п.)."""

    @abstractmethod
    def get_history(self, user_id: int) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def append_message(self, user_id: int, message: Dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def reset(self, user_id: int) -> None:
        raise NotImplementedError
