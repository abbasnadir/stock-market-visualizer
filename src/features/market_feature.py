"""Market tracking and stock chart feature."""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html

from src.features.base_feature import BaseFeature


class MarketFeature(BaseFeature):
    """Displays live quote snapshot and historical close chart."""

    @staticmethod
    def _format_compact_number(value: float) -> str:
        if value >= 1_000_000_000_000:
            return f"{value / 1_000_000_000_000:.2f}T"
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}B"
        if value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        if value >= 1_000:
            return f"{value / 1_000:.2f}K"
        return f"{value:.0f}"

    def _build_chart(self, symbol: str, history):
        figure = go.Figure()
        figure.update_layout(
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            xaxis={"showgrid": True, "gridcolor": "#edf2f7", "zeroline": False},
            yaxis={"showgrid": True, "gridcolor": "#edf2f7", "zeroline": False},
            template="plotly_white",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=340,
        )

        if not history.empty:
            figure.add_trace(
                go.Scatter(
                    x=history["Date"],
                    y=history["Close"],
                    mode="lines",
                    fill="tozeroy",
                    fillcolor="rgba(92, 107, 192, 0.12)",
                    line={"width": 2.5, "color": "#5c6bc0"},
                    name=symbol,
                    showlegend=False,
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

        return figure

    def get_layout(self):
        default_symbol = self.services.settings.default_symbol

        return html.Section(
            [
                html.Div(
                    [
                        dcc.Input(
                            id="market-symbol-input",
                            type="text",
                            value=default_symbol,
                            placeholder="Ticker (e.g. AAPL)",
                            style={"padding": "8px 12px", "borderRadius": "8px", "border": "1px solid #d6deeb"},
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
                            style={"margin": "0 8px", "minWidth": "160px"},
                        ),
                        html.Button("Search", id="market-refresh-btn", n_clicks=0),
                    ],
                    className="market-search-row",
                ),
                html.Div(
                    [
                        html.Div(id="stock-logo", children="A", className="stock-logo-large"),
                        html.Div(
                            [
                                html.H1(id="stock-name", children="Apple"),
                                html.P(id="stock-sub", children="Market snapshot and trend overview"),
                            ],
                            className="stock-title",
                        ),
                        html.Div(
                            [
                                html.H2(id="header-price", children="$0.00"),
                                html.Div(id="header-trend", children="+0.00%", className="trend-badge up"),
                            ],
                            className="stock-price-header",
                        ),
                    ],
                    className="stock-header",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.P("Market Cap"),
                                html.H3(id="card-mcap", children="$0.00"),
                                html.Div(
                                    [
                                        html.Span("24H", style={"color": "var(--text-muted)"}),
                                        html.Span("+0.00%", id="card-mcap-trend", style={"fontWeight": "600"}),
                                    ],
                                    className="trend-row",
                                ),
                            ],
                            className="summary-card",
                        ),
                        html.Div(
                            [
                                html.P("Volume"),
                                html.H3(id="card-volume", children="0"),
                                html.Div(
                                    [
                                        html.Span("24H", style={"color": "var(--text-muted)"}),
                                        html.Span("+0.00%", id="card-volume-trend", style={"fontWeight": "600"}),
                                    ],
                                    className="trend-row",
                                ),
                            ],
                            className="summary-card",
                        ),
                        html.Div(
                            [
                                html.P("Estimated FD Market Cap"),
                                html.H3(id="card-fdmc", children="$0.00"),
                                html.Div(
                                    [
                                        html.Span("Delta", style={"color": "var(--text-muted)"}),
                                        html.Span("+0.00%", id="card-fdmc-trend", style={"fontWeight": "600"}),
                                    ],
                                    className="trend-row",
                                ),
                            ],
                            className="summary-card",
                        ),
                        html.Div(
                            [
                                html.P("Shares Outstanding"),
                                html.H3(id="card-circ", children="0"),
                                html.Div(
                                    [
                                        html.Span("Reference", style={"color": "var(--text-muted)"}),
                                        html.Span("+0.00%", id="card-circ-trend", style={"fontWeight": "600"}),
                                    ],
                                    className="trend-row",
                                ),
                            ],
                            className="summary-card",
                        ),
                    ],
                    className="summary-cards-row",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H3(
                                            [
                                                html.Div("A", id="chart-logo-small", className="small-logo"),
                                                html.Span("Apple Inc. (AAPL)", id="chart-title"),
                                            ]
                                        ),
                                        html.Div(
                                            [
                                                html.Span("$0.00", id="chart-price", className="chart-price"),
                                                html.Span("+0.00 (0.00%)", id="chart-change", className="chart-change"),
                                            ]
                                        ),
                                    ],
                                    className="chart-meta",
                                )
                            ],
                            className="chart-header",
                        ),
                        html.Div(
                            id="market-chart-container",
                            children=[],
                            style={"width": "100%", "minHeight": "360px"},
                        ),
                        html.P(id="market-quote-output", className="market-quote-output"),
                    ],
                    className="chart-container-card",
                ),
            ]
        )

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("market-quote-output", "children"),
            Output("market-chart-container", "children"),
            Output("stock-logo", "children"),
            Output("chart-logo-small", "children"),
            Output("stock-name", "children"),
            Output("stock-sub", "children"),
            Output("chart-title", "children"),
            Output("header-price", "children"),
            Output("header-trend", "children"),
            Output("header-trend", "className"),
            Output("chart-price", "children"),
            Output("chart-change", "children"),
            Output("chart-change", "style"),
            Output("card-mcap", "children"),
            Output("card-mcap-trend", "children"),
            Output("card-mcap-trend", "style"),
            Output("card-volume", "children"),
            Output("card-volume-trend", "children"),
            Output("card-volume-trend", "style"),
            Output("card-fdmc", "children"),
            Output("card-fdmc-trend", "children"),
            Output("card-fdmc-trend", "style"),
            Output("card-circ", "children"),
            Output("card-circ-trend", "children"),
            Output("card-circ-trend", "style"),
            Output("rs-company-name", "children"),
            Output("rs-company", "children"),
            Output("rs-price", "children"),
            Output("rs-ticker", "children"),
            Output("rs-change", "children"),
            Output("rs-mcap", "children"),
            Output("rs-volume", "children"),
            Output("rs-pe", "children"),
            Input("market-refresh-btn", "n_clicks"),
            State("market-symbol-input", "value"),
            State("market-period-select", "value"),
            prevent_initial_call=False,
        )
        def refresh_market_view(_, symbol, period):
            del _

            symbol = (symbol or self.services.settings.default_symbol).upper().strip()
            period = period or "6mo"

            snapshot = self.services.market_data_service.get_quote_snapshot(symbol)
            metadata = self.services.market_data_service.get_stock_metadata(symbol)
            history = self.services.market_data_service.get_history(symbol=symbol, period=period, interval="1d")

            figure = self._build_chart(symbol, history)

            quote_text = (
                f"{snapshot['symbol']} | Price: ${snapshot['price']:.2f} | "
                f"Change: {snapshot['change']:+.2f} ({snapshot['change_pct']:+.2f}%)"
            )

            price = float(snapshot.get("price") or 0.0)
            change = float(snapshot.get("change") or 0.0)
            change_pct = float(snapshot.get("change_pct") or 0.0)

            market_cap = float(metadata.get("market_cap") or 0.0)
            volume = float(metadata.get("volume") or 0.0)
            pe_ratio = float(metadata.get("pe_ratio") or 0.0)
            shares_outstanding = float(metadata.get("shares_outstanding") or 0.0)
            company_name = str(metadata.get("company_name") or symbol)

            fdmc_value = market_cap if market_cap > 0 else price * shares_outstanding
            is_up = change >= 0
            trend_symbol = "+" if is_up else "-"
            trend_color = "var(--success)" if is_up else "var(--danger)"

            trend_text = f"{trend_symbol} {abs(change_pct):.2f}%"
            trend_class = "trend-badge up" if is_up else "trend-badge down"
            chart_change = f"{'+' if change >= 0 else ''}{change:.2f} ({change_pct:+.2f}%)"

            mcap_text = f"${self._format_compact_number(market_cap)}" if market_cap > 0 else "$0.00"
            volume_text = self._format_compact_number(volume) if volume > 0 else "0"
            fdmc_text = f"${self._format_compact_number(fdmc_value)}" if fdmc_value > 0 else "$0.00"
            circ_text = self._format_compact_number(shares_outstanding) if shares_outstanding > 0 else "0"

            logo_char = symbol[0] if symbol else "?"
            subtitle = "Live market snapshot"

            return (
                quote_text,
                [html.Div(dcc.Graph(figure=figure, config={"displayModeBar": False}), style={"width": "100%"})],
                logo_char,
                logo_char,
                company_name,
                subtitle,
                f"{company_name} ({symbol})",
                f"${price:.2f}",
                trend_text,
                trend_class,
                f"${price:.2f}",
                chart_change,
                {"color": trend_color, "marginLeft": "8px"},
                mcap_text,
                trend_text,
                {"color": trend_color, "fontWeight": "600"},
                volume_text,
                trend_text,
                {"color": trend_color, "fontWeight": "600"},
                fdmc_text,
                trend_text,
                {"color": trend_color, "fontWeight": "600"},
                circ_text,
                trend_text,
                {"color": trend_color, "fontWeight": "600"},
                f"{company_name} ({symbol})",
                company_name,
                f"${price:.2f}",
                symbol,
                f"{'+' if change >= 0 else ''}{change:.2f}",
                mcap_text,
                volume_text,
                f"{pe_ratio:.2f}" if pe_ratio > 0 else "-",
            )
