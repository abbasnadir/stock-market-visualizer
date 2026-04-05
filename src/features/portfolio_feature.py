"""Portfolio valuation feature."""

from __future__ import annotations

import plotly.graph_objects as go
from dash import Dash, Input, Output, html

from src.features.base_feature import BaseFeature


class PortfolioFeature(BaseFeature):
    """Calculates and visualizes total portfolio value."""

    def get_layout(self):
        return html.Section(
            [
                html.H2("Portfolio Value Calculation"),
                html.Button("Refresh Value", id="portfolio-refresh-btn", n_clicks=0),
                html.P(id="portfolio-total-output", style={"marginTop": "10px", "fontWeight": "bold"}),
                html.Div(id="portfolio-graph-container"),
            ]
        )

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("portfolio-total-output", "children"),
            Output("portfolio-graph-container", "children"),
            Input("portfolio-refresh-btn", "n_clicks"),
            Input("global-user-store", "data"),
            prevent_initial_call=False,
        )
        def refresh_portfolio(_, user_store):
            del _

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
                figure.update_layout(height=340, template="plotly_white")
                return "Portfolio Value: N/A", [dcc_graph(figure)]

            balance = self.services.portfolio_repository.get_balance(user_id)
            positions = self.services.portfolio_repository.get_positions(user_id)

            labels = ["Cash"]
            values = [max(float(balance), 0.0)]

            holdings_value = 0.0
            for position in positions:
                symbol = position["symbol"]
                quantity = float(position["quantity"])
                current_price = self.services.market_data_service.get_latest_price(symbol)
                market_value = quantity * current_price
                holdings_value += market_value
                labels.append(symbol)
                values.append(max(market_value, 0.0))

            total_value = balance + holdings_value

            figure = go.Figure(
                data=[
                    go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.45,
                    )
                ]
            )
            figure.update_layout(
                template="plotly_white",
                height=380,
                margin={"l": 20, "r": 20, "t": 30, "b": 20},
            )

            return f"Portfolio Value: ${total_value:,.2f}", [dcc_graph(figure)]


def dcc_graph(figure):
    from dash import dcc

    return dcc.Graph(figure=figure, config={"displayModeBar": False})
