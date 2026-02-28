"""
LedgerAI — Main Entry Point
Initializes the database, registers bot handlers, starts the scheduler,
and runs the Telegram bot polling loop.
"""

import asyncio
import logging
import sys

from telegram.ext import Application

from bot.handlers import register_handlers
from config import settings
from models.database import init_db
from reports.scheduler import start_scheduler

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s │ %(name)-20s │ %(levelname)-7s │ %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("LedgerAI")


async def post_init(app: Application):
    """Called after the bot application is initialized."""
    logger.info("🗄️  Initializing database...")
    await init_db()
    logger.info("✅ Database ready — tables created & categories seeded")

    logger.info("⏰ Starting report scheduler...")
    start_scheduler(app)


def main():
    """Boot up LedgerAI."""
    logger.info("=" * 50)
    logger.info("  🤖 LedgerAI — Conversational Finance Tracker")
    logger.info("=" * 50)

    # Build the Telegram bot application
    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register command & message handlers
    register_handlers(app)

    logger.info("🚀 Bot is starting... (polling mode)")
    logger.info(f"💱 Currency: {settings.CURRENCY_SYMBOL}")
    logger.info(f"🧠 LLM Model: {settings.OPENAI_MODEL}")
    logger.info(
        f"📊 Daily report at: {settings.REPORT_HOUR:02d}:{settings.REPORT_MINUTE:02d} {settings.TIMEZONE}"
    )
    logger.info("Press Ctrl+C to stop.\n")

    # Start polling (blocks until Ctrl+C)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
