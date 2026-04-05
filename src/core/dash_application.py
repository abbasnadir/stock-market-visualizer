"""Main Dash application class that combines all feature modules."""

from __future__ import annotations

from dash import Dash, dcc, html

from src.core.service_container import ServiceContainer
from src.features.alerts_feature import AlertsFeature
from src.features.auth_feature import AuthFeature
from src.features.market_feature import MarketFeature
from src.features.portfolio_feature import PortfolioFeature
from src.features.trading_feature import TradingFeature
from src.features.watchlist_feature import WatchlistFeature


class StockDashApplication:
    """Creates one Dash app and mounts all module layouts and callbacks."""

    def __init__(self) -> None:
        self.services = ServiceContainer()
        self.app = Dash(__name__, title=self.services.settings.app_title)

        self.features = [
            AuthFeature(self.services),
            MarketFeature(self.services),
            TradingFeature(self.services),
            PortfolioFeature(self.services),
            WatchlistFeature(self.services),
            AlertsFeature(self.services),
        ]

        self.app.layout = self._build_layout()
        self._register_callbacks()

    def _build_layout(self):
        sections = []
        for feature in self.features:
            sections.append(
                html.Div(
                    feature.get_layout(),
                    className="feature-card",
                )
            )

        supabase_status = (
            "Supabase connected" if self.services.supabase_service.is_configured else "Supabase pending .env setup"
        )

        return html.Div(
            [
                dcc.Store(id="global-user-store", storage_type="session", data={}),
                html.Header(
                    [
                        html.H1(self.services.settings.app_title),
                        html.P(
                            "Single-host Dash app with modular OOP architecture, Supabase auth, trading, portfolio, watchlist, and alerts."
                        ),
                        html.P(f"Data/Auth Status: {supabase_status}", className="status-text"),
                        html.P("Current user: not signed in", id="auth-user-display"),
                    ],
                    className="app-header",
                ),
                html.Main(sections, className="feature-grid"),
            ],
            className="page",
        )

    def _register_callbacks(self) -> None:
        for feature in self.features:
            feature.register_callbacks(self.app)

    def run(self) -> None:
        self.app.run(
            host=self.services.settings.host,
            port=self.services.settings.port,
            debug=self.services.settings.debug,
        )
