from __future__ import annotations

import asyncio
from typing import List, Dict, Any, Optional

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL, logger
from .base import LLMClient, ChatMessage


class GeminiClient(LLMClient):
    def __init__(self, api_key: str = GEMINI_API_KEY, model: str = GEMINI_MODEL):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def generate(self, messages: List[ChatMessage]) -> Optional[str]:
        """
        Основной метод: принимает "универсальные" сообщения, конвертирует
        в формат Gemini и возвращает текст ответа.
        """
        contents = self._convert_messages_for_gemini(messages)

        loop = asyncio.get_running_loop()

        def _request() -> Optional[str]:
            resp = self._client.models.generate_content(
                model=self._model,
                contents=contents,
            )
            return getattr(resp, "text", None)

        logger.info("Sending request to Gemini")
        result = await loop.run_in_executor(None, _request)
        logger.info("Response from Gemini received")
        return result

    @staticmethod
    def _convert_messages_for_gemini(messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """
        Конвертация в формат Gemini:
        вход:
        {
            "role": "user"/"assistant"/"system",
            "content": "...",
            "images": [{"data": bytes, "mime_type": "image/jpeg"}, ...]
            "files":  [{"data": bytes, "mime_type": "application/pdf", "name": "file.pdf"}, ...]
        }

        выход:
        {
            "role": "user"/"model",
            "parts": [...]
        }
        """
        converted: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")

            if role == "assistant":
                role = "model"
            elif role == "system":
                # У Gemini нет system – передаём как user
                role = "user"

            parts: List[Dict[str, Any]] = []

            content = msg.get("content")
            if content:
                parts.append({"text": content})

            images = msg.get("images") or []
            for img in images:
                data = bytes(img["data"])
                mime_type = img.get("mime_type", "image/jpeg")
                parts.append(
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": data,
                        }
                    }
                )

            audios = msg.get("audios") or []
            for a in audios:
                data = bytes(a["data"])
                mime_type = a.get("mime_type", "audio/ogg")
                parts.append(
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": data,
                        }
                    }
                )

            files = msg.get("files") or []
            for f in files:
                data = bytes(f["data"])
                mime_type = f.get("mime_type", "application/octet-stream")
                parts.append(
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": data,
                        }
                    }
                )

            if parts:
                converted.append({"role": role, "parts": parts})

        return converted
