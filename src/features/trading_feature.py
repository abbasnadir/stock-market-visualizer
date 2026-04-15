"""Trading feature for buy and sell actions with balance updates."""

from __future__ import annotations

from typing import Any

from dash import Dash, Input, Output, State, ctx, dash_table, dcc, html

from src.features.base_feature import BaseFeature
from src.ui.formatters import format_currency, normalize_symbol


class TradingFeature(BaseFeature):
    """Supports buy and sell operations with live quote previews."""

    def get_layout(self):
        return html.Section(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.P("Order Ticket", className="panel-title"),
                                html.P(
                                    "Research symbol once, place order here, portfolio updates everywhere.",
                                    className="panel-subtitle",
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.P("Ticker", className="input-label"),
                                                dcc.Input(
                                                    id="trade-symbol-input",
                                                    type="text",
                                                    placeholder="Ticker",
                                                    value=self.services.settings.default_symbol,
                                                    className="app-input",
                                                ),
                                            ],
                                            className="field-stack grow",
                                        ),
                                        html.Div(
                                            [
                                                html.P("Quantity", className="input-label"),
                                                dcc.Input(
                                                    id="trade-quantity-input",
                                                    type="number",
                                                    placeholder="Quantity",
                                                    min=1,
                                                    step=1,
                                                    value=1,
                                                    className="app-input",
                                                ),
                                            ],
                                            className="field-stack compact",
                                        ),
                                    ],
                                    className="form-grid two-up",
                                ),
                                html.Div(
                                    [
                                        html.Button("Buy", id="trade-buy-btn", n_clicks=0, className="primary-btn"),
                                        html.Button("Sell", id="trade-sell-btn", n_clicks=0, className="secondary-btn"),
                                        html.Button(
                                            "Refresh Portfolio",
                                            id="trade-refresh-btn",
                                            n_clicks=0,
                                            className="ghost-btn",
                                        ),
                                    ],
                                    className="button-row wrap",
                                ),
                                html.P(id="trade-message", className="inline-feedback"),
                            ],
                            className="app-panel",
                        ),
                        html.Div(
                            [
                                html.P("Execution Snapshot", className="panel-title"),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Span("Cash balance", className="metric-label"),
                                                html.Strong("Balance: N/A", id="trade-balance-output", className="metric-value"),
                                            ],
                                            className="metric-tile",
                                        ),
                                        html.Div(
                                            [
                                                html.Span("Live price", className="metric-label"),
                                                html.Strong("Unavailable", id="trade-price-output", className="metric-value"),
                                            ],
                                            className="metric-tile",
                                        ),
                                        html.Div(
                                            [
                                                html.Span("Estimated notional", className="metric-label"),
                                                html.Strong("Unavailable", id="trade-order-total", className="metric-value"),
                                            ],
                                            className="metric-tile",
                                        ),
                                    ],
                                    className="metric-grid compact-grid",
                                ),
                            ],
                            className="app-panel muted-panel",
                        ),
                    ],
                    className="content-grid two-column-grid",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.P("Current Holdings", className="panel-title"),
                                html.P("Live valuation, cost basis, and unrealized move.", className="panel-subtitle"),
                                dash_table.DataTable(
                                    id="trade-holdings-table",
                                    columns=[
                                        {"name": "Symbol", "id": "symbol"},
                                        {"name": "Quantity", "id": "quantity"},
                                        {"name": "Avg Cost", "id": "avg_cost"},
                                        {"name": "Current Price", "id": "current_price"},
                                        {"name": "Market Value", "id": "market_value"},
                                        {"name": "Unrealized P/L", "id": "unrealized_pl"},
                                    ],
                                    data=[],
                                    page_size=8,
                                    style_table={"overflowX": "auto"},
                                ),
                            ],
                            className="app-panel table-panel",
                        ),
                        html.Div(
                            [
                                html.P("Recent Activity", className="panel-title"),
                                html.P("Latest buy and sell executions from transaction ledger.", className="panel-subtitle"),
                                dash_table.DataTable(
                                    id="trade-activity-table",
                                    columns=[
                                        {"name": "Time", "id": "timestamp"},
                                        {"name": "Action", "id": "action"},
                                        {"name": "Symbol", "id": "symbol"},
                                        {"name": "Quantity", "id": "quantity"},
                                        {"name": "Price", "id": "price"},
                                        {"name": "Notional", "id": "notional"},
                                    ],
                                    data=[],
                                    page_size=8,
                                    style_table={"overflowX": "auto"},
                                ),
                            ],
                            className="app-panel table-panel",
                        ),
                    ],
                    className="stack-grid",
                ),
            ]
        )

    def _build_holdings_rows(self, user_id: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        positions = self.services.portfolio_repository.get_positions(user_id)
        snapshots = self.services.market_data_service.get_quote_map([position["symbol"] for position in positions])

        for position in positions:
            symbol = position["symbol"]
            quantity = float(position["quantity"])
            avg_cost = float(position["avg_cost"])
            current_price = float(snapshots.get(symbol, {}).get("price") or 0.0)
            market_value = quantity * current_price
            unrealized = market_value - (quantity * avg_cost)

            rows.append(
                {
                    "symbol": symbol,
                    "quantity": round(quantity, 4),
                    "avg_cost": format_currency(avg_cost),
                    "current_price": format_currency(current_price),
                    "market_value": format_currency(market_value, allow_zero=True),
                    "unrealized_pl": format_currency(unrealized, fallback="$0.00", allow_zero=True),
                }
            )

        return rows

    def _build_activity_rows(self, user_id: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in self.services.portfolio_repository.get_transactions(user_id, limit=8):
            quantity = float(item.get("quantity") or 0.0)
            price = float(item.get("price") or 0.0)
            rows.append(
                {
                    "timestamp": str(item.get("timestamp", ""))[:16].replace("T", " "),
                    "action": item.get("action", "-"),
                    "symbol": str(item.get("symbol", "")).upper(),
                    "quantity": round(quantity, 4),
                    "price": format_currency(price),
                    "notional": format_currency(quantity * price, allow_zero=True),
                }
            )
        return rows

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("trade-symbol-input", "disabled"),
            Output("trade-quantity-input", "disabled"),
            Output("trade-buy-btn", "disabled"),
            Output("trade-sell-btn", "disabled"),
            Output("trade-refresh-btn", "disabled"),
            Input("global-user-store", "data"),
            prevent_initial_call=False,
        )
        def lock_trade_controls(user_store):
            user_store = user_store or {}
            locked = not bool(user_store.get("user_id"))
            return locked, locked, locked, locked, locked

        @app.callback(
            Output("trade-symbol-input", "value"),
            Input("selected-symbol-store", "data"),
            prevent_initial_call=False,
        )
        def sync_trade_symbol(selected_symbol):
            return normalize_symbol((selected_symbol or {}).get("symbol"), self.services.settings.default_symbol)

        @app.callback(
            Output("trade-price-output", "children"),
            Output("trade-order-total", "children"),
            Input("trade-symbol-input", "value"),
            Input("trade-quantity-input", "value"),
            Input("global-user-store", "data"),
            prevent_initial_call=False,
        )
        def preview_order(symbol, quantity, user_store):
            try:
                user_store = user_store or {}
                if not user_store.get("user_id"):
                    return "Login required", "Login required"

                symbol = normalize_symbol(symbol, self.services.settings.default_symbol)
                quantity = float(quantity or 0.0)
                price = self.services.market_data_service.get_latest_price(symbol)
                notional = price * quantity

                price_text = format_currency(price)
                notional_text = format_currency(notional)
                if quantity <= 0:
                    notional_text = "Enter quantity"
                return price_text, notional_text
            except Exception as exc:
                return f"Error: {exc}", "Unavailable"

        @app.callback(
            Output("trade-message", "children"),
            Output("trade-balance-output", "children"),
            Output("trade-holdings-table", "data"),
            Output("trade-activity-table", "data"),
            Input("trade-buy-btn", "n_clicks"),
            Input("trade-sell-btn", "n_clicks"),
            Input("trade-refresh-btn", "n_clicks"),
            Input("global-user-store", "data"),
            State("trade-symbol-input", "value"),
            State("trade-quantity-input", "value"),
            prevent_initial_call=False,
        )
        def execute_trade(_, __, ___, user_store, symbol, quantity):
            del _, __, ___

            try:
                user_store = user_store or {}
                user_id = user_store.get("user_id")
                if not user_id:
                    return "Log in to access trading features.", "Balance: N/A", [], []

                def current_snapshot():
                    try:
                        balance_value = self.services.portfolio_repository.get_balance(user_id)
                        holdings_rows = self._build_holdings_rows(user_id)
                        activity_rows = self._build_activity_rows(user_id)
                        return balance_value, holdings_rows, activity_rows, None
                    except RuntimeError as exc:
                        return 0.0, [], [], str(exc)

                symbol = normalize_symbol(symbol)
                quantity = float(quantity or 0)

                action = ctx.triggered_id
                message = "Portfolio refreshed."

                if action in {"trade-buy-btn", "trade-sell-btn"}:
                    if not symbol:
                        snapshot_balance, snapshot_rows, activity_rows, snapshot_error = current_snapshot()
                        if snapshot_error:
                            return snapshot_error, "Balance: unavailable", [], []
                        return (
                            "Please enter valid ticker symbol.",
                            f"Balance: {format_currency(snapshot_balance, allow_zero=True)}",
                            snapshot_rows,
                            activity_rows,
                        )

                    if quantity <= 0:
                        snapshot_balance, snapshot_rows, activity_rows, snapshot_error = current_snapshot()
                        if snapshot_error:
                            return snapshot_error, "Balance: unavailable", [], []
                        return (
                            "Quantity must be greater than 0.",
                            f"Balance: {format_currency(snapshot_balance, allow_zero=True)}",
                            snapshot_rows,
                            activity_rows,
                        )

                    price = self.services.market_data_service.get_latest_price(symbol)
                    if price <= 0:
                        snapshot_balance, snapshot_rows, activity_rows, snapshot_error = current_snapshot()
                        if snapshot_error:
                            return snapshot_error, "Balance: unavailable", [], []
                        return (
                            f"Could not fetch valid market price for {symbol}.",
                            f"Balance: {format_currency(snapshot_balance, allow_zero=True)}",
                            snapshot_rows,
                            activity_rows,
                        )

                    if action == "trade-buy-btn":
                        result = self.services.portfolio_repository.buy_stock(user_id, symbol, quantity, price)
                    else:
                        result = self.services.portfolio_repository.sell_stock(user_id, symbol, quantity, price)

                    message = result.message

                balance, rows, activity_rows, snapshot_error = current_snapshot()
                if snapshot_error:
                    return snapshot_error, "Balance: unavailable", [], []

                return message, f"Balance: {format_currency(balance, allow_zero=True)}", rows, activity_rows
            except Exception as exc:
                return f"Trading error: {exc}", "Balance: unavailable", [], []
