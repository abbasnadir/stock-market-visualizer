"""Market data integration service."""

from __future__ import annotations

import pandas as pd
import yfinance as yf


class MarketDataService:
    """Fetches stock prices and historical series from Yahoo Finance."""

    def get_latest_price(self, symbol: str) -> float:
        ticker = yf.Ticker(symbol)

        try:
            info = ticker.fast_info
            if info and info.get("lastPrice"):
                return float(info["lastPrice"])
        except Exception:
            pass

        history = ticker.history(period="1d", interval="1m")
        if history.empty:
            return 0.0
        return float(history["Close"].iloc[-1])

    def get_quote_snapshot(self, symbol: str) -> dict[str, float | str]:
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

    def get_history(self, symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period, interval=interval)

        if history.empty:
            return pd.DataFrame(columns=["Date", "Close"])

        normalized = history.reset_index()
        date_column = "Date" if "Date" in normalized.columns else normalized.columns[0]
        normalized = normalized[[date_column, "Close"]].rename(columns={date_column: "Date"})
        normalized["Date"] = pd.to_datetime(normalized["Date"])
        return normalized
