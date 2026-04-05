"""Portfolio data access layer with Supabase and in-memory fallback."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from src.core.result import OperationResult
from src.services.supabase_service import SupabaseService


class PortfolioRepository:
    """Manages user balances, positions, watchlists, and alerts."""

    def __init__(self, supabase_service: SupabaseService, default_cash_balance: float) -> None:
        self.supabase_service = supabase_service
        self.default_cash_balance = float(default_cash_balance)

        self._memory_profiles: dict[str, dict[str, Any]] = {}
        self._memory_positions: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
        self._memory_transactions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._memory_watchlist: dict[str, set[str]] = defaultdict(set)
        self._memory_alerts: dict[str, list[dict[str, Any]]] = defaultdict(list)

    @property
    def _client(self):
        return self.supabase_service.client

    def _utc_now(self) -> str:
        return datetime.now(tz=timezone.utc).isoformat()

    def _ensure_memory_profile(self, user_id: str, email: str = "") -> dict[str, Any]:
        if user_id not in self._memory_profiles:
            self._memory_profiles[user_id] = {
                "id": user_id,
                "email": email,
                "balance": self.default_cash_balance,
                "created_at": self._utc_now(),
            }
        return self._memory_profiles[user_id]

    def ensure_user_profile(self, user_id: str, email: str = "") -> OperationResult:
        if self._client:
            try:
                payload = {
                    "id": user_id,
                    "email": email,
                    "balance": self.default_cash_balance,
                }
                self._client.table("profiles").upsert(payload, on_conflict="id").execute()
                return OperationResult(True, "Profile synced with Supabase.", payload)
            except Exception:
                pass

        profile = self._ensure_memory_profile(user_id, email)
        return OperationResult(
            True,
            "Profile stored in local fallback because Supabase tables are not ready.",
            profile,
        )

    def get_balance(self, user_id: str) -> float:
        if self._client:
            try:
                response = (
                    self._client.table("profiles")
                    .select("balance")
                    .eq("id", user_id)
                    .single()
                    .execute()
                )
                return float(response.data["balance"])
            except Exception:
                pass

        profile = self._ensure_memory_profile(user_id)
        return float(profile["balance"])

    def _set_balance(self, user_id: str, new_balance: float) -> None:
        if self._client:
            try:
                self._client.table("profiles").update({"balance": new_balance}).eq("id", user_id).execute()
                return
            except Exception:
                pass

        profile = self._ensure_memory_profile(user_id)
        profile["balance"] = float(new_balance)

    def get_positions(self, user_id: str) -> list[dict[str, Any]]:
        if self._client:
            try:
                response = (
                    self._client.table("portfolios")
                    .select("symbol,quantity,avg_cost")
                    .eq("user_id", user_id)
                    .execute()
                )
                return response.data or []
            except Exception:
                pass

        positions = self._memory_positions[user_id]
        return [
            {
                "symbol": symbol,
                "quantity": values["quantity"],
                "avg_cost": values["avg_cost"],
            }
            for symbol, values in positions.items()
            if values["quantity"] > 0
        ]

    def _upsert_position(self, user_id: str, symbol: str, quantity: float, avg_cost: float) -> None:
        if self._client:
            try:
                payload = {
                    "user_id": user_id,
                    "symbol": symbol,
                    "quantity": quantity,
                    "avg_cost": avg_cost,
                }
                self._client.table("portfolios").upsert(payload, on_conflict="user_id,symbol").execute()
                return
            except Exception:
                pass

        self._memory_positions[user_id][symbol] = {
            "quantity": quantity,
            "avg_cost": avg_cost,
        }

    def _insert_transaction(self, user_id: str, action: str, symbol: str, quantity: float, price: float) -> None:
        payload = {
            "user_id": user_id,
            "action": action,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "timestamp": self._utc_now(),
        }

        if self._client:
            try:
                self._client.table("transactions").insert(payload).execute()
                return
            except Exception:
                pass

        self._memory_transactions[user_id].append(payload)

    def buy_stock(self, user_id: str, symbol: str, quantity: float, price: float) -> OperationResult:
        if quantity <= 0:
            return OperationResult(False, "Quantity must be greater than 0.")

        symbol = symbol.upper().strip()
        balance = self.get_balance(user_id)
        total_cost = quantity * price

        if total_cost > balance:
            return OperationResult(False, "Insufficient balance for this buy order.")

        positions = {p["symbol"]: p for p in self.get_positions(user_id)}
        current = positions.get(symbol, {"quantity": 0.0, "avg_cost": 0.0})

        new_quantity = float(current["quantity"]) + quantity
        new_avg_cost = (
            (float(current["quantity"]) * float(current["avg_cost"]) + total_cost) / new_quantity
            if new_quantity
            else 0.0
        )

        self._upsert_position(user_id, symbol, new_quantity, new_avg_cost)
        self._set_balance(user_id, balance - total_cost)
        self._insert_transaction(user_id, "BUY", symbol, quantity, price)

        return OperationResult(
            True,
            f"Bought {quantity} share(s) of {symbol} at ${price:.2f}.",
            {"new_balance": round(balance - total_cost, 2)},
        )

    def sell_stock(self, user_id: str, symbol: str, quantity: float, price: float) -> OperationResult:
        if quantity <= 0:
            return OperationResult(False, "Quantity must be greater than 0.")

        symbol = symbol.upper().strip()
        positions = {p["symbol"]: p for p in self.get_positions(user_id)}
        current = positions.get(symbol)

        if not current or float(current["quantity"]) < quantity:
            return OperationResult(False, "Not enough shares to sell.")

        remaining = float(current["quantity"]) - quantity
        avg_cost = float(current["avg_cost"])

        if remaining > 0:
            self._upsert_position(user_id, symbol, remaining, avg_cost)
        else:
            self._upsert_position(user_id, symbol, 0.0, avg_cost)

        sale_total = quantity * price
        balance = self.get_balance(user_id)
        self._set_balance(user_id, balance + sale_total)
        self._insert_transaction(user_id, "SELL", symbol, quantity, price)

        return OperationResult(
            True,
            f"Sold {quantity} share(s) of {symbol} at ${price:.2f}.",
            {"new_balance": round(balance + sale_total, 2)},
        )

    def get_watchlist(self, user_id: str) -> list[str]:
        if self._client:
            try:
                response = (
                    self._client.table("watchlists")
                    .select("symbol")
                    .eq("user_id", user_id)
                    .order("symbol")
                    .execute()
                )
                return [row["symbol"] for row in (response.data or [])]
            except Exception:
                pass

        return sorted(self._memory_watchlist[user_id])

    def add_to_watchlist(self, user_id: str, symbol: str) -> OperationResult:
        symbol = symbol.upper().strip()
        if not symbol:
            return OperationResult(False, "Please provide a valid symbol.")

        if self._client:
            try:
                payload = {"user_id": user_id, "symbol": symbol}
                self._client.table("watchlists").upsert(payload, on_conflict="user_id,symbol").execute()
                return OperationResult(True, f"Added {symbol} to watchlist.")
            except Exception:
                pass

        self._memory_watchlist[user_id].add(symbol)
        return OperationResult(True, f"Added {symbol} to watchlist (local fallback).")

    def remove_from_watchlist(self, user_id: str, symbol: str) -> OperationResult:
        symbol = symbol.upper().strip()

        if self._client:
            try:
                (
                    self._client.table("watchlists")
                    .delete()
                    .eq("user_id", user_id)
                    .eq("symbol", symbol)
                    .execute()
                )
                return OperationResult(True, f"Removed {symbol} from watchlist.")
            except Exception:
                pass

        self._memory_watchlist[user_id].discard(symbol)
        return OperationResult(True, f"Removed {symbol} from watchlist (local fallback).")

    def add_alert(
        self,
        user_id: str,
        symbol: str,
        target_price: float,
        condition: str,
    ) -> OperationResult:
        symbol = symbol.upper().strip()
        condition = condition.lower().strip()

        if condition not in {"above", "below"}:
            return OperationResult(False, "Condition must be either 'above' or 'below'.")

        payload = {
            "user_id": user_id,
            "symbol": symbol,
            "target_price": float(target_price),
            "condition": condition,
            "active": True,
            "created_at": self._utc_now(),
        }

        if self._client:
            try:
                self._client.table("alerts").insert(payload).execute()
                return OperationResult(True, f"Alert created for {symbol}.")
            except Exception:
                pass

        self._memory_alerts[user_id].append(payload)
        return OperationResult(True, f"Alert created for {symbol} (local fallback).")

    def get_alerts(self, user_id: str) -> list[dict[str, Any]]:
        if self._client:
            try:
                response = (
                    self._client.table("alerts")
                    .select("symbol,target_price,condition,active,created_at")
                    .eq("user_id", user_id)
                    .eq("active", True)
                    .order("created_at", desc=True)
                    .execute()
                )
                return response.data or []
            except Exception:
                pass

        return [alert for alert in self._memory_alerts[user_id] if alert.get("active", True)]

    def check_alerts(self, user_id: str, market_prices: dict[str, float]) -> list[str]:
        alerts = self.get_alerts(user_id)
        triggered: list[str] = []

        for alert in alerts:
            symbol = alert["symbol"].upper()
            condition = alert["condition"].lower()
            target = float(alert["target_price"])
            current_price = float(market_prices.get(symbol, 0.0))

            if condition == "above" and current_price >= target:
                triggered.append(
                    f"{symbol} is above ${target:.2f} at ${current_price:.2f}."
                )
            elif condition == "below" and current_price <= target:
                triggered.append(
                    f"{symbol} is below ${target:.2f} at ${current_price:.2f}."
                )

        return triggered
