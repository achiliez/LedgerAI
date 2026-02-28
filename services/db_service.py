"""
LedgerAI — Database Service
CRUD operations for users, transactions, and reports.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Account, Category, Transaction, User, async_session
from models.schemas import CategoryBreakdown, DailyReport, TransactionCreate

logger = logging.getLogger(__name__)


async def get_or_create_user(
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> User:
    """Get existing user or create a new one on first message."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            session.add(user)
            await session.flush()

            # Create default accounts
            for acct_name, is_default in [("Cash", True), ("Bank", False), ("Credit Card", False)]:
                session.add(
                    Account(user_id=user.id, name=acct_name, is_default=is_default)
                )

            await session.commit()
            await session.refresh(user)
            logger.info(f"New user created: {telegram_id} ({first_name})")
        else:
            # Update name/username if changed
            changed = False
            if username and user.username != username:
                user.username = username
                changed = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if changed:
                await session.commit()

        return user


async def get_category_by_name(name: str) -> Category | None:
    """Find a category by name (case-insensitive)."""
    async with async_session() as session:
        result = await session.execute(
            select(Category).where(func.lower(Category.name) == name.lower())
        )
        return result.scalar_one_or_none()


async def log_transaction(user_id: int, data: TransactionCreate) -> Transaction:
    """Insert a validated transaction into the database."""
    async with async_session() as session:
        # Resolve category
        category = None
        result = await session.execute(
            select(Category).where(func.lower(Category.name) == data.category.lower())
        )
        category = result.scalar_one_or_none()

        # Find the default account
        result = await session.execute(
            select(Account).where(
                Account.user_id == user_id,
                Account.is_default == True,  # noqa: E712
            )
        )
        default_account = result.scalar_one_or_none()

        tx = Transaction(
            user_id=user_id,
            account_id=default_account.id if default_account else None,
            category_id=category.id if category else None,
            amount=data.amount,
            type=data.type.value,
            description=data.description,
            merchant=data.merchant,
            date=data.date,
            payment_method=data.payment_method,
        )
        session.add(tx)

        # Update account balance
        if default_account:
            if data.type.value == "income":
                default_account.balance += data.amount
            else:
                default_account.balance -= data.amount

        await session.commit()
        await session.refresh(tx)
        logger.info(f"Transaction logged: {data.type.value} {data.amount} ({data.category})")
        return tx


async def get_transactions(
    user_id: int,
    start_date: date,
    end_date: date | None = None,
) -> list[dict]:
    """Fetch transactions for a user within a date range."""
    if end_date is None:
        end_date = start_date

    async with async_session() as session:
        result = await session.execute(
            select(Transaction, Category)
            .outerjoin(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.date >= start_date,
                Transaction.date <= end_date,
            )
            .order_by(Transaction.created_at.desc())
        )
        rows = result.all()

        return [
            {
                "id": tx.id,
                "amount": tx.amount,
                "type": tx.type,
                "category": cat.name if cat else "Uncategorized",
                "emoji": cat.emoji if cat else "📦",
                "description": tx.description,
                "merchant": tx.merchant,
                "date": tx.date,
                "payment_method": tx.payment_method,
            }
            for tx, cat in rows
        ]


async def get_report_data(
    user_id: int,
    start_date: date,
    end_date: date | None = None,
    currency_symbol: str = "₹",
) -> DailyReport:
    """Generate aggregated report data for a date range."""
    if end_date is None:
        end_date = start_date

    transactions = await get_transactions(user_id, start_date, end_date)

    total_income = Decimal("0")
    total_expense = Decimal("0")
    category_totals: dict[str, dict] = {}

    for tx in transactions:
        amount = Decimal(str(tx["amount"]))
        if tx["type"] == "income":
            total_income += amount
        else:
            total_expense += amount
            cat = tx["category"]
            if cat not in category_totals:
                category_totals[cat] = {
                    "emoji": tx["emoji"],
                    "total": Decimal("0"),
                    "count": 0,
                }
            category_totals[cat]["total"] += amount
            category_totals[cat]["count"] += 1

    # Build breakdown with percentages
    breakdown = []
    for cat_name, data in sorted(
        category_totals.items(), key=lambda x: x[1]["total"], reverse=True
    ):
        pct = (
            float(data["total"] / total_expense * 100)
            if total_expense > 0
            else 0.0
        )
        breakdown.append(
            CategoryBreakdown(
                category=cat_name,
                emoji=data["emoji"],
                total=data["total"],
                percentage=round(pct, 1),
                count=data["count"],
            )
        )

    return DailyReport(
        date=start_date,
        total_income=total_income,
        total_expense=total_expense,
        net=total_income - total_expense,
        transaction_count=len(transactions),
        breakdown=breakdown,
        currency_symbol=currency_symbol,
    )


async def get_all_active_user_ids() -> list[int]:
    """Return all active user IDs (for scheduled reports)."""
    async with async_session() as session:
        result = await session.execute(
            select(User.id, User.telegram_id).where(User.is_active == True)  # noqa: E712
        )
        return [(row[0], row[1]) for row in result.all()]
