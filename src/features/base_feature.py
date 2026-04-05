"""Base class for feature modules."""

from __future__ import annotations

from abc import ABC, abstractmethod

from dash import Dash
from dash.development.base_component import Component

from src.core.service_container import ServiceContainer


class BaseFeature(ABC):
    """Abstract base feature every module extends."""

    def __init__(self, services: ServiceContainer) -> None:
        self.services = services

    @abstractmethod
    def get_layout(self) -> Component:
        """Return the Dash layout fragment for the feature."""

    @abstractmethod
    def register_callbacks(self, app: Dash) -> None:
        """Register all callbacks required for the feature."""
