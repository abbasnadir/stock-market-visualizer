"""Dependency container for creating and sharing service instances."""

from __future__ import annotations

from src.config.settings import AppSettings
from src.repositories.portfolio_repository import PortfolioRepository
from src.services.market_data_service import MarketDataService
from src.services.supabase_service import SupabaseService


class ServiceContainer:
    """Creates all core services once and shares them across feature modules."""

    def __init__(self) -> None:
        self.settings = AppSettings.from_env()
        self.supabase_service = SupabaseService(self.settings)
        self.market_data_service = MarketDataService()
        self.portfolio_repository = PortfolioRepository(
            supabase_service=self.supabase_service,
            default_cash_balance=self.settings.default_cash_balance,
        )
