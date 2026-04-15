"""Portfolio data access layer backed strictly by Supabase."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.result import OperationResult
from src.services.supabase_service import SupabaseService


class PortfolioRepository:
    """Manages user balances, positions, watchlists, and alerts."""

    def __init__(self, supabase_service: SupabaseService, default_cash_balance: float) -> None:
        self.supabase_service = supabase_service
        self.default_cash_balance = float(default_cash_balance)

    @property
    def _client(self):
        return self.supabase_service.client

    def _require_client(self):
        client = self._client
        if not client:
            raise RuntimeError(
                "Supabase is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY to .env and restart the app."
            )
        return client

    def _utc_now(self) -> str:
        return datetime.now(tz=timezone.utc).isoformat()

    @staticmethod
    def _friendly_db_error(exc: Exception, table: str, operation: str) -> str:
        raw = str(exc)
        normalized = raw.lower()
        if "row-level security policy" in normalized or "42501" in normalized:
            return (
                f"RLS blocked {operation} on '{table}'. "
                "Apply the policies in dbdesign.md / supabase_setup.sql, then retry."
            )
        return raw

    def ensure_user_profile(self, user_id: str, email: str = "") -> OperationResult:
        try:
            client = self._require_client()
            payload = {
                "id": user_id,
                "email": email,
                "balance": self.default_cash_balance,
            }
            client.table("profiles").upsert(payload, on_conflict="id").execute()
            return OperationResult(True, "Profile synced with Supabase.", payload)
        except Exception as exc:
            error_text = self._friendly_db_error(exc, "profiles", "profile sync")
            return OperationResult(False, f"Failed to sync profile in Supabase: {error_text}")

    def get_balance(self, user_id: str) -> float:
        try:
            client = self._require_client()
            response = (
                client.table("profiles")
                .select("balance")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )
            rows = response.data or []

            if not rows:
                ensure_result = self.ensure_user_profile(user_id)
                if not ensure_result.success:
                    raise RuntimeError(ensure_result.message)

                response = (
                    client.table("profiles")
                    .select("balance")
                    .eq("id", user_id)
                    .limit(1)
                    .execute()
                )
                rows = response.data or []

            if not rows:
                raise RuntimeError("Profile row is missing in Supabase.")

            return float(rows[0].get("balance", self.default_cash_balance))
        except RuntimeError:
            raise
        except Exception as exc:
            error_text = self._friendly_db_error(exc, "profiles", "balance read")
            raise RuntimeError(f"Could not fetch live balance from Supabase: {error_text}") from exc

    def _set_balance(self, user_id: str, new_balance: float) -> OperationResult:
        try:
            client = self._require_client()
            client.table("profiles").update({"balance": new_balance}).eq("id", user_id).execute()
            return OperationResult(True, "Balance updated.")
        except Exception as exc:
            return OperationResult(False, f"Failed to update balance in Supabase: {exc}")

    def get_positions(self, user_id: str) -> list[dict[str, Any]]:
        try:
            client = self._require_client()
            response = (
                client.table("portfolios")
                .select("symbol,quantity,avg_cost")
                .eq("user_id", user_id)
                .execute()
            )
            rows = response.data or []

            return [
                {
                    "symbol": str(row.get("symbol", "")).upper(),
                    "quantity": float(row.get("quantity") or 0.0),
                    "avg_cost": float(row.get("avg_cost") or 0.0),
                }
                for row in rows
                if row.get("symbol") and float(row.get("quantity") or 0.0) > 0
            ]
        except RuntimeError:
            raise
        except Exception as exc:
            error_text = self._friendly_db_error(exc, "portfolios", "positions read")
            raise RuntimeError(f"Could not fetch live positions from Supabase: {error_text}") from exc

    def _upsert_position(self, user_id: str, symbol: str, quantity: float, avg_cost: float) -> OperationResult:
        try:
            client = self._require_client()
            payload = {
                "user_id": user_id,
                "symbol": symbol,
                "quantity": quantity,
                "avg_cost": avg_cost,
            }
            client.table("portfolios").upsert(payload, on_conflict="user_id,symbol").execute()
            return OperationResult(True, "Position updated.")
        except Exception as exc:
            return OperationResult(False, f"Failed to update position in Supabase: {exc}")

    def _delete_position(self, user_id: str, symbol: str) -> OperationResult:
        try:
            client = self._require_client()
            client.table("portfolios").delete().eq("user_id", user_id).eq("symbol", symbol).execute()
            return OperationResult(True, "Position removed.")
        except Exception as exc:
            return OperationResult(False, f"Failed to remove position in Supabase: {exc}")

    def _insert_transaction(self, user_id: str, action: str, symbol: str, quantity: float, price: float) -> OperationResult:
        payload = {
            "user_id": user_id,
            "action": action,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "timestamp": self._utc_now(),
        }
        try:
            client = self._require_client()
            client.table("transactions").insert(payload).execute()
            return OperationResult(True, "Transaction inserted.")
        except Exception as exc:
            return OperationResult(False, f"Failed to record transaction in Supabase: {exc}")

    def get_transactions(self, user_id: str, limit: int = 8) -> list[dict[str, Any]]:
        try:
            client = self._require_client()
            response = (
                client.table("transactions")
                .select("action,symbol,quantity,price,timestamp")
                .eq("user_id", user_id)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except RuntimeError:
            raise
        except Exception as exc:
            error_text = self._friendly_db_error(exc, "transactions", "transactions read")
            raise RuntimeError(f"Could not fetch live transactions from Supabase: {error_text}") from exc

    def buy_stock(self, user_id: str, symbol: str, quantity: float, price: float) -> OperationResult:
        if quantity <= 0:
            return OperationResult(False, "Quantity must be greater than 0.")

        symbol = symbol.upper().strip()
        try:
            balance = self.get_balance(user_id)
            positions = {p["symbol"]: p for p in self.get_positions(user_id)}
        except RuntimeError as exc:
            return OperationResult(False, str(exc))

        total_cost = quantity * price

        if total_cost > balance:
            return OperationResult(False, "Insufficient balance for this buy order.")

        current = positions.get(symbol, {"quantity": 0.0, "avg_cost": 0.0})

        new_quantity = float(current["quantity"]) + quantity
        new_avg_cost = (
            (float(current["quantity"]) * float(current["avg_cost"]) + total_cost) / new_quantity
            if new_quantity
            else 0.0
        )

        upsert_result = self._upsert_position(user_id, symbol, new_quantity, new_avg_cost)
        if not upsert_result.success:
            return upsert_result

        set_balance_result = self._set_balance(user_id, balance - total_cost)
        if not set_balance_result.success:
            return set_balance_result

        transaction_result = self._insert_transaction(user_id, "BUY", symbol, quantity, price)
        if not transaction_result.success:
            return transaction_result

        return OperationResult(
            True,
            f"Bought {quantity} share(s) of {symbol} at ${price:.2f}.",
            {"new_balance": round(balance - total_cost, 2)},
        )

    def sell_stock(self, user_id: str, symbol: str, quantity: float, price: float) -> OperationResult:
        if quantity <= 0:
            return OperationResult(False, "Quantity must be greater than 0.")

        symbol = symbol.upper().strip()
        try:
            positions = {p["symbol"]: p for p in self.get_positions(user_id)}
            balance = self.get_balance(user_id)
        except RuntimeError as exc:
            return OperationResult(False, str(exc))

        current = positions.get(symbol)

        if not current or float(current["quantity"]) < quantity:
            return OperationResult(False, "Not enough shares to sell.")

        remaining = float(current["quantity"]) - quantity
        avg_cost = float(current["avg_cost"])

        if remaining > 0:
            position_result = self._upsert_position(user_id, symbol, remaining, avg_cost)
        else:
            position_result = self._delete_position(user_id, symbol)
        if not position_result.success:
            return position_result

        sale_total = quantity * price
        set_balance_result = self._set_balance(user_id, balance + sale_total)
        if not set_balance_result.success:
            return set_balance_result

        transaction_result = self._insert_transaction(user_id, "SELL", symbol, quantity, price)
        if not transaction_result.success:
            return transaction_result

        return OperationResult(
            True,
            f"Sold {quantity} share(s) of {symbol} at ${price:.2f}.",
            {"new_balance": round(balance + sale_total, 2)},
        )

    def get_watchlist(self, user_id: str) -> list[str]:
        try:
            client = self._require_client()
            response = (
                client.table("watchlists")
                .select("symbol")
                .eq("user_id", user_id)
                .order("symbol")
                .execute()
            )
            return [str(row["symbol"]).upper() for row in (response.data or []) if row.get("symbol")]
        except RuntimeError:
            raise
        except Exception as exc:
            error_text = self._friendly_db_error(exc, "watchlists", "watchlist read")
            raise RuntimeError(f"Could not fetch live watchlist from Supabase: {error_text}") from exc

    def add_to_watchlist(self, user_id: str, symbol: str) -> OperationResult:
        symbol = symbol.upper().strip()
        if not symbol:
            return OperationResult(False, "Please provide a valid symbol.")

        try:
            client = self._require_client()
            payload = {"user_id": user_id, "symbol": symbol}
            client.table("watchlists").upsert(payload, on_conflict="user_id,symbol").execute()
            return OperationResult(True, f"Added {symbol} to watchlist.")
        except Exception as exc:
            return OperationResult(False, f"Failed to add {symbol} to watchlist in Supabase: {exc}")

    def remove_from_watchlist(self, user_id: str, symbol: str) -> OperationResult:
        symbol = symbol.upper().strip()
        if not symbol:
            return OperationResult(False, "Please provide a valid symbol.")

        try:
            client = self._require_client()
            (
                client.table("watchlists")
                .delete()
                .eq("user_id", user_id)
                .eq("symbol", symbol)
                .execute()
            )
            return OperationResult(True, f"Removed {symbol} from watchlist.")
        except Exception as exc:
            return OperationResult(False, f"Failed to remove {symbol} from watchlist in Supabase: {exc}")

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

        try:
            client = self._require_client()
            client.table("alerts").insert(payload).execute()
            return OperationResult(True, f"Alert created for {symbol}.")
        except Exception as exc:
            return OperationResult(False, f"Failed to create alert in Supabase: {exc}")

    def get_alerts(self, user_id: str) -> list[dict[str, Any]]:
        try:
            client = self._require_client()
            response = (
                client.table("alerts")
                .select("id,symbol,target_price,condition,active,created_at")
                .eq("user_id", user_id)
                .eq("active", True)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data or []
        except RuntimeError:
            raise
        except Exception as exc:
            error_text = self._friendly_db_error(exc, "alerts", "alerts read")
            raise RuntimeError(f"Could not fetch live alerts from Supabase: {error_text}") from exc

    def remove_alert(self, user_id: str, alert_id: int) -> OperationResult:
        try:
            client = self._require_client()
            client.table("alerts").delete().eq("user_id", user_id).eq("id", alert_id).execute()
            return OperationResult(True, "Alert removed.")
        except Exception as exc:
            return OperationResult(False, f"Failed to remove alert from Supabase: {exc}")

    def check_alerts(self, user_id: str, market_prices: dict[str, float]) -> list[str]:
        alerts = self.get_alerts(user_id)
        triggered: list[str] = []

        for alert in alerts:
            symbol = alert["symbol"].upper()
            condition = alert["condition"].lower()
            target = float(alert["target_price"])
            current_price_raw = market_prices.get(symbol)
            if current_price_raw is None:
                continue

            current_price = float(current_price_raw)
            if current_price <= 0:
                continue

            if condition == "above" and current_price >= target:
                triggered.append(
                    f"{symbol} is above ${target:.2f} at ${current_price:.2f}."
                )
            elif condition == "below" and current_price <= target:
                triggered.append(
                    f"{symbol} is below ${target:.2f} at ${current_price:.2f}."
                )

        return triggered
