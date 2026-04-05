"""Watchlist management feature."""

from __future__ import annotations

from dash import Dash, Input, Output, State, ctx, dcc, dash_table, html

from src.features.base_feature import BaseFeature


class WatchlistFeature(BaseFeature):
    """Allows adding/removing symbols and tracking latest prices."""

    def get_layout(self):
        return html.Section(
            [
                html.H2("Watchlist"),
                html.Div(
                    [
                        dcc.Input(
                            id="watchlist-symbol-input",
                            type="text",
                            placeholder="Ticker",
                            style={"marginRight": "8px"},
                        ),
                        html.Button("Add", id="watchlist-add-btn", n_clicks=0),
                        html.Button(
                            "Remove",
                            id="watchlist-remove-btn",
                            n_clicks=0,
                            style={"marginLeft": "8px"},
                        ),
                        html.Button(
                            "Refresh",
                            id="watchlist-refresh-btn",
                            n_clicks=0,
                            style={"marginLeft": "8px"},
                        ),
                    ],
                    style={"display": "flex", "flexWrap": "wrap", "gap": "8px"},
                ),
                html.P(id="watchlist-message", style={"marginTop": "10px"}),
                dash_table.DataTable(
                    id="watchlist-table",
                    columns=[
                        {"name": "Symbol", "id": "symbol"},
                        {"name": "Latest Price", "id": "price"},
                    ],
                    data=[],
                    page_size=8,
                    style_table={"overflowX": "auto"},
                ),
            ]
        )

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("watchlist-message", "children"),
            Output("watchlist-table", "data"),
            Input("watchlist-add-btn", "n_clicks"),
            Input("watchlist-remove-btn", "n_clicks"),
            Input("watchlist-refresh-btn", "n_clicks"),
            Input("global-user-store", "data"),
            State("watchlist-symbol-input", "value"),
            prevent_initial_call=False,
        )
        def update_watchlist(_, __, ___, user_store, symbol):
            del _, __, ___

            user_store = user_store or {}
            user_id = user_store.get("user_id")
            if not user_id:
                return "Log in to manage your watchlist.", []

            action = ctx.triggered_id
            symbol = (symbol or "").upper().strip()
            message = "Watchlist refreshed."

            if action == "watchlist-add-btn":
                result = self.services.portfolio_repository.add_to_watchlist(user_id, symbol)
                message = result.message
            elif action == "watchlist-remove-btn":
                result = self.services.portfolio_repository.remove_from_watchlist(user_id, symbol)
                message = result.message

            watchlist = self.services.portfolio_repository.get_watchlist(user_id)
            rows = []
            for item in watchlist:
                price = self.services.market_data_service.get_latest_price(item)
                rows.append({"symbol": item, "price": round(price, 2)})

            return message, rows
