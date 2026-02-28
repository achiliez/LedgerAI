"""
LedgerAI — Pydantic Schemas
Validates LLM output before it reaches the database.
"""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    NOT_TRANSACTION = "not_transaction"


class TransactionCreate(BaseModel):
    """Schema for a parsed transaction from the LLM."""

    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="INR", max_length=10)
    category: str = Field(..., max_length=50)
    type: TransactionType
    description: Optional[str] = Field(default=None, max_length=200)
    merchant: Optional[str] = Field(default=None, max_length=100)
    date: date
    payment_method: Optional[str] = Field(default=None, max_length=50)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: str) -> str:
        return v.strip().title()

    @field_validator("description", "merchant")
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class LLMResponse(BaseModel):
    """Wrapper for the full LLM response — may or may not be a transaction."""

    type: TransactionType
    transaction: Optional[TransactionCreate] = None
    message: Optional[str] = None  # Friendly reply for non-transaction messages


class TransactionResponse(BaseModel):
    """Transaction as returned to the user / reports."""

    id: int
    amount: Decimal
    category: str
    category_emoji: str
    type: TransactionType
    description: Optional[str]
    merchant: Optional[str]
    date: date

    model_config = {"from_attributes": True}


class CategoryBreakdown(BaseModel):
    """Aggregated category data for reports."""

    category: str
    emoji: str
    total: Decimal
    percentage: float
    count: int


class DailyReport(BaseModel):
    """Aggregated report data."""

    date: date
    total_income: Decimal = Decimal("0")
    total_expense: Decimal = Decimal("0")
    net: Decimal = Decimal("0")
    transaction_count: int = 0
    breakdown: list[CategoryBreakdown] = []
    currency_symbol: str = "₹"
