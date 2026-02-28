# 🤖 LedgerAI — Conversational Finance Tracker

A Telegram bot that understands natural-language expense/income messages, logs them to PostgreSQL, and sends daily chart-based reports.

**Example:**
```
You:  "Spent ₹500 on groceries"
Bot:  "✅ 💸 Logged ₹500.00
       📁 Category: Groceries
       📝 Expense — Groceries
       📅 Feb 28, 2026"
```

---

## 🏗️ Architecture

```
User (Telegram) → PII Masking (Presidio) → GPT-4o (parse) → Pydantic (validate) → PostgreSQL (store) → Reply
                                                                                                    ↓
                                                                          Scheduler (daily 9 PM) → Matplotlib chart → Telegram
```

| Layer | Technology |
|-------|-----------|
| Messaging | Telegram Bot API (`python-telegram-bot`) |
| NLP | GPT-4o (`openai` SDK) |
| Privacy | Microsoft Presidio |
| Validation | Pydantic v2 |
| Database | PostgreSQL 16 + SQLAlchemy (async) |
| Charts | Matplotlib |
| Scheduler | APScheduler |
| Hosting | Docker Compose |

---

## 🚀 Quick Start

### Prerequisites
- [Docker](https://www.docker.com/get-started/) installed
- Telegram account
- OpenAI API key

### Step 1 — Create Telegram Bot
1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the **API token** you receive

### Step 2 — Get OpenAI API Key
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create a new secret key
3. Copy it

### Step 3 — Configure Environment
```bash
cp .env.example .env
```

Edit `.env` and fill in:
```env
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
OPENAI_API_KEY=sk-your-openai-key
```

### Step 4 — Run!
```bash
docker-compose up --build
```

That's it! Open Telegram and start chatting with your bot. 🎉

---

## 📱 Bot Commands

| Command | What it does |
|---------|-----------|
| `/start` | Welcome message + usage guide |
| `/today` | Today's spending summary + pie chart |
| `/week` | Last 7 days summary + bar chart |
| `/month` | This month's summary + pie chart |
| `/help` | Show all commands |

Or just type naturally:
- *"Paid ₹200 for Uber to office"*
- *"Received ₹50,000 salary"*
- *"Had coffee for 150 at Starbucks"*

---

## 🗄️ Database Schema

4 normalized tables (3NF):

| Table | Purpose |
|-------|---------|
| `users` | Telegram IDs, currency preference, timezone |
| `accounts` | Cash, Savings, Credit Card buckets |
| `categories` | Hierarchical categories with emoji |
| `transactions` | Central fact table — amount (NUMERIC), type, date, etc. |

Auto-seeded with 19 default categories on first run.

---

## 📊 Daily Reports

Automated at 9:00 PM IST (configurable). Includes:
- Total income & expenses
- Category breakdown with percentages
- Dark-themed donut/bar charts sent as images
- Net balance indicator

---

## 🔧 Configuration

All settings via `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | **Required.** From @BotFather |
| `OPENAI_API_KEY` | — | **Required.** From OpenAI |
| `DATABASE_URL` | auto (Docker) | PostgreSQL connection string |
| `OPENAI_MODEL` | `gpt-4o` | Model for parsing |
| `REPORT_HOUR` | `21` | Daily report hour (24h) |
| `REPORT_MINUTE` | `0` | Daily report minute |
| `TIMEZONE` | `Asia/Kolkata` | IANA timezone |
| `CURRENCY_SYMBOL` | `₹` | Display currency |

---

## 🛠️ Development (without Docker)

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_lg

# 3. Start PostgreSQL locally (or use Docker for just the DB)
docker-compose up -d db

# 4. Set DATABASE_URL for local PostgreSQL
# In .env: DATABASE_URL=postgresql+asyncpg://ledgerai:ledgerai@localhost:5432/ledgerai

# 5. Run
python main.py
```

---

## 📁 Project Structure

```
LedgerAI/
├── main.py              # Entry point
├── config.py            # Settings (pydantic-settings)
├── models/
│   ├── database.py      # SQLAlchemy ORM (4 tables)
│   └── schemas.py       # Pydantic validation schemas
├── services/
│   ├── llm_parser.py    # GPT-4o transaction parsing
│   ├── privacy.py       # Presidio PII masking
│   └── db_service.py    # Database CRUD
├── bot/
│   └── handlers.py      # Telegram commands & message handler
├── reports/
│   ├── generator.py     # Text reports + Matplotlib charts
│   └── scheduler.py     # APScheduler daily cron
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 📄 License

MIT
