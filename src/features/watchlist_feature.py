"""Watchlist management feature."""

from __future__ import annotations

from dash import Dash, Input, Output, State, ctx, dash_table, dcc, html, no_update

from src.features.base_feature import BaseFeature
from src.ui.formatters import format_currency, format_percent, normalize_symbol


class WatchlistFeature(BaseFeature):
    """Allows adding, removing, and tracking watchlist symbols."""

    def get_layout(self):
        return html.Section(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.P("Watchlist Workspace", className="panel-title"),
                                html.P("Save symbols, monitor moves, click row to sync focus ticker.", className="panel-subtitle"),
                            ],
                            className="panel-copy",
                        ),
                        html.Div(
                            [
                                html.Span("Tracked symbols", className="metric-label"),
                                html.Strong("0", id="watchlist-count", className="metric-value"),
                            ],
                            className="metric-tile small-tile",
                        ),
                    ],
                    className="panel-header-row",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.P("Ticker", className="input-label"),
                                dcc.Input(
                                    id="watchlist-symbol-input",
                                    type="text",
                                    placeholder="Ticker",
                                    className="app-input",
                                ),
                            ],
                            className="field-stack grow",
                        ),
                        html.Button("Add", id="watchlist-add-btn", n_clicks=0, className="primary-btn"),
                        html.Button("Remove", id="watchlist-remove-btn", n_clicks=0, className="secondary-btn"),
                        html.Button("Refresh", id="watchlist-refresh-btn", n_clicks=0, className="ghost-btn"),
                    ],
                    className="button-row wrap align-end",
                ),
                html.P(id="watchlist-message", className="inline-feedback"),
                dash_table.DataTable(
                    id="watchlist-table",
                    columns=[
                        {"name": "Symbol", "id": "symbol"},
                        {"name": "Price", "id": "price"},
                        {"name": "Change", "id": "change"},
                        {"name": "Change %", "id": "change_pct"},
                    ],
                    data=[],
                    row_selectable="single",
                    selected_rows=[],
                    page_size=8,
                    style_table={"overflowX": "auto"},
                ),
            ]
        )

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("watchlist-symbol-input", "disabled"),
            Output("watchlist-add-btn", "disabled"),
            Output("watchlist-remove-btn", "disabled"),
            Output("watchlist-refresh-btn", "disabled"),
            Input("global-user-store", "data"),
            prevent_initial_call=False,
        )
        def lock_watchlist_controls(user_store):
            user_store = user_store or {}
            locked = not bool(user_store.get("user_id"))
            return locked, locked, locked, locked

        @app.callback(
            Output("watchlist-symbol-input", "value"),
            Input("selected-symbol-store", "data"),
            prevent_initial_call=False,
        )
        def sync_watchlist_symbol(selected_symbol):
            return normalize_symbol((selected_symbol or {}).get("symbol"))

        @app.callback(
            Output("watchlist-message", "children"),
            Output("watchlist-table", "data"),
            Output("watchlist-count", "children"),
            Input("watchlist-add-btn", "n_clicks"),
            Input("watchlist-remove-btn", "n_clicks"),
            Input("watchlist-refresh-btn", "n_clicks"),
            Input("global-user-store", "data"),
            State("watchlist-symbol-input", "value"),
            State("watchlist-table", "selected_rows"),
            State("watchlist-table", "data"),
            prevent_initial_call=False,
        )
        def update_watchlist(_, __, ___, user_store, symbol, selected_rows, table_rows):
            del _, __, ___

            try:
                user_store = user_store or {}
                user_id = user_store.get("user_id")
                if not user_id:
                    return "Log in to manage your watchlist.", [], "0"

                action = ctx.triggered_id
                symbol = normalize_symbol(symbol)
                selected_rows = selected_rows or []
                table_rows = table_rows or []
                selected_symbol = ""
                if selected_rows:
                    selected_index = selected_rows[0]
                    if selected_index < len(table_rows):
                        selected_symbol = normalize_symbol(table_rows[selected_index].get("symbol"))

                message = "Watchlist refreshed."

                if action == "watchlist-add-btn":
                    result = self.services.portfolio_repository.add_to_watchlist(user_id, symbol)
                    message = result.message
                elif action == "watchlist-remove-btn":
                    target_symbol = symbol or selected_symbol
                    result = self.services.portfolio_repository.remove_from_watchlist(user_id, target_symbol)
                    message = result.message

                try:
                    watchlist = self.services.portfolio_repository.get_watchlist(user_id)
                except RuntimeError as exc:
                    return str(exc), [], "0"

                snapshots = self.services.market_data_service.get_quote_map(watchlist)
                rows = []
                for item in watchlist:
                    snapshot = snapshots.get(item, {})
                    rows.append(
                        {
                            "symbol": item,
                            "price": format_currency(float(snapshot.get("price") or 0.0)),
                            "change": format_currency(abs(float(snapshot.get("change") or 0.0)), fallback="$0.00")
                            if float(snapshot.get("change") or 0.0) >= 0
                            else f"-{format_currency(abs(float(snapshot.get('change') or 0.0)), fallback='$0.00')}",
                            "change_pct": format_percent(float(snapshot.get("change_pct") or 0.0)),
                        }
                    )

                return message, rows, str(len(rows))
            except Exception as exc:
                return f"Watchlist error: {exc}", [], "0"

        @app.callback(
            Output("selected-symbol-store", "data", allow_duplicate=True),
            Input("watchlist-table", "selected_rows"),
            State("watchlist-table", "data"),
            prevent_initial_call=True,
        )
        def sync_selected_symbol(selected_rows, rows):
            rows = rows or []
            selected_rows = selected_rows or []
            if not selected_rows:
                return no_update
            row_index = selected_rows[0]
            if row_index >= len(rows):
                return no_update
            return {"symbol": normalize_symbol(rows[row_index].get("symbol"))}
