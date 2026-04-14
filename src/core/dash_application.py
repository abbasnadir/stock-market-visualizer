"""Main Dash application class that combines all feature modules."""

from __future__ import annotations

import os

from dash import Dash, Input, Output, dcc, html

from src.core.service_container import ServiceContainer
from src.features.alerts_feature import AlertsFeature
from src.features.auth_feature import AuthFeature
from src.features.market_feature import MarketFeature
from src.features.portfolio_feature import PortfolioFeature
from src.features.profile_feature import ProfileFeature
from src.features.trading_feature import TradingFeature
from src.features.watchlist_feature import WatchlistFeature


class StockDashApplication:
    """Creates one Dash app and mounts all module layouts and callbacks."""

    def __init__(self) -> None:
        self.services = ServiceContainer()
        assets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
        self.app = Dash(__name__, title=self.services.settings.app_title, assets_folder=assets_path)

        self.auth_feature = AuthFeature(self.services)
        self.market_feature = MarketFeature(self.services)
        self.trading_feature = TradingFeature(self.services)
        self.portfolio_feature = PortfolioFeature(self.services)
        self.watchlist_feature = WatchlistFeature(self.services)
        self.alerts_feature = AlertsFeature(self.services)
        self.profile_feature = ProfileFeature(self.services)

        self.features = [
            self.auth_feature,
            self.market_feature,
            self.trading_feature,
            self.portfolio_feature,
            self.watchlist_feature,
            self.alerts_feature,
            self.profile_feature,
        ]

        self.app.layout = self._build_layout()
        self._register_callbacks()

    def _build_layout(self):
        supabase_status = (
            "Supabase connected" if self.services.supabase_service.is_configured else "Supabase pending .env setup"
        )

        return html.Div(
            [
                html.Div(
                    [
                        html.Div("S", className="logo-box"),
                        dcc.Link("OV", href="/", refresh=False, id="nav-overview", className="nav-icon active"),
                        dcc.Link("TR", href="/trading", refresh=False, id="nav-trading", className="nav-icon"),
                        dcc.Link("PF", href="/portfolio", refresh=False, id="nav-portfolio", className="nav-icon"),
                        dcc.Link("WL", href="/watchlist", refresh=False, id="nav-watchlist", className="nav-icon"),
                        dcc.Link("AL", href="/alerts", refresh=False, id="nav-alerts", className="nav-icon"),
                    ],
                    className="left-sidebar",
                ),
                html.Div(
                    [
                        dcc.Location(id="app-location", refresh=False),
                        dcc.Store(id="global-user-store", storage_type="session", data={}),
                        html.Div(id="auth-user-display", style={"display": "none"}),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span("Overview / "),
                                        html.Strong("Market", id="top-breadcrumb"),
                                    ],
                                    className="breadcrumbs",
                                ),
                                self.profile_feature.get_layout(),
                            ],
                            className="top-bar",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [html.Strong("SPY"), html.Span("US Market Index", className="ticker-price")],
                                    className="ticker-item",
                                ),
                                html.Div(
                                    [html.Strong("QQQ"), html.Span("Tech Index", className="ticker-price")],
                                    className="ticker-item",
                                ),
                                html.Div(
                                    [html.Strong("DIA"), html.Span("Blue Chip Index", className="ticker-price")],
                                    className="ticker-item",
                                ),
                                html.Div(
                                    [html.Strong("VIX"), html.Span("Volatility", className="ticker-price")],
                                    className="ticker-item",
                                ),
                                html.Div(
                                    [html.Strong("STATUS"), html.Span(supabase_status, className="ticker-price")],
                                    className="ticker-item",
                                ),
                            ],
                            className="ticker-tape",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            html.Div(
                                                self.market_feature.get_layout(),
                                                className="feature-card market-feature-wrapper",
                                            ),
                                            id="page-overview",
                                            className="page-pane",
                                        ),
                                        html.Div(
                                            html.Div(
                                                self.trading_feature.get_layout(),
                                                className="feature-card secondary-card",
                                            ),
                                            id="page-trading",
                                            className="page-pane",
                                            style={"display": "none"},
                                        ),
                                        html.Div(
                                            html.Div(
                                                self.portfolio_feature.get_layout(),
                                                className="feature-card secondary-card",
                                            ),
                                            id="page-portfolio",
                                            className="page-pane",
                                            style={"display": "none"},
                                        ),
                                        html.Div(
                                            html.Div(
                                                self.watchlist_feature.get_layout(),
                                                className="feature-card secondary-card",
                                            ),
                                            id="page-watchlist",
                                            className="page-pane",
                                            style={"display": "none"},
                                        ),
                                        html.Div(
                                            html.Div(
                                                self.alerts_feature.get_layout(),
                                                className="feature-card secondary-card",
                                            ),
                                            id="page-alerts",
                                            className="page-pane",
                                            style={"display": "none"},
                                        ),
                                    ],
                                    className="market-main",
                                ),
                                html.Div(
                                    [
                                        html.Div(self.auth_feature.get_layout(), className="auth-card"),
                                        html.Div(
                                            [
                                                html.H3("Stock Details"),
                                                html.P("Company profile", id="rs-company-name"),
                                                html.Div(
                                                    [
                                                        html.Span("Company", className="label"),
                                                        html.Span("-", id="rs-company", className="val"),
                                                    ],
                                                    className="detail-row",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Span("Current Price", className="label"),
                                                        html.Span("-", id="rs-price", className="val"),
                                                    ],
                                                    className="detail-row",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Span("Ticker", className="label"),
                                                        html.Span("-", id="rs-ticker", className="val"),
                                                    ],
                                                    className="detail-row",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Span("Change", className="label"),
                                                        html.Span("-", id="rs-change", className="val"),
                                                    ],
                                                    className="detail-row",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Span("Market Cap", className="label"),
                                                        html.Span("-", id="rs-mcap", className="val"),
                                                    ],
                                                    className="detail-row",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Span("Volume", className="label"),
                                                        html.Span("-", id="rs-volume", className="val"),
                                                    ],
                                                    className="detail-row",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Span("PE Ratio", className="label"),
                                                        html.Span("-", id="rs-pe", className="val"),
                                                    ],
                                                    className="detail-row",
                                                ),
                                            ],
                                            className="details-card",
                                        ),
                                    ],
                                    className="right-sidebar",
                                ),
                            ],
                            className="content-scroll-area",
                        ),
                    ],
                    className="main-wrapper",
                ),
            ],
            className="dashboard-layout",
        )

    def _register_layout_callbacks(self) -> None:
        @self.app.callback(
            Output("page-overview", "style"),
            Output("page-trading", "style"),
            Output("page-portfolio", "style"),
            Output("page-watchlist", "style"),
            Output("page-alerts", "style"),
            Output("nav-overview", "className"),
            Output("nav-trading", "className"),
            Output("nav-portfolio", "className"),
            Output("nav-watchlist", "className"),
            Output("nav-alerts", "className"),
            Output("top-breadcrumb", "children"),
            Input("app-location", "pathname"),
        )
        def switch_page(pathname: str | None):
            visible = {"display": "block"}
            hidden = {"display": "none"}

            normalized = (pathname or "/").rstrip("/")
            normalized = normalized if normalized else "/"

            states = {
                "/": [visible, hidden, hidden, hidden, hidden],
                "/trading": [hidden, visible, hidden, hidden, hidden],
                "/portfolio": [hidden, hidden, visible, hidden, hidden],
                "/watchlist": [hidden, hidden, hidden, visible, hidden],
                "/alerts": [hidden, hidden, hidden, hidden, visible],
            }
            labels = {
                "/": "Market",
                "/trading": "Trading",
                "/portfolio": "Portfolio",
                "/watchlist": "Watchlist",
                "/alerts": "Alerts",
            }

            selected_path = normalized if normalized in states else "/"
            page_styles = states[selected_path]
            breadcrumb = labels[selected_path]

            return (
                page_styles[0],
                page_styles[1],
                page_styles[2],
                page_styles[3],
                page_styles[4],
                "nav-icon active" if selected_path == "/" else "nav-icon",
                "nav-icon active" if selected_path == "/trading" else "nav-icon",
                "nav-icon active" if selected_path == "/portfolio" else "nav-icon",
                "nav-icon active" if selected_path == "/watchlist" else "nav-icon",
                "nav-icon active" if selected_path == "/alerts" else "nav-icon",
                breadcrumb,
            )

    def _register_callbacks(self) -> None:
        self._register_layout_callbacks()
        for feature in self.features:
            feature.register_callbacks(self.app)

    def run(self) -> None:
        self.app.run(
            host=self.services.settings.host,
            port=self.services.settings.port,
            debug=self.services.settings.debug,
        )
