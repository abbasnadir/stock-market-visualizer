"""Market tracking and stock chart feature."""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html

from src.features.base_feature import BaseFeature


class MarketFeature(BaseFeature):
    """Displays live quote snapshot and historical close chart."""

    def get_layout(self):
        default_symbol = self.services.settings.default_symbol

        return html.Section(
            [
                html.H2("Stock Value Graph and Tracker"),
                html.Div(
                    [
                        dcc.Input(
                            id="market-symbol-input",
                            type="text",
                            value=default_symbol,
                            placeholder="Ticker (e.g. AAPL)",
                            style={"marginRight": "8px"},
                        ),
                        dcc.Dropdown(
                            id="market-period-select",
                            options=[
                                {"label": "1 Month", "value": "1mo"},
                                {"label": "3 Months", "value": "3mo"},
                                {"label": "6 Months", "value": "6mo"},
                                {"label": "1 Year", "value": "1y"},
                                {"label": "2 Years", "value": "2y"},
                            ],
                            value="6mo",
                            clearable=False,
                            style={"marginRight": "8px", "minWidth": "160px"},
                        ),
                        html.Button("Refresh", id="market-refresh-btn", n_clicks=0),
                    ],
                    style={"display": "flex", "flexWrap": "wrap", "gap": "8px"},
                ),
                html.P(id="market-quote-output", style={"marginTop": "10px"}),
                html.Div(
                    [
                        html.Div(
                            id="market-chart-container",
                            children=[],
                            style={"width": "100%", "minHeight": "360px"},
                        )
                    ]
                ),
            ]
        )

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("market-quote-output", "children"),
            Output("market-chart-container", "children"),
            Input("market-refresh-btn", "n_clicks"),
            State("market-symbol-input", "value"),
            State("market-period-select", "value"),
        )
        def refresh_market_view(_, symbol, period):
            del _

            symbol = (symbol or self.services.settings.default_symbol).upper().strip()
            period = period or "6mo"

            snapshot = self.services.market_data_service.get_quote_snapshot(symbol)
            history = self.services.market_data_service.get_history(symbol=symbol, period=period, interval="1d")

            figure = go.Figure()
            figure.update_layout(
                margin={"l": 20, "r": 10, "t": 30, "b": 20},
                xaxis_title="Date",
                yaxis_title="Close Price (USD)",
                template="plotly_white",
                height=380,
            )

            if not history.empty:
                figure.add_trace(
                    go.Scatter(
                        x=history["Date"],
                        y=history["Close"],
                        mode="lines",
                        line={"width": 3, "color": "#1f77b4"},
                        name=symbol,
                    )
                )
            else:
                figure.add_annotation(
                    text="No market data available for the selected symbol.",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                )

            quote_text = (
                f"{snapshot['symbol']} | Price: ${snapshot['price']:.2f} | "
                f"Change: {snapshot['change']:+.2f} ({snapshot['change_pct']:+.2f}%)"
            )

            return quote_text, [
                html.Div(
                    dcc.Graph(figure=figure, config={"displayModeBar": False}),
                    style={"width": "100%"},
                )
            ]
