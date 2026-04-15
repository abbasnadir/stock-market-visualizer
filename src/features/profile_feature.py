"""User profile dropdown shown in the dashboard top bar."""

from __future__ import annotations

from dash import Dash, Input, Output, dcc, html

from src.features.base_feature import BaseFeature
from src.ui.formatters import format_currency


class ProfileFeature(BaseFeature):
    """Displays compact account information and portfolio quick stats."""

    def get_layout(self):
        return html.Div(
            [
                html.Div(
                    html.Span("GU", id="profile-initials"),
                    className="profile-icon",
                    tabIndex="0",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.P("Guest User", id="profile-name", className="profile-name"),
                                html.P("Please sign in", id="profile-email", className="profile-email"),
                            ],
                            className="profile-header-section",
                        ),
                        html.Ul(
                            [
                                html.Li(dcc.Link("Overview", href="/", refresh=False)),
                                html.Li(dcc.Link("Trading", href="/trading", refresh=False)),
                                html.Li(dcc.Link("Portfolio", href="/portfolio", refresh=False)),
                                html.Li(dcc.Link("Watchlist", href="/watchlist", refresh=False)),
                                html.Li(dcc.Link("Alerts", href="/alerts", refresh=False)),
                            ],
                            className="profile-links-list",
                        ),
                        html.Hr(),
                        html.Div(
                            [
                                html.P("Account Snapshot", className="insights-label"),
                                html.Div(
                                    [
                                        html.Span("Total Portfolio:", className="insight-title"),
                                        html.Span("$0.00", id="profile-total-value", className="insight-value"),
                                    ],
                                    className="insight-row",
                                ),
                                html.Div(
                                    [
                                        html.Span("Profit / Loss:", className="insight-title"),
                                        html.Span("0.00%", id="profile-pl", className="insight-value"),
                                    ],
                                    className="insight-row",
                                ),
                                html.Div(
                                    [
                                        html.Span("Stocks Owned:", className="insight-title"),
                                        html.Span("0", id="profile-stocks-count", className="insight-value"),
                                    ],
                                    className="insight-row",
                                ),
                            ],
                            className="profile-insights-section",
                        ),
                        html.Hr(),
                        html.Div(
                            [
                                html.Button("Switch Account", id="profile-switch-btn", className="profile-action-btn"),
                                html.Button("Logout", id="profile-logout-btn", className="profile-action-btn logout-btn"),
                            ],
                            className="profile-actions-section",
                        ),
                    ],
                    className="dropdown-menu",
                ),
            ],
            className="profile-dropdown-container",
            id="profile-dropdown-container",
        )

    def register_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output("profile-switch-btn", "style"),
            Output("profile-logout-btn", "style"),
            Input("global-user-store", "data"),
            prevent_initial_call=False,
        )
        def toggle_profile_actions(user_data):
            user_data = user_data or {}
            if user_data.get("user_id"):
                return {"display": "inline-flex"}, {"display": "inline-flex"}
            return {"display": "none"}, {"display": "none"}

        @app.callback(
            Output("profile-initials", "children"),
            Output("profile-name", "children"),
            Output("profile-email", "children"),
            Output("profile-total-value", "children"),
            Output("profile-pl", "children"),
            Output("profile-stocks-count", "children"),
            Output("profile-pl", "className"),
            Input("global-user-store", "data"),
            Input("trade-holdings-table", "data"),
            prevent_initial_call=False,
        )
        def update_profile_dropdown(user_data, _trade_data):
            del _trade_data

            if not user_data or "user_id" not in user_data:
                return (
                    "GU",
                    "Guest User",
                    "Sign in to unlock workspace",
                    "$0.00",
                    "0.00%",
                    "0",
                    "insight-value",
                )

            user_id = user_data["user_id"]
            email = user_data.get("email", "")

            initials = email[:2].upper() if len(email) >= 2 else "U"
            name = email.split("@")[0].capitalize() if email else "User"

            try:
                cash = self.services.portfolio_repository.get_balance(user_id)
                positions = self.services.portfolio_repository.get_positions(user_id)
            except RuntimeError as exc:
                return (
                    initials,
                    name,
                    f"{email} | {exc}",
                    "Unavailable",
                    "Unavailable",
                    "0",
                    "insight-value",
                )

            total_equity = 0.0
            total_cost_basis = 0.0
            stocks_count = len(positions)
            snapshots = self.services.market_data_service.get_quote_map([pos["symbol"] for pos in positions])

            for pos in positions:
                symbol = pos["symbol"]
                qty = float(pos["quantity"])
                avg_cost = float(pos["avg_cost"])

                live_price = float(snapshots.get(symbol, {}).get("price") or 0.0)
                if live_price <= 0:
                    continue

                total_equity += live_price * qty
                total_cost_basis += avg_cost * qty

            total_value = cash + total_equity
            pl_amount = total_equity - total_cost_basis
            pl_pct = (pl_amount / total_cost_basis * 100) if total_cost_basis > 0 else 0.0

            pl_class = "insight-value positive" if pl_amount >= 0 else "insight-value negative"
            pl_text = f"{'+' if pl_amount > 0 else ''}{pl_pct:.2f}%"

            return (
                initials,
                name,
                email,
                format_currency(total_value, allow_zero=True),
                pl_text,
                str(stocks_count),
                pl_class,
            )
