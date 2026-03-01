"""
LedgerAI — LLM Transaction Parser
Uses GPT-4o to parse natural language messages into structured transaction data.
"""

import json
import logging
from datetime import date

from google import genai
from google.genai import types

from config import settings
from models.schemas import LLMResponse, TransactionCreate, TransactionType

logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.GEMINI_API_KEY)

# ── System Prompt ──────────────────────────────────────────────
SYSTEM_PROMPT = """You are a financial transaction parser for LedgerAI.
Your ONLY job is to extract structured data from natural language messages about money.

RULES:
1. If the message describes a financial transaction (spending, receiving, paying, earning, etc.), extract the data.
2. If the message is NOT about a financial transaction, return {"type": "not_transaction", "message": "<a helpful, friendly reply>"}.
3. Always respond with VALID JSON only — no markdown, no explanation.
4. Use today's date if no date is mentioned.
5. Infer the category from context.

CATEGORIES (use one of these exactly):
Expenses: Food & Drinks, Groceries, Transport, Entertainment, Shopping, Bills & Utilities, Health, Education, Rent, Subscriptions, Travel, Personal Care, Other Expense
Income: Salary, Freelance, Investment, Gift, Refund, Other Income

OUTPUT FORMAT for transactions:
{
    "type": "income" or "expense",
    "amount": <number>,
    "currency": "INR",
    "category": "<category from the list above>",
    "description": "<brief description>",
    "merchant": "<merchant/vendor name if mentioned, else null>",
    "date": "YYYY-MM-DD",
    "payment_method": "<cash/card/UPI/bank transfer if mentioned, else null>"
}

OUTPUT FORMAT for non-transactions:
{
    "type": "not_transaction",
    "message": "<friendly helpful response>"
}

EXAMPLES:
User: "Spent 500 on groceries"
→ {"type": "expense", "amount": 500, "currency": "INR", "category": "Groceries", "description": "Groceries", "merchant": null, "date": "TODAYS_DATE", "payment_method": null}

User: "Got 50000 salary"
→ {"type": "income", "amount": 50000, "currency": "INR", "category": "Salary", "description": "Monthly salary", "merchant": null, "date": "TODAYS_DATE", "payment_method": null}

User: "Paid 200 for Uber to office"
→ {"type": "expense", "amount": 200, "currency": "INR", "category": "Transport", "description": "Uber to office", "merchant": "Uber", "date": "TODAYS_DATE", "payment_method": null}

User: "hello"
→ {"type": "not_transaction", "message": "Hey! 👋 Send me your expenses or income and I'll track them for you. For example: 'Spent ₹500 on lunch' or 'Received ₹50,000 salary'"}
"""


async def parse_transaction(message: str, today: date | None = None) -> LLMResponse:
    """
    Send a user message to Gemini and parse the response into a validated schema.

    Args:
        message: The (PII-masked) user message.
        today: Override for today's date (useful for testing).

    Returns:
        LLMResponse containing either a validated TransactionCreate or a friendly message.
    """
    if today is None:
        today = date.today()

    # Inject today's date into the system prompt
    prompt = SYSTEM_PROMPT.replace("TODAYS_DATE", today.isoformat())

    try:
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=prompt,
                temperature=0.1,  # Low temperature for consistent parsing
                response_mime_type="application/json",
            )
        )

        raw = response.text
        if not raw:
            return LLMResponse(
                type=TransactionType.NOT_TRANSACTION,
                message="I couldn't understand that. Try something like 'Spent ₹500 on dinner'.",
            )

        data = json.loads(raw)
        tx_type = data.get("type", "not_transaction")

        if tx_type == "not_transaction":
            return LLMResponse(
                type=TransactionType.NOT_TRANSACTION,
                message=data.get("message", "Send me an expense or income to log!"),
            )

        # Validate through Pydantic
        transaction = TransactionCreate(**data)
        return LLMResponse(type=transaction.type, transaction=transaction)

    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}")
        return LLMResponse(
            type=TransactionType.NOT_TRANSACTION,
            message="I had trouble parsing that. Could you rephrase? Example: 'Spent ₹200 on coffee'.",
        )
    except Exception as e:
        logger.error(f"LLM parsing failed: {e}")
        return LLMResponse(
            type=TransactionType.NOT_TRANSACTION,
            message="Something went wrong. Please try again!",
        )
