"""Smart alert feature for price threshold notifications."""

from __future__ import annotations

from dash import Dash, Input, Output, State, ctx, dcc, dash_table, html

from src.features.base_feature import BaseFeature


class AlertsFeature(BaseFeature):
    """Creates and evaluates price alerts for watch symbols."""

    def get_layout(self):
        return html.Section(
            [
                html.H2("Smart Alerts"),
                html.Div(
                    [
                        dcc.Input(
                            id="alert-symbol-input",
                            type="text",
                            placeholder="Ticker",
                            style={"marginRight": "8px"},
                        ),
                        dcc.Input(
                            id="alert-target-input",
                            type="number",
                            placeholder="Target price",
                            min=0,
                            step=0.01,
                            style={"marginRight": "8px", "width": "160px"},
                        ),
                        dcc.Dropdown(
                            id="alert-condition-select",
                            options=[
                                {"label": "Above", "value": "above"},
                                {"label": "Below", "value": "below"},
                            ],
                            value="above",
                            clearable=False,
                            style={"marginRight": "8px", "minWidth": "140px"},
                        ),
                        html.Button("Add Alert", id="alert-add-btn", n_clicks=0),
                        html.Button(
                            "Check Alerts",
                            id="alert-check-btn",
                            n_clicks=0,
                            style={"marginLeft": "8px"},
                        ),
                        html.Button(
                            "Refresh",
                            id="alert-refresh-btn",
                            n_clicks=0,
                            style={"marginLeft": "8px"},
                        ),
                    ],
                    style={"display": "flex", "flexWrap": "wrap", "gap": "8px"},
                ),
                html.P(id="alert-message", style={"marginTop": "10px"}),
                dash_table.DataTable(
                    id="alert-table",
                    columns=[
                        {"name": "Symbol", "id": "symbol"},
                        {"name": "Condition", "id": "condition"},
                        {"name": "Target Price", "id": "target_price"},
                    ],
                    data=[],
                    page_size=8,
                    style_table={"overflowX": "auto"},
                ),
                html.H4("Triggered Alerts"),
                html.Ul(id="alert-triggered-list"),
            ]
        )

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("alert-message", "children"),
            Output("alert-table", "data"),
            Output("alert-triggered-list", "children"),
            Input("alert-add-btn", "n_clicks"),
            Input("alert-check-btn", "n_clicks"),
            Input("alert-refresh-btn", "n_clicks"),
            Input("global-user-store", "data"),
            State("alert-symbol-input", "value"),
            State("alert-target-input", "value"),
            State("alert-condition-select", "value"),
            prevent_initial_call=False,
        )
        def handle_alerts(_, __, ___, user_store, symbol, target_price, condition):
            del _, __, ___

            user_store = user_store or {}
            user_id = user_store.get("user_id")

            if not user_id:
                return "Log in to manage alerts.", [], [html.Li("No alerts triggered.")]

            action = ctx.triggered_id
            message = "Alerts refreshed."

            if action == "alert-add-btn":
                symbol = (symbol or "").upper().strip()
                if not symbol:
                    return (
                        "Please provide a valid ticker symbol.",
                        self.services.portfolio_repository.get_alerts(user_id),
                        [html.Li("No alerts triggered.")],
                    )
                if target_price is None or float(target_price) <= 0:
                    return (
                        "Target price must be greater than 0.",
                        self.services.portfolio_repository.get_alerts(user_id),
                        [html.Li("No alerts triggered.")],
                    )

                result = self.services.portfolio_repository.add_alert(
                    user_id=user_id,
                    symbol=symbol,
                    target_price=float(target_price),
                    condition=condition or "above",
                )
                message = result.message

            alerts = self.services.portfolio_repository.get_alerts(user_id)
            alert_rows = [
                {
                    "symbol": item["symbol"],
                    "condition": item["condition"],
                    "target_price": round(float(item["target_price"]), 2),
                }
                for item in alerts
            ]

            triggered_items = [html.Li("No alerts triggered.")]
            if action == "alert-check-btn":
                symbols = sorted({item["symbol"].upper() for item in alerts})
                market_prices = {
                    ticker: self.services.market_data_service.get_latest_price(ticker)
                    for ticker in symbols
                }
                triggered = self.services.portfolio_repository.check_alerts(user_id, market_prices)
                if triggered:
                    triggered_items = [html.Li(line) for line in triggered]
                message = f"Checked {len(symbols)} symbol(s) against active alerts."

            return message, alert_rows, triggered_items
