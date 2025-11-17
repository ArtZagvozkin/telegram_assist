from __future__ import annotations

from typing import List
from config import MAX_TELEGRAM_MESSAGE_LEN


def split_message(text: str, limit: int = MAX_TELEGRAM_MESSAGE_LEN) -> List[str]:
    """
    Разбивает длинный текст на части так, чтобы каждая влезала в лимит Telegram.
    Старается резать по переводам строк или пробелам.
    """
    chunks: List[str] = []
    current = text

    while len(current) > limit:
        split_pos = current.rfind("\n", 0, limit)
        if split_pos == -1:
            split_pos = current.rfind(" ", 0, limit)
        if split_pos == -1:
            split_pos = limit

        chunks.append(current[:split_pos].rstrip())
        current = current[split_pos:].lstrip()

    if current:
        chunks.append(current)

    return chunks
