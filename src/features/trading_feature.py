"""Trading feature for buy and sell actions with balance updates."""

from __future__ import annotations

from typing import Any

from dash import Dash, Input, Output, State, ctx, dcc, dash_table, html

from src.features.base_feature import BaseFeature


class TradingFeature(BaseFeature):
    """Supports buy/sell operations with balance calculation."""

    def get_layout(self):
        return html.Section(
            [
                html.H2("Buy / Sell Shares (Balance Calculation)"),
                html.Div(
                    [
                        dcc.Input(
                            id="trade-symbol-input",
                            type="text",
                            placeholder="Ticker",
                            value=self.services.settings.default_symbol,
                            style={"marginRight": "8px"},
                        ),
                        dcc.Input(
                            id="trade-quantity-input",
                            type="number",
                            placeholder="Quantity",
                            min=1,
                            step=1,
                            value=1,
                            style={"marginRight": "8px", "width": "120px"},
                        ),
                        html.Button("Buy", id="trade-buy-btn", n_clicks=0),
                        html.Button(
                            "Sell",
                            id="trade-sell-btn",
                            n_clicks=0,
                            style={"marginLeft": "8px"},
                        ),
                        html.Button(
                            "Refresh Portfolio",
                            id="trade-refresh-btn",
                            n_clicks=0,
                            style={"marginLeft": "8px"},
                        ),
                    ],
                    style={"display": "flex", "flexWrap": "wrap", "gap": "8px"},
                ),
                html.P(id="trade-message", style={"marginTop": "10px"}),
                html.P(id="trade-balance-output", style={"fontWeight": "bold"}),
                dash_table.DataTable(
                    id="trade-holdings-table",
                    columns=[
                        {"name": "Symbol", "id": "symbol"},
                        {"name": "Quantity", "id": "quantity"},
                        {"name": "Avg Cost", "id": "avg_cost"},
                        {"name": "Current Price", "id": "current_price"},
                        {"name": "Market Value", "id": "market_value"},
                    ],
                    data=[],
                    page_size=8,
                    style_table={"overflowX": "auto"},
                ),
            ]
        )

    def _build_holdings_rows(self, user_id: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        positions = self.services.portfolio_repository.get_positions(user_id)

        for position in positions:
            symbol = position["symbol"]
            quantity = float(position["quantity"])
            avg_cost = float(position["avg_cost"])
            current_price = self.services.market_data_service.get_latest_price(symbol)
            market_value = quantity * current_price

            rows.append(
                {
                    "symbol": symbol,
                    "quantity": round(quantity, 4),
                    "avg_cost": round(avg_cost, 2),
                    "current_price": round(current_price, 2),
                    "market_value": round(market_value, 2),
                }
            )

        return rows

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("trade-message", "children"),
            Output("trade-balance-output", "children"),
            Output("trade-holdings-table", "data"),
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

            user_store = user_store or {}
            user_id = user_store.get("user_id")
            if not user_id:
                return (
                    "Log in to access trading features.",
                    "Balance: N/A",
                    [],
                )

            symbol = (symbol or "").upper().strip()
            quantity = float(quantity or 0)

            action = ctx.triggered_id
            message = "Portfolio refreshed."

            if action in {"trade-buy-btn", "trade-sell-btn"}:
                if not symbol:
                    return (
                        "Please enter a valid ticker symbol.",
                        f"Balance: ${self.services.portfolio_repository.get_balance(user_id):,.2f}",
                        self._build_holdings_rows(user_id),
                    )

                if quantity <= 0:
                    return (
                        "Quantity must be greater than 0.",
                        f"Balance: ${self.services.portfolio_repository.get_balance(user_id):,.2f}",
                        self._build_holdings_rows(user_id),
                    )

                price = self.services.market_data_service.get_latest_price(symbol)
                if price <= 0:
                    return (
                        f"Could not fetch a valid market price for {symbol}.",
                        f"Balance: ${self.services.portfolio_repository.get_balance(user_id):,.2f}",
                        self._build_holdings_rows(user_id),
                    )

                if action == "trade-buy-btn":
                    result = self.services.portfolio_repository.buy_stock(user_id, symbol, quantity, price)
                else:
                    result = self.services.portfolio_repository.sell_stock(user_id, symbol, quantity, price)

                message = result.message

            balance = self.services.portfolio_repository.get_balance(user_id)
            rows = self._build_holdings_rows(user_id)

            return message, f"Balance: ${balance:,.2f}", rows
