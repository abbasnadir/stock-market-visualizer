"""Portfolio valuation and holdings analytics feature."""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Dash, Input, Output, dash_table, dcc, html

from src.features.base_feature import BaseFeature
from src.ui.formatters import format_currency, format_percent


class PortfolioFeature(BaseFeature):
    """Calculates and visualizes portfolio value and allocation."""

    def get_layout(self):
        return html.Section(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.P("Portfolio Summary", className="panel-title"),
                                html.P("Live equity plus cash, allocation, position-level performance.", className="panel-subtitle"),
                            ],
                            className="panel-copy",
                        ),
                        html.Button("Refresh Analytics", id="portfolio-refresh-btn", n_clicks=0, className="ghost-btn"),
                    ],
                    className="panel-header-row",
                ),
                html.Div(
                    [
                        html.Div(
                            [html.Span("Total value", className="metric-label"), html.Strong("$0.00", id="portfolio-total-output", className="metric-value")],
                            className="metric-tile",
                        ),
                        html.Div(
                            [html.Span("Cash", className="metric-label"), html.Strong("$0.00", id="portfolio-cash-output", className="metric-value")],
                            className="metric-tile",
                        ),
                        html.Div(
                            [html.Span("Invested", className="metric-label"), html.Strong("$0.00", id="portfolio-invested-output", className="metric-value")],
                            className="metric-tile",
                        ),
                        html.Div(
                            [html.Span("Positions", className="metric-label"), html.Strong("0", id="portfolio-positions-output", className="metric-value")],
                            className="metric-tile",
                        ),
                    ],
                    className="metric-grid",
                ),
                html.P(id="portfolio-summary-note", className="inline-feedback muted"),
                html.Div(id="portfolio-graph-container", className="chart-panel"),
                html.Div(
                    [
                        html.P("Holdings Breakdown", className="panel-title"),
                        dash_table.DataTable(
                            id="portfolio-holdings-table",
                            columns=[
                                {"name": "Symbol", "id": "symbol"},
                                {"name": "Quantity", "id": "quantity"},
                                {"name": "Avg Cost", "id": "avg_cost"},
                                {"name": "Price", "id": "current_price"},
                                {"name": "Market Value", "id": "market_value"},
                                {"name": "Weight", "id": "weight"},
                                {"name": "P/L", "id": "pl"},
                            ],
                            data=[],
                            page_size=8,
                            style_table={"overflowX": "auto"},
                        ),
                    ],
                    className="app-panel table-panel",
                ),
            ]
        )

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("portfolio-refresh-btn", "disabled"),
            Input("global-user-store", "data"),
            prevent_initial_call=False,
        )
        def lock_portfolio_controls(user_store):
            user_store = user_store or {}
            return not bool(user_store.get("user_id"))

        @app.callback(
            Output("portfolio-total-output", "children"),
            Output("portfolio-cash-output", "children"),
            Output("portfolio-invested-output", "children"),
            Output("portfolio-positions-output", "children"),
            Output("portfolio-summary-note", "children"),
            Output("portfolio-graph-container", "children"),
            Output("portfolio-holdings-table", "data"),
            Input("portfolio-refresh-btn", "n_clicks"),
            Input("global-user-store", "data"),
            prevent_initial_call=False,
        )
        def refresh_portfolio(_, user_store):
            del _
            try:
                user_store = user_store or {}
                user_id = user_store.get("user_id")

                if not user_id:
                    figure = go.Figure()
                    figure.add_annotation(
                        text="Log in to view portfolio valuation.",
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                    )
                    figure.update_layout(height=340, template="plotly_white", margin={"l": 20, "r": 20, "t": 20, "b": 20})
                    return "$0.00", "$0.00", "$0.00", "0", "Sign in to unlock analytics.", [dcc_graph(figure)], []

                try:
                    balance = self.services.portfolio_repository.get_balance(user_id)
                    positions = self.services.portfolio_repository.get_positions(user_id)
                except RuntimeError as exc:
                    figure = go.Figure()
                    figure.add_annotation(
                        text=str(exc),
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                    )
                    figure.update_layout(height=340, template="plotly_white", margin={"l": 20, "r": 20, "t": 20, "b": 20})
                    return "Unavailable", "Unavailable", "Unavailable", "0", "Portfolio data unavailable.", [dcc_graph(figure)], []

                snapshots = self.services.market_data_service.get_quote_map([position["symbol"] for position in positions])
                labels = ["Cash"]
                values = [max(float(balance), 0.0)]
                holdings_rows = []
                invested_total = 0.0
                unavailable_symbols: list[str] = []

                for position in positions:
                    symbol = position["symbol"]
                    quantity = float(position["quantity"])
                    avg_cost = float(position["avg_cost"])
                    current_price = float(snapshots.get(symbol, {}).get("price") or 0.0)
                    if current_price <= 0:
                        unavailable_symbols.append(symbol)
                        continue

                    market_value = quantity * current_price
                    cost_basis = quantity * avg_cost
                    invested_total += market_value
                    labels.append(symbol)
                    values.append(max(market_value, 0.0))

                    holdings_rows.append(
                        {
                            "symbol": symbol,
                            "quantity": round(quantity, 4),
                            "avg_cost": format_currency(avg_cost),
                            "current_price": format_currency(current_price),
                            "market_value": format_currency(market_value, allow_zero=True),
                            "weight": "0.00%",
                            "pl": format_currency(market_value - cost_basis, fallback="$0.00", allow_zero=True),
                        }
                    )

                total_value = balance + invested_total
                for row in holdings_rows:
                    market_value = float(str(row["market_value"]).replace("$", "").replace(",", "") or 0.0)
                    weight = (market_value / total_value * 100.0) if total_value > 0 else 0.0
                    row["weight"] = format_percent(weight)

                figure = go.Figure(
                    data=[
                        go.Pie(
                            labels=labels,
                            values=values,
                            hole=0.55,
                            marker={"colors": ["#0f172a", "#1d4ed8", "#0ea5e9", "#14b8a6", "#f97316", "#facc15"]},
                        )
                    ]
                )
                figure.update_layout(
                    template="plotly_white",
                    height=380,
                    margin={"l": 20, "r": 20, "t": 30, "b": 20},
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )

                note = "Live analytics synced."
                if unavailable_symbols:
                    note = f"Missing live prices for: {', '.join(sorted(set(unavailable_symbols)))}."

                return (
                    format_currency(total_value, allow_zero=True),
                    format_currency(balance, allow_zero=True),
                    format_currency(invested_total, allow_zero=True),
                    str(len(positions)),
                    note,
                    [dcc_graph(figure)],
                    holdings_rows,
                )
            except Exception as exc:
                figure = go.Figure()
                figure.add_annotation(
                    text=f"Portfolio error: {exc}",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                )
                figure.update_layout(height=340, template="plotly_white", margin={"l": 20, "r": 20, "t": 20, "b": 20})
                return "Unavailable", "Unavailable", "Unavailable", "0", f"Portfolio error: {exc}", [dcc_graph(figure)], []


def dcc_graph(figure):
    return dcc.Graph(figure=figure, config={"displayModeBar": False})
