"""Market data integration service."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from src.ui.formatters import normalize_symbol


class MarketDataService:
    """Fetches stock prices and historical series from Yahoo Finance."""

    def get_stock_metadata(self, symbol: str) -> dict[str, float | str]:
        """Fetches supplemental quote metadata for dashboard summary cards."""
        symbol = normalize_symbol(symbol)
        ticker = yf.Ticker(symbol)

        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            info = {}

        market_cap = float(info.get("marketCap") or 0.0)
        volume = float(info.get("volume") or info.get("averageVolume") or 0.0)
        pe_ratio = float(info.get("trailingPE") or info.get("forwardPE") or 0.0)
        shares = float(info.get("sharesOutstanding") or 0.0)
        company_name = str(info.get("longName") or info.get("shortName") or symbol.upper())

        return {
            "symbol": symbol.upper(),
            "company_name": company_name,
            "market_cap": market_cap,
            "volume": volume,
            "pe_ratio": pe_ratio,
            "shares_outstanding": shares,
        }

    def get_latest_price(self, symbol: str) -> float:
        symbol = normalize_symbol(symbol)
        ticker = yf.Ticker(symbol)

        try:
            info = ticker.fast_info
            if info and info.get("lastPrice"):
                return float(info["lastPrice"])
        except Exception:
            pass

        try:
            history = ticker.history(period="1d", interval="1m")
        except Exception:
            return 0.0
        if history.empty:
            return 0.0
        return float(history["Close"].iloc[-1])

    def get_quote_snapshot(self, symbol: str) -> dict[str, float | str]:
        symbol = normalize_symbol(symbol)
        history = self.get_history(symbol=symbol, period="5d", interval="1d")
        if history.empty:
            return {"symbol": symbol.upper(), "price": 0.0, "change": 0.0, "change_pct": 0.0}

        last_price = float(history["Close"].iloc[-1])
        previous_close = float(history["Close"].iloc[-2]) if len(history) > 1 else last_price
        change = last_price - previous_close
        change_pct = (change / previous_close * 100.0) if previous_close else 0.0

        return {
            "symbol": symbol.upper(),
            "price": round(last_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
        }

    def get_quote_map(self, symbols: list[str]) -> dict[str, dict[str, float | str]]:
        """Fetch snapshot map for many symbols."""
        snapshots: dict[str, dict[str, float | str]] = {}
        for symbol in dict.fromkeys(normalize_symbol(item) for item in symbols if item):
            snapshots[symbol] = self.get_quote_snapshot(symbol)
        return snapshots

    def get_history(self, symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        symbol = normalize_symbol(symbol)
        ticker = yf.Ticker(symbol)
        try:
            history = ticker.history(period=period, interval=interval)
        except Exception:
            return pd.DataFrame(columns=["Date", "Close"])

        if history.empty:
            return pd.DataFrame(columns=["Date", "Close"])

        normalized = history.reset_index()
        date_column = "Date" if "Date" in normalized.columns else normalized.columns[0]
        normalized = normalized[[date_column, "Close"]].rename(columns={date_column: "Date"})
        normalized["Date"] = pd.to_datetime(normalized["Date"])
        return normalized
