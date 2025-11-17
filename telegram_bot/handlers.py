from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import SYSTEM_PROMPT, logger
from llm.base import LLMClient
from storage.base import BaseContextStore
from telegram_bot.utils import split_message
from telegram_bot.message_adapter import parse_message, to_chat_message


def create_handlers(llm_client: LLMClient, context_store: BaseContextStore):
    """
    Фабрика хендлеров. Внутренние функции-обработчики видят llm_client и context_store
    через замыкание.
    """

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if message:
            await message.reply_text("Привет! Я чат-бот, чем могу помочь?")

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

        # 1. Парсим входящее сообщение
        parsed = await parse_message(message)
        user_message = to_chat_message(parsed)

        if user_message is None:
            logger.warning("No text or supported media found, exiting")
            await message.reply_text(
                "Пока я понимаю только текст, изображения, файлы и аудио 🙂"
            )
            return

        # 2. Работа с контекстом
        context_store.append_message(user_id, user_message)
        history = context_store.get_history(user_id)

        messages_for_llm = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ] + history

        # 3. Запрос к LLM
        try:
            assistant_response = await llm_client.generate(messages_for_llm)
            if not assistant_response:
                logger.error("LLM returned empty text for user %s", user_id)
                await message.reply_text("Не смог получить ответ от модели 😔")
                return

            # 4. Сохраняем ответ ассистента в контекст
            context_store.append_message(
                user_id,
                {"role": "assistant", "content": assistant_response},
            )

            # 5. Режем длинный ответ на части
            for chunk in split_message(assistant_response):
                await message.reply_text(chunk)

        except Exception:
            logger.exception(
                "Error while getting response from LLM for user %s", user_id
            )
            await message.reply_text("Произошла ошибка, попробуйте позже.")

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
