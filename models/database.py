"""
LedgerAI — SQLAlchemy ORM Models
Normalized 3NF schema: Users, Accounts, Categories, Transactions.
All monetary values use NUMERIC(12,2) — never float.
"""

from datetime import datetime, date as date_type
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config import settings


# ── Engine & Session ──────────────────────────────────────────
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


# ── Base ──────────────────────────────────────────────────────
class Base(AsyncAttrs, DeclarativeBase):
    pass


# ── Users ─────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    base_currency: Mapped[str] = mapped_column(String(10), default="INR")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    accounts: Mapped[list["Account"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ── Accounts ──────────────────────────────────────────────────
class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(50))  # Cash, Savings, Credit Card
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")


# ── Categories ────────────────────────────────────────────────
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    emoji: Mapped[str] = mapped_column(String(10), default="📦")
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    is_income: Mapped[bool] = mapped_column(Boolean, default=False)

    # Self-referential relationship for hierarchy
    parent: Mapped["Category | None"] = relationship(
        "Category", remote_side="Category.id", backref="children"
    )
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="category")


# ── Transactions ──────────────────────────────────────────────
class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    type: Mapped[str] = mapped_column(String(10))  # "income" or "expense"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    merchant: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="transactions")
    account: Mapped["Account | None"] = relationship(back_populates="transactions")
    category: Mapped["Category | None"] = relationship(back_populates="transactions")


# ── Default Categories ───────────────────────────────────────
DEFAULT_CATEGORIES = [
    # Expense categories
    {"name": "Food & Drinks", "emoji": "🍔", "is_income": False},
    {"name": "Groceries", "emoji": "🛒", "is_income": False},
    {"name": "Transport", "emoji": "🚗", "is_income": False},
    {"name": "Entertainment", "emoji": "🎬", "is_income": False},
    {"name": "Shopping", "emoji": "🛍️", "is_income": False},
    {"name": "Bills & Utilities", "emoji": "💡", "is_income": False},
    {"name": "Health", "emoji": "🏥", "is_income": False},
    {"name": "Education", "emoji": "📚", "is_income": False},
    {"name": "Rent", "emoji": "🏠", "is_income": False},
    {"name": "Subscriptions", "emoji": "📱", "is_income": False},
    {"name": "Travel", "emoji": "✈️", "is_income": False},
    {"name": "Personal Care", "emoji": "💈", "is_income": False},
    {"name": "Other Expense", "emoji": "📦", "is_income": False},
    # Income categories
    {"name": "Salary", "emoji": "💰", "is_income": True},
    {"name": "Freelance", "emoji": "💻", "is_income": True},
    {"name": "Investment", "emoji": "📈", "is_income": True},
    {"name": "Gift", "emoji": "🎁", "is_income": True},
    {"name": "Refund", "emoji": "🔄", "is_income": True},
    {"name": "Other Income", "emoji": "💵", "is_income": True},
]


async def init_db():
    """Create all tables and seed default categories."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed categories
    async with async_session() as session:
        from sqlalchemy import select

        result = await session.execute(select(func.count(Category.id)))
        count = result.scalar()
        if count == 0:
            for cat_data in DEFAULT_CATEGORIES:
                session.add(Category(**cat_data))
            await session.commit()
