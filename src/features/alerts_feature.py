"""Smart alert feature for price threshold notifications."""

from __future__ import annotations

from dash import Dash, Input, Output, State, ctx, dash_table, dcc, html, no_update

from src.features.base_feature import BaseFeature
from src.ui.formatters import format_currency, normalize_symbol


class AlertsFeature(BaseFeature):
    """Creates, removes, and evaluates price alerts."""

    def get_layout(self):
        return html.Section(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.P("Alert Rules", className="panel-title"),
                                html.P("Create threshold rules and check live trigger status.", className="panel-subtitle"),
                            ],
                            className="panel-copy",
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
                                    id="alert-symbol-input",
                                    type="text",
                                    placeholder="Ticker",
                                    className="app-input",
                                ),
                            ],
                            className="field-stack grow",
                        ),
                        html.Div(
                            [
                                html.P("Target", className="input-label"),
                                dcc.Input(
                                    id="alert-target-input",
                                    type="number",
                                    placeholder="Target price",
                                    min=0,
                                    step=0.01,
                                    className="app-input",
                                ),
                            ],
                            className="field-stack compact",
                        ),
                        html.Div(
                            [
                                html.P("Condition", className="input-label"),
                                dcc.Dropdown(
                                    id="alert-condition-select",
                                    options=[
                                        {"label": "Above", "value": "above"},
                                        {"label": "Below", "value": "below"},
                                    ],
                                    value="above",
                                    clearable=False,
                                    className="app-dropdown",
                                ),
                            ],
                            className="field-stack compact",
                        ),
                    ],
                    className="form-grid three-up",
                ),
                html.Div(
                    [
                        html.Button("Add Alert", id="alert-add-btn", n_clicks=0, className="primary-btn"),
                        html.Button("Remove Selected", id="alert-remove-btn", n_clicks=0, className="secondary-btn"),
                        html.Button("Check Alerts", id="alert-check-btn", n_clicks=0, className="ghost-btn"),
                        html.Button("Refresh", id="alert-refresh-btn", n_clicks=0, className="ghost-btn"),
                    ],
                    className="button-row wrap",
                ),
                html.P(id="alert-message", className="inline-feedback"),
                dash_table.DataTable(
                    id="alert-table",
                    columns=[
                        {"name": "Symbol", "id": "symbol"},
                        {"name": "Condition", "id": "condition"},
                        {"name": "Target", "id": "target_price"},
                        {"name": "Current", "id": "current_price"},
                        {"name": "Status", "id": "status"},
                    ],
                    data=[],
                    row_selectable="single",
                    selected_rows=[],
                    page_size=8,
                    style_table={"overflowX": "auto"},
                ),
                html.Div(
                    [
                        html.H4("Triggered Alerts", className="panel-title"),
                        html.Ul(id="alert-triggered-list", className="list-block"),
                    ],
                    className="app-panel",
                ),
            ]
        )

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("alert-symbol-input", "disabled"),
            Output("alert-target-input", "disabled"),
            Output("alert-condition-select", "disabled"),
            Output("alert-add-btn", "disabled"),
            Output("alert-remove-btn", "disabled"),
            Output("alert-check-btn", "disabled"),
            Output("alert-refresh-btn", "disabled"),
            Input("global-user-store", "data"),
            prevent_initial_call=False,
        )
        def lock_alert_controls(user_store):
            user_store = user_store or {}
            locked = not bool(user_store.get("user_id"))
            return locked, locked, locked, locked, locked, locked, locked

        @app.callback(
            Output("alert-symbol-input", "value"),
            Input("selected-symbol-store", "data"),
            prevent_initial_call=False,
        )
        def sync_alert_symbol(selected_symbol):
            return normalize_symbol((selected_symbol or {}).get("symbol"))

        @app.callback(
            Output("alert-message", "children"),
            Output("alert-table", "data"),
            Output("alert-triggered-list", "children"),
            Input("alert-add-btn", "n_clicks"),
            Input("alert-remove-btn", "n_clicks"),
            Input("alert-check-btn", "n_clicks"),
            Input("alert-refresh-btn", "n_clicks"),
            Input("global-user-store", "data"),
            State("alert-symbol-input", "value"),
            State("alert-target-input", "value"),
            State("alert-condition-select", "value"),
            State("alert-table", "selected_rows"),
            State("alert-table", "data"),
            prevent_initial_call=False,
        )
        def handle_alerts(_, __, ___, ____, user_store, symbol, target_price, condition, selected_rows, table_rows):
            del _, __, ___, ____

            try:
                user_store = user_store or {}
                user_id = user_store.get("user_id")

                if not user_id:
                    return "Log in to manage alerts.", [], [html.Li("No alerts triggered.")]

                action = ctx.triggered_id
                symbol = normalize_symbol(symbol)
                selected_rows = selected_rows or []
                table_rows = table_rows or []
                message = "Alerts refreshed."

                def load_alert_rows():
                    alerts_data = self.services.portfolio_repository.get_alerts(user_id)
                    snapshots = self.services.market_data_service.get_quote_map([item["symbol"] for item in alerts_data])
                    rows = []
                    for item in alerts_data:
                        current_price = float(snapshots.get(item["symbol"], {}).get("price") or 0.0)
                        target = float(item["target_price"])
                        condition_value = str(item["condition"]).lower()
                        status = "Monitoring"
                        if current_price > 0:
                            if condition_value == "above" and current_price >= target:
                                status = "Triggered"
                            elif condition_value == "below" and current_price <= target:
                                status = "Triggered"

                        rows.append(
                            {
                                "alert_id": item["id"],
                                "symbol": item["symbol"],
                                "condition": condition_value.title(),
                                "target_price": format_currency(target),
                                "current_price": format_currency(current_price),
                                "status": status,
                            }
                        )
                    return alerts_data, rows

                if action == "alert-add-btn":
                    if not symbol:
                        try:
                            _, rows = load_alert_rows()
                        except RuntimeError as exc:
                            return str(exc), [], [html.Li("No alerts triggered.")]
                        return "Please provide valid ticker symbol.", rows, [html.Li("No alerts triggered.")]

                    if target_price is None or float(target_price) <= 0:
                        try:
                            _, rows = load_alert_rows()
                        except RuntimeError as exc:
                            return str(exc), [], [html.Li("No alerts triggered.")]
                        return "Target price must be greater than 0.", rows, [html.Li("No alerts triggered.")]

                    result = self.services.portfolio_repository.add_alert(
                        user_id=user_id,
                        symbol=symbol,
                        target_price=float(target_price),
                        condition=condition or "above",
                    )
                    message = result.message
                elif action == "alert-remove-btn":
                    if not selected_rows:
                        try:
                            _, rows = load_alert_rows()
                        except RuntimeError as exc:
                            return str(exc), [], [html.Li("No alerts triggered.")]
                        return "Select alert row to remove.", rows, [html.Li("No alerts triggered.")]

                    selected_index = selected_rows[0]
                    if selected_index < len(table_rows):
                        alert_id = int(table_rows[selected_index]["alert_id"])
                        result = self.services.portfolio_repository.remove_alert(user_id, alert_id)
                        message = result.message

                try:
                    alerts, alert_rows = load_alert_rows()
                except RuntimeError as exc:
                    return str(exc), [], [html.Li("No alerts triggered.")]

                triggered_items = [html.Li("No alerts triggered.")]
                if action == "alert-check-btn":
                    symbols = sorted({item["symbol"].upper() for item in alerts})
                    market_prices = {}
                    unavailable_symbols = []
                    for ticker in symbols:
                        live_price = self.services.market_data_service.get_latest_price(ticker)
                        if live_price > 0:
                            market_prices[ticker] = live_price
                        else:
                            unavailable_symbols.append(ticker)

                    triggered = self.services.portfolio_repository.check_alerts(user_id, market_prices)
                    if triggered:
                        triggered_items = [html.Li(line) for line in triggered]
                    message = f"Checked {len(symbols)} symbol(s) against active alerts."
                    if unavailable_symbols:
                        message = f"{message} Live price unavailable: {', '.join(unavailable_symbols)}."

                return message, alert_rows, triggered_items
            except Exception as exc:
                return f"Alerts error: {exc}", [], [html.Li("No alerts triggered.")]

        @app.callback(
            Output("selected-symbol-store", "data", allow_duplicate=True),
            Input("alert-table", "selected_rows"),
            State("alert-table", "data"),
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
