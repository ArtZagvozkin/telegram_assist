#!/usr/bin/env python3

from telegram.ext import ApplicationBuilder

from config import TELEGRAM_TOKEN, MAX_HISTORY, LLM_PROVIDER, logger
from llm.gemini_client import GeminiClient
from storage.memory import MemoryContextStore
from telegram_bot.handlers import create_handlers


def build_llm_client():
    if LLM_PROVIDER == "gemini":
        logger.info("Using Gemini LLM provider")
        return GeminiClient()
    # elif LLM_PROVIDER == "openai":
    #     logger.info("Using openai LLM provider")
    #     return OpenAIClient(...)
    # elif LLM_PROVIDER == "ollama":
        # logger.info("Using ollama LLM provider")
    #     return OllamaClient(...)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def main() -> None:
    llm_client = build_llm_client()
    context_store = MemoryContextStore(max_history=MAX_HISTORY)

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    handlers = create_handlers(llm_client, context_store)
    for h in handlers:
        application.add_handler(h)

    application.run_polling()


if __name__ == "__main__":
    main()
