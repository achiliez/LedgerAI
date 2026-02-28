"""
LedgerAI — Telegram Bot Handlers
Commands: /start, /today, /week, /month, /help
Default handler: natural language → transaction logging.
"""

import logging
from datetime import date, timedelta

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import settings
from models.schemas import TransactionType
from reports.generator import generate_chart, generate_text_report
from services.db_service import get_or_create_user, get_report_data, log_transaction
from services.llm_parser import parse_transaction
from services.privacy import mask_pii

logger = logging.getLogger(__name__)

CURRENCY = settings.CURRENCY_SYMBOL


# ── /start ────────────────────────────────────────────────────
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with usage instructions."""
    user = update.effective_user
    if not user or not update.message:
        return

    await get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    welcome = (
        f"👋 Hey {user.first_name or 'there'}! I'm **LedgerAI** — your personal finance tracker.\n\n"
        f"Just tell me about your expenses and income in natural language, and I'll log them for you.\n\n"
        f"**Examples:**\n"
        f"• _Spent {CURRENCY}500 on groceries_\n"
        f"• _Paid {CURRENCY}200 for Uber_\n"
        f"• _Received {CURRENCY}50,000 salary_\n"
        f"• _Had coffee for {CURRENCY}150 at Starbucks_\n\n"
        f"**Commands:**\n"
        f"/today — Today's summary\n"
        f"/week — Last 7 days\n"
        f"/month — This month\n"
        f"/help — Show this message\n\n"
        f"Let's start tracking! 💰"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


# ── /help ─────────────────────────────────────────────────────
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help text."""
    if not update.message:
        return

    help_text = (
        "📖 **LedgerAI Commands**\n\n"
        "/start — Welcome & setup\n"
        "/today — Today's spending summary + chart\n"
        "/week — Last 7 days summary + chart\n"
        "/month — This month's summary + chart\n"
        "/help — Show this help\n\n"
        "💡 **Tips:**\n"
        "• Just type naturally — I understand most formats\n"
        f"• Include amounts: _{CURRENCY}500, 500 rupees, 500 bucks_\n"
        "• Mention what it's for: _groceries, uber, dinner_\n"
        "• I auto-categorize everything!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ── /today ────────────────────────────────────────────────────
async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Today's spending summary with chart."""
    if not update.message or not update.effective_user:
        return

    user = await get_or_create_user(telegram_id=update.effective_user.id)
    today = date.today()
    report = await get_report_data(user.id, today, currency_symbol=CURRENCY)

    if report.transaction_count == 0:
        await update.message.reply_text(
            "📭 No transactions logged today yet.\n\n"
            f"Send me something like: _Spent {CURRENCY}300 on lunch_",
            parse_mode="Markdown",
        )
        return

    text = generate_text_report(report, title=f"📊 Today — {today.strftime('%b %d')}")
    await update.message.reply_text(text, parse_mode="Markdown")

    # Send pie chart if there are expenses
    if report.breakdown:
        chart_path = generate_chart(report, chart_type="pie")
        if chart_path:
            with open(chart_path, "rb") as f:
                await update.message.reply_photo(photo=f)
            import os
            os.remove(chart_path)


# ── /week ─────────────────────────────────────────────────────
async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Last 7 days summary with chart."""
    if not update.message or not update.effective_user:
        return

    user = await get_or_create_user(telegram_id=update.effective_user.id)
    end = date.today()
    start = end - timedelta(days=6)
    report = await get_report_data(user.id, start, end, currency_symbol=CURRENCY)

    if report.transaction_count == 0:
        await update.message.reply_text("📭 No transactions in the last 7 days.")
        return

    text = generate_text_report(
        report,
        title=f"📊 Weekly — {start.strftime('%b %d')} to {end.strftime('%b %d')}",
    )
    await update.message.reply_text(text, parse_mode="Markdown")

    if report.breakdown:
        chart_path = generate_chart(report, chart_type="bar")
        if chart_path:
            with open(chart_path, "rb") as f:
                await update.message.reply_photo(photo=f)
            import os
            os.remove(chart_path)


# ── /month ────────────────────────────────────────────────────
async def month_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Current month summary with chart."""
    if not update.message or not update.effective_user:
        return

    user = await get_or_create_user(telegram_id=update.effective_user.id)
    today = date.today()
    start = today.replace(day=1)
    report = await get_report_data(user.id, start, today, currency_symbol=CURRENCY)

    if report.transaction_count == 0:
        await update.message.reply_text(
            f"📭 No transactions this month ({today.strftime('%B')})."
        )
        return

    text = generate_text_report(
        report,
        title=f"📊 {today.strftime('%B %Y')}",
    )
    await update.message.reply_text(text, parse_mode="Markdown")

    if report.breakdown:
        chart_path = generate_chart(report, chart_type="pie")
        if chart_path:
            with open(chart_path, "rb") as f:
                await update.message.reply_photo(photo=f)
            import os
            os.remove(chart_path)


# ── Default Message Handler ──────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Process any text message:
    1. Mask PII  2. Parse with GPT-4o  3. Log to DB  4. Reply
    """
    if not update.message or not update.message.text or not update.effective_user:
        return

    user = await get_or_create_user(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
    )

    raw_text = update.message.text

    # 1. Mask PII before sending to LLM
    masked_text = mask_pii(raw_text)

    # 2. Parse with GPT-4o
    result = await parse_transaction(masked_text)

    # 3. Handle non-transaction messages
    if result.type == TransactionType.NOT_TRANSACTION:
        await update.message.reply_text(
            result.message or "Send me an expense or income to track!"
        )
        return

    if result.transaction is None:
        await update.message.reply_text("I couldn't parse that. Try again?")
        return

    # 4. Log to database
    tx_data = result.transaction
    tx = await log_transaction(user.id, tx_data)

    # 5. Build confirmation message
    emoji = "💸" if tx_data.type.value == "expense" else "💰"
    category_line = tx_data.category
    desc_line = f" — _{tx_data.description}_" if tx_data.description else ""
    merchant_line = f" at {tx_data.merchant}" if tx_data.merchant else ""

    confirmation = (
        f"✅ {emoji} Logged {CURRENCY}{tx_data.amount:,.2f}\n\n"
        f"📁 Category: **{category_line}**\n"
        f"📝 {tx_data.type.value.title()}{desc_line}{merchant_line}\n"
        f"📅 {tx_data.date.strftime('%b %d, %Y')}"
    )

    await update.message.reply_text(confirmation, parse_mode="Markdown")


# ── Register Handlers ────────────────────────────────────────
def register_handlers(app: Application):
    """Register all command and message handlers with the bot application."""
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("week", week_command))
    app.add_handler(CommandHandler("month", month_command))

    # Default handler — must be added last
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
