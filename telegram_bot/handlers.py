from __future__ import annotations

from telegram import Update, Message
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import SYSTEM_PROMPT, logger
from storage.base import BaseContextStore
from telegram_bot.utils import convert_to_md_v2, split_md_v2
from telegram_bot.message_adapter import parse_message, to_chat_message
from llm.base import (
    LLMClient,
    LLMError,
    LLMOverloadedError,
    LLMQuotaExceededError,
)


async def send_reply(message: Message, text: str) -> None:
    if not text or not text.strip():
        logger.warning("send_reply called with empty text")
        await message.reply_text("Ответ получился пустым 😔 Попробуй спросить иначе.")
        return

    try:
        md_text = convert_to_md_v2(text)
        chunks = split_md_v2(md_text)
    except Exception:
        logger.exception("MarkdownV2 conversion/split failed")
        await message.reply_text(
            "Я сгенерировал ответ, но не смог корректно его отформатировать для Telegram. "
            "Попробуй переформулировать запрос или сократить его 🙂"
        )
        return

    if not chunks:
        logger.warning("split_md_v2 returned no chunks for non-empty text")
        await message.reply_text("Ответ получился пустым 😔 Попробуй спросить иначе.")
        return

    for chunk in chunks:
        try:
            await message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN_V2)
        except TelegramError as e:
            logger.exception(
                "TelegramError while sending MarkdownV2.\n"
                "Error: %r\n"
                "Chunk preview: %r",
                e, chunk,
            )
            await message.reply_text(
                "Я подготовил ответ, но Telegram не смог его принять из-за форматирования. "
                "Попробуй задать вопрос ещё раз или чуть короче 🙂"
            )
            break


def create_handlers(llm_client: LLMClient, context_store: BaseContextStore):
    """
    Фабрика хендлеров.
    Внутренние функции-обработчики видят llm_client и context_store через замыкание.
    """

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if message:
            await message.reply_text("Привет! Чем могу помочь?")

    async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message

        if not user or not message:
            logger.warning("Reset called without proper user/message: %s", update)
            return

        user_id = user.id
        context_store.reset(user_id)

        logger.info("Context reset for user %s", user_id)
        await message.reply_text("Контекст очищен 🧹")

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        user = update.effective_user
        if message is None or user is None:
            logger.warning("Update without message or user: %s", update)
            return

        user_id = user.id
        logger.info("User id: %s", user_id)

        # Парсим входящее сообщение
        parsed = await parse_message(message)
        if parsed is None:
            logger.warning("parse_message returned None")
            await message.reply_text("Пока я понимаю только текст, изображения, файлы и аудио 🙂")
            return

        user_message = to_chat_message(parsed)
        if user_message is None:
            logger.warning("No text or supported media found, exiting")
            await message.reply_text(
                "Пока я понимаю только текст, изображения, файлы и аудио 🙂"
            )
            return

        # Работа с контекстом
        context_store.append_message(user_id, user_message)
        history = context_store.get_history(user_id)

        messages_for_llm = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ] + history

        # Запрос к LLM
        try:
            assistant_response = await llm_client.generate(messages_for_llm)
            if not assistant_response:
                logger.error("LLM returned empty text for user %s", user_id)
                await message.reply_text("Не смог получить ответ от модели 😔")
                return

            # Сохраняем ответ ассистента в контекст
            context_store.append_message(
                user_id,
                {"role": "assistant", "content": assistant_response},
            )

            await send_reply(message, assistant_response)

        except LLMQuotaExceededError:
            logger.warning("LLM quota exceeded (Gemini 429) for user %s", user_id)
            await message.reply_text(
                "Исчерпан доступный лимит запросов к модели. "
                "Лимит скоро обновится. Пожалуйста, попробуй ещё раз чуть позже 🙂"
            )

        except LLMOverloadedError:
            logger.warning("LLM overloaded (Gemini 503) for user %s", user_id)
            await message.reply_text(
                "Сейчас модель перегружена и временно недоступна. "
                "Пожалуйста, попробуй ещё раз чуть позже 🙂"
            )

        except LLMError:
            logger.exception(
                "LLMError while getting response from LLM for user %s", user_id
            )
            await message.reply_text(
                "Возникла ошибка при обращении к модели. "
                "Скорее всего проблема на стороне сервиса LLM. "
                "Пожалуйста, попробуй ещё раз чуть позже 🙂"
            )

        except Exception:
            logger.exception(
                "Unexpected error while processing message for user %s", user_id
            )
            await message.reply_text("Произошла непредвиденная ошибка, попробуйте позже.")

    return [
        CommandHandler("start", start),
        CommandHandler("reset", reset),
        MessageHandler(
            (filters.TEXT & ~filters.COMMAND)
            | filters.PHOTO
            | filters.Document.ALL
            | filters.VOICE
            | filters.AUDIO
            | filters.VIDEO
            | filters.VIDEO_NOTE,
            handle_message,
        ),
    ]
