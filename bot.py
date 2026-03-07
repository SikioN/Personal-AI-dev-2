"""Telegram bot entry point for Personal-AI KG QA Navigator."""
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Check your .env file.")

    logger.info("Initializing QA engine (this may take a minute)...")
    from src.bot.engine_loader import load_engine
    try:
        load_engine()
        logger.info("QA engine ready.")
    except Exception as e:
        logger.warning(f"Engine pre-load failed (will retry on first request): {e}")

    from src.bot.handlers import router

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Bot started polling.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
