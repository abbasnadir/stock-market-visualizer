"""Market tracking and stock chart feature."""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html

from src.features.base_feature import BaseFeature
from src.ui.formatters import (
    format_compact_number,
    format_currency,
    format_percent,
    get_change_tone,
    normalize_symbol,
)


class MarketFeature(BaseFeature):
    """Displays live quote snapshot and historical close chart."""

    def _build_chart(self, symbol: str, history):
        figure = go.Figure()
        figure.update_layout(
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            xaxis={"showgrid": True, "gridcolor": "rgba(148, 163, 184, 0.16)", "zeroline": False},
            yaxis={"showgrid": True, "gridcolor": "rgba(148, 163, 184, 0.16)", "zeroline": False},
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
                    fillcolor="rgba(43, 108, 176, 0.14)",
                    line={"width": 2.8, "color": "#1d4ed8"},
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
                        html.Div(
                            [
                                html.P("Symbol", className="input-label"),
                                dcc.Input(
                                    id="market-symbol-input",
                                    type="text",
                                    value=default_symbol,
                                    placeholder="Ticker (e.g. AAPL)",
                                    className="app-input",
                                ),
                            ],
                            className="field-stack grow",
                        ),
                        html.Div(
                            [
                                html.P("Range", className="input-label"),
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
                                    className="app-dropdown",
                                ),
                            ],
                            className="field-stack compact",
                        ),
                        html.Button("Refresh Market", id="market-refresh-btn", n_clicks=0, className="primary-btn"),
                    ],
                    className="market-search-row",
                ),
                html.Div(
                    [
                        html.Div(id="stock-logo", children="A", className="stock-logo-large"),
                        html.Div(
                            [
                                html.H1(id="stock-name", children="Apple"),
                                html.P(id="stock-sub", children="Market snapshot, live quote, momentum context"),
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
            Output("market-symbol-input", "value"),
            Input("selected-symbol-store", "data"),
            prevent_initial_call=False,
        )
        def sync_market_symbol(selected_symbol):
            return normalize_symbol((selected_symbol or {}).get("symbol"), self.services.settings.default_symbol)

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
            Output("selected-symbol-store", "data"),
            Input("market-refresh-btn", "n_clicks"),
            State("market-symbol-input", "value"),
            State("market-period-select", "value"),
            prevent_initial_call=False,
        )
        def refresh_market_view(_, symbol, period):
            del _

            symbol = normalize_symbol(symbol, self.services.settings.default_symbol)
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
            tone, trend_class = get_change_tone(change)
            if price > 0:
                trend_color = "var(--success)" if tone == "positive" else "var(--danger)" if tone == "negative" else "var(--text-muted)"
                trend_text = format_percent(change_pct)
                chart_change = f"{'+' if change >= 0 else ''}{change:.2f} ({change_pct:+.2f}%)"
                price_text = format_currency(price)
                rs_change_text = f"{'+' if change >= 0 else ''}{change:.2f}"
            else:
                quote_text = f"{symbol} | Live quote unavailable. Check ticker/network and retry."
                trend_color = "var(--text-muted)"
                trend_text = "Unavailable"
                trend_class = "trend-badge neutral"
                chart_change = "Unavailable"
                price_text = "Unavailable"
                rs_change_text = "Unavailable"

            mcap_text = format_compact_number(market_cap, prefix="$")
            volume_text = format_compact_number(volume)
            fdmc_text = format_compact_number(fdmc_value, prefix="$")
            circ_text = format_compact_number(shares_outstanding)

            logo_char = symbol[0] if symbol else "?"
            subtitle = "Live market snapshot with synced workspace ticker"

            return (
                quote_text,
                [html.Div(dcc.Graph(figure=figure, config={"displayModeBar": False}), style={"width": "100%"})],
                logo_char,
                logo_char,
                company_name,
                subtitle,
                f"{company_name} ({symbol})",
                price_text,
                trend_text,
                trend_class,
                price_text,
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
                price_text,
                symbol,
                rs_change_text,
                mcap_text,
                volume_text,
                f"{pe_ratio:.2f}" if pe_ratio > 0 else "-",
                {"symbol": symbol},
            )
