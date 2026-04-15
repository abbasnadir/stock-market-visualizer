"""Main Dash application class that combines all feature modules."""

from __future__ import annotations

import os

from dash import Dash, Input, Output

from src.core.service_container import ServiceContainer
from src.features.alerts_feature import AlertsFeature
from src.features.auth_feature import AuthFeature
from src.features.market_feature import MarketFeature
from src.features.portfolio_feature import PortfolioFeature
from src.features.profile_feature import ProfileFeature
from src.features.trading_feature import TradingFeature
from src.features.watchlist_feature import WatchlistFeature
from src.ui.dashboard_shell import PAGE_CONFIG, build_dashboard_layout


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
            "Supabase live" if self.services.supabase_service.is_configured else "Supabase not configured"
        )
        return build_dashboard_layout(
            market_layout=self.market_feature.get_layout(),
            trading_layout=self.trading_feature.get_layout(),
            portfolio_layout=self.portfolio_feature.get_layout(),
            watchlist_layout=self.watchlist_feature.get_layout(),
            alerts_layout=self.alerts_feature.get_layout(),
            auth_layout=self.auth_feature.get_layout(),
            profile_layout=self.profile_feature.get_layout(),
            supabase_status=supabase_status,
            default_symbol=self.services.settings.default_symbol,
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

            page_paths = [page["path"] for page in PAGE_CONFIG]
            selected_path = normalized if normalized in page_paths else "/"
            page_styles = [visible if page["path"] == selected_path else hidden for page in PAGE_CONFIG]
            breadcrumb = next(page["label"] for page in PAGE_CONFIG if page["path"] == selected_path)
            nav_classes = [
                "nav-link active" if page["path"] == selected_path else "nav-link"
                for page in PAGE_CONFIG
            ]

            return (
                page_styles[0],
                page_styles[1],
                page_styles[2],
                page_styles[3],
                page_styles[4],
                nav_classes[0],
                nav_classes[1],
                nav_classes[2],
                nav_classes[3],
                nav_classes[4],
                breadcrumb,
            )

        @self.app.callback(
            Output("status-market", "children"),
            Output("status-market", "className"),
            Output("status-auth", "children"),
            Output("status-auth", "className"),
            Output("status-trading", "children"),
            Output("status-trading", "className"),
            Output("status-portfolio", "children"),
            Output("status-portfolio", "className"),
            Output("status-watchlist", "children"),
            Output("status-watchlist", "className"),
            Output("status-alerts", "children"),
            Output("status-alerts", "className"),
            Output("status-note", "children"),
            Input("workspace-status-interval", "n_intervals"),
            Input("global-user-store", "data"),
            prevent_initial_call=False,
        )
        def refresh_workspace_status(_, user_store):
            del _

            def badge(label: str, tone: str):
                return label, f"status-badge {tone}"

            user_store = user_store or {}
            user_id = user_store.get("user_id")
            is_logged_in = bool(user_id)
            is_supabase_ready = self.services.supabase_service.is_configured

            market_price = self.services.market_data_service.get_latest_price(self.services.settings.default_symbol)
            market_status = badge("Live" if market_price > 0 else "Unavailable", "live" if market_price > 0 else "error")

            if not is_supabase_ready:
                note = "Supabase is not configured. Public market view works, but account features are unavailable."
                auth_status = badge("Unavailable", "off")
                restricted_status = badge("Unavailable", "off")
                return (
                    market_status[0],
                    market_status[1],
                    auth_status[0],
                    auth_status[1],
                    restricted_status[0],
                    restricted_status[1],
                    restricted_status[0],
                    restricted_status[1],
                    restricted_status[0],
                    restricted_status[1],
                    restricted_status[0],
                    restricted_status[1],
                    note,
                )

            auth_status = badge("Live" if is_logged_in else "Login Required", "live" if is_logged_in else "login")

            if not is_logged_in:
                note = "Market and auth are ready. Sign in to enable trading, portfolio, watchlist, and alerts."
                restricted_status = badge("Login Required", "login")
                return (
                    market_status[0],
                    market_status[1],
                    auth_status[0],
                    auth_status[1],
                    restricted_status[0],
                    restricted_status[1],
                    restricted_status[0],
                    restricted_status[1],
                    restricted_status[0],
                    restricted_status[1],
                    restricted_status[0],
                    restricted_status[1],
                    note,
                )

            trading_status = badge("Live", "live")
            portfolio_status = badge("Live", "live")
            watchlist_status = badge("Live", "live")
            alerts_status = badge("Live", "live")
            errors: list[str] = []

            try:
                self.services.portfolio_repository.get_balance(user_id)
                self.services.portfolio_repository.get_transactions(user_id, limit=1)
            except RuntimeError:
                trading_status = badge("Issue", "error")
                errors.append("trading")

            try:
                self.services.portfolio_repository.get_positions(user_id)
            except RuntimeError:
                portfolio_status = badge("Issue", "error")
                errors.append("portfolio")

            try:
                self.services.portfolio_repository.get_watchlist(user_id)
            except RuntimeError:
                watchlist_status = badge("Issue", "error")
                errors.append("watchlist")

            try:
                self.services.portfolio_repository.get_alerts(user_id)
            except RuntimeError:
                alerts_status = badge("Issue", "error")
                errors.append("alerts")

            note = "All account features are connected and using live data."
            if errors:
                note = (
                    "Some account features report backend issues: "
                    f"{', '.join(sorted(set(errors)))}. Check Supabase tables/RLS and credentials."
                )

            return (
                market_status[0],
                market_status[1],
                auth_status[0],
                auth_status[1],
                trading_status[0],
                trading_status[1],
                portfolio_status[0],
                portfolio_status[1],
                watchlist_status[0],
                watchlist_status[1],
                alerts_status[0],
                alerts_status[1],
                note,
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
