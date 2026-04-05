"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AppSettings:
    """Runtime configuration for the application."""

    supabase_url: str
    supabase_anon_key: str
    app_title: str
    default_cash_balance: float
    default_symbol: str
    host: str
    port: int
    debug: bool

    @classmethod
    def from_env(cls) -> "AppSettings":
        """Build settings object from .env values."""
        return cls(
            supabase_url=os.getenv("SUPABASE_URL", "").strip(),
            supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", "").strip(),
            app_title=os.getenv("APP_TITLE", "Stock Market Dash App"),
            default_cash_balance=float(os.getenv("DEFAULT_CASH_BALANCE", "100000")),
            default_symbol=os.getenv("DEFAULT_SYMBOL", "AAPL"),
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "8050")),
            debug=os.getenv("DEBUG", "true").lower() == "true",
        )

    @property
    def has_supabase_credentials(self) -> bool:
        """Whether Supabase can be initialized from environment variables."""
        return bool(self.supabase_url and self.supabase_anon_key)
