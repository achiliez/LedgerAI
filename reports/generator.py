"""
LedgerAI — Report Generator
Builds text summaries and Matplotlib charts (pie, bar) from report data.
"""

import logging
import os
import tempfile
import uuid

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for server use
import matplotlib.pyplot as plt

from models.schemas import DailyReport

logger = logging.getLogger(__name__)

# ── Styling ───────────────────────────────────────────────────
COLORS = [
    "#FF6B6B",  # Red
    "#4ECDC4",  # Teal
    "#45B7D1",  # Sky blue
    "#96CEB4",  # Sage
    "#FFEAA7",  # Yellow
    "#DDA0DD",  # Plum
    "#98D8C8",  # Mint
    "#F7DC6F",  # Gold
    "#BB8FCE",  # Lavender
    "#85C1E9",  # Light blue
    "#F0B27A",  # Peach
    "#82E0AA",  # Green
    "#F1948A",  # Salmon
]

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.size": 12,
        "figure.facecolor": "#1a1a2e",
        "axes.facecolor": "#16213e",
        "text.color": "#e0e0e0",
        "axes.labelcolor": "#e0e0e0",
    }
)


def generate_text_report(report: DailyReport, title: str = "📊 Report") -> str:
    """Generate a formatted text report string."""
    sym = report.currency_symbol
    lines = [f"*{title}*\n"]

    lines.append(f"💸 Total Spent: *{sym}{report.total_expense:,.2f}*")
    lines.append(f"💰 Total Received: *{sym}{report.total_income:,.2f}*")
    lines.append(f"📋 Transactions: {report.transaction_count}\n")

    if report.breakdown:
        lines.append("*Breakdown:*")
        for item in report.breakdown:
            lines.append(
                f"{item.emoji} {item.category}   "
                f"*{sym}{item.total:,.2f}*  ({item.percentage}%)"
            )
        lines.append("")

    # Net balance
    net = report.net
    if net >= 0:
        lines.append(f"💚 You're *{sym}{net:,.2f}* in the green!")
    else:
        lines.append(f"🔴 You're *{sym}{abs(net):,.2f}* in the red.")

    return "\n".join(lines)


def generate_chart(
    report: DailyReport,
    chart_type: str = "pie",
) -> str | None:
    """
    Generate a chart image and return the file path.
    Supported types: 'pie', 'bar'.
    Returns None if no data to chart.
    """
    if not report.breakdown:
        return None

    try:
        fig, ax = plt.subplots(figsize=(8, 6))

        labels = [f"{b.emoji} {b.category}" for b in report.breakdown]
        values = [float(b.total) for b in report.breakdown]
        colors = COLORS[: len(labels)]

        if chart_type == "pie":
            wedges, texts, autotexts = ax.pie(
                values,
                labels=labels,
                colors=colors,
                autopct="%1.1f%%",
                startangle=140,
                pctdistance=0.85,
                textprops={"fontsize": 11, "color": "#e0e0e0"},
            )
            for autotext in autotexts:
                autotext.set_fontsize(10)
                autotext.set_color("#ffffff")

            # Donut style
            centre_circle = plt.Circle((0, 0), 0.65, fc="#1a1a2e")
            ax.add_patch(centre_circle)
            ax.set_title(
                f"Expense Breakdown",
                fontsize=16,
                fontweight="bold",
                color="#e0e0e0",
                pad=20,
            )

        elif chart_type == "bar":
            bars = ax.barh(labels, values, color=colors, height=0.6, edgecolor="none")
            ax.set_xlabel(f"Amount ({report.currency_symbol})", fontsize=12)
            ax.set_title(
                "Spending by Category",
                fontsize=16,
                fontweight="bold",
                color="#e0e0e0",
                pad=20,
            )
            ax.tick_params(colors="#e0e0e0")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_color("#444")
            ax.spines["left"].set_color("#444")

            # Add value labels on bars
            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_width() + max(values) * 0.02,
                    bar.get_y() + bar.get_height() / 2,
                    f"{report.currency_symbol}{val:,.0f}",
                    va="center",
                    fontsize=10,
                    color="#e0e0e0",
                )

        plt.tight_layout()

        # Save to temp file
        path = os.path.join(
            tempfile.gettempdir(), f"ledgerai_chart_{uuid.uuid4().hex[:8]}.png"
        )
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        return path

    except Exception as e:
        logger.error(f"Chart generation failed: {e}")
        plt.close("all")
        return None
