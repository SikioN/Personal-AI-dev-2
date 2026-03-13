"""Telegram bot entry point for Personal-AI KG QA Navigator."""
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
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

    # 5.5: validate token format before making any API calls
    import re as _re
    if not _re.match(r'^\d+:[A-Za-z0-9_-]{35,}$', token):
        raise RuntimeError("TELEGRAM_BOT_TOKEN format is invalid (expected '<digits>:<35+ alphanum chars>').")

    logger.info("Initializing QA engine (this may take a minute)...")
    from src.bot.engine_loader import load_engine
    try:
        # 1.3: heavy synchronous init (E5 encoding) must not block the event loop
        await asyncio.to_thread(load_engine)
        logger.info("QA engine ready.")
    except Exception as e:
        logger.warning(f"Engine pre-load failed (will retry on first request): {e}")

    from src.bot.handlers import router

    bot = Bot(token=token, default=DefaultBotProperties())
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Bot started polling.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
