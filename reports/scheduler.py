"""
LedgerAI — Report Scheduler
Sends daily reports to all active users at the configured time.
"""

import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application

from config import settings
from reports.generator import generate_chart, generate_text_report
from services.db_service import get_all_active_user_ids, get_report_data

logger = logging.getLogger(__name__)


async def send_daily_reports(app: Application):
    """Fetch today's data for every active user and send them a report."""
    today = date.today()
    users = await get_all_active_user_ids()

    logger.info(f"📤 Sending daily reports to {len(users)} user(s)...")

    for user_id, telegram_id in users:
        try:
            report = await get_report_data(
                user_id, today, currency_symbol=settings.CURRENCY_SYMBOL
            )

            if report.transaction_count == 0:
                # Skip users with no transactions today
                continue

            text = generate_text_report(
                report,
                title=f"📊 Daily Report — {today.strftime('%b %d')}",
            )
            await app.bot.send_message(
                chat_id=telegram_id, text=text, parse_mode="Markdown"
            )

            # Send chart
            if report.breakdown:
                chart_path = generate_chart(report, chart_type="pie")
                if chart_path:
                    with open(chart_path, "rb") as f:
                        await app.bot.send_photo(chat_id=telegram_id, photo=f)
                    import os
                    os.remove(chart_path)

            logger.info(f"  ✅ Report sent to user {telegram_id}")

        except Exception as e:
            logger.error(f"  ❌ Failed to send report to {telegram_id}: {e}")

    logger.info("📤 Daily report run complete.")


def start_scheduler(app: Application) -> AsyncIOScheduler:
    """Start the APScheduler with a daily cron trigger."""
    scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)

    scheduler.add_job(
        send_daily_reports,
        trigger=CronTrigger(
            hour=settings.REPORT_HOUR,
            minute=settings.REPORT_MINUTE,
            timezone=settings.TIMEZONE,
        ),
        args=[app],
        id="daily_report",
        name="Daily Finance Report",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"⏰ Scheduler started — daily reports at "
        f"{settings.REPORT_HOUR:02d}:{settings.REPORT_MINUTE:02d} {settings.TIMEZONE}"
    )
    return scheduler
