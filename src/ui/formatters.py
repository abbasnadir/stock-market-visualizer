"""Shared formatting helpers for UI output."""

from __future__ import annotations

from typing import Any


def normalize_symbol(value: Any, default: str = "") -> str:
    """Normalize free-form ticker input into a display-safe symbol."""
    return str(value or default).upper().strip()


def format_currency(
    value: float | int | None,
    fallback: str = "Unavailable",
    allow_zero: bool = False,
) -> str:
    """Format numeric value as USD currency."""
    if value is None:
        return fallback
    numeric = float(value)
    if numeric == 0 and not allow_zero:
        return fallback
    sign = "-" if numeric < 0 else ""
    return f"{sign}${abs(numeric):,.2f}"


def format_plain_number(value: float | int | None, digits: int = 2, fallback: str = "Unavailable") -> str:
    """Format a plain numeric value."""
    if value is None:
        return fallback
    numeric = float(value)
    if numeric <= 0:
        return fallback
    return f"{numeric:,.{digits}f}"


def format_compact_number(value: float | int | None, prefix: str = "", fallback: str = "Unavailable") -> str:
    """Format large number using compact suffixes."""
    if value is None:
        return fallback
    numeric = float(value)
    if numeric <= 0:
        return fallback

    suffixes = (
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    )
    for threshold, suffix in suffixes:
        if numeric >= threshold:
            return f"{prefix}{numeric / threshold:.2f}{suffix}"
    return f"{prefix}{numeric:,.0f}"


def format_percent(value: float | int | None, signed: bool = True, fallback: str = "Unavailable") -> str:
    """Format percentage values."""
    if value is None:
        return fallback
    numeric = float(value)
    sign = "+" if signed and numeric > 0 else ""
    return f"{sign}{numeric:.2f}%"


def get_change_tone(value: float | int | None) -> tuple[str, str]:
    """Return CSS tone tokens for change values."""
    numeric = float(value or 0.0)
    if numeric > 0:
        return "positive", "trend-badge up"
    if numeric < 0:
        return "negative", "trend-badge down"
    return "neutral", "trend-badge neutral"
