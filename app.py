"""Entrypoint for the modular stock dashboard Dash app."""

from src.core.dash_application import StockDashApplication


if __name__ == "__main__":
    application = StockDashApplication()
    application.run()
