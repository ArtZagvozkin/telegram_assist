import os
from dotenv import load_dotenv
from logger import setup_logger

logger = setup_logger()

load_dotenv()


# --- Env / tokens ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in .env")

# --- Limits ---
MAX_HISTORY = 10
MAX_TELEGRAM_MESSAGE_LEN = 4000

# --- LLM ---
GEMINI_MODEL = "gemini-2.5-flash-lite-preview-09-2025"

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")

# --- Prompts ---
SYSTEM_PROMPT = """
Твоя роль: AI-эксперт по анализу и суммаризации текста.
Твоя цель: помогать пользователю быстро извлекать главные смыслы из предоставленных материалов,
давать структурированные ответы и при необходимости краткие выводы.
...
"""

DEFAULT_IMAGE_PROMPT = "Опиши это изображение."
DEFAULT_AUDIO_PROMPT = "Расшифруй и кратко перескажи это аудио."
DEFAULT_VIDEO_PROMPT = "Опиши и кратко перескажи содержание этого видео."
DEFAULT_FILE_PROMPT = "Пожалуйста, проанализируй этот файл."
