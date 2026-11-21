"""Create a demo account with a small paper-trading portfolio, watchlist and alerts.

Uses the app's own services, so orders go through PortfolioRepository at live
Yahoo Finance prices. Meant for a local Supabase stand-in (see local-supabase/).

    python scripts/seed_demo.py
"""

from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.service_container import ServiceContainer  # noqa: E402

DEMO_EMAIL = os.getenv("DEMO_EMAIL", "demo@example.com")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo-password-123")
ORDERS = [("AAPL", 10), ("MSFT", 6), ("NVDA", 12), ("JPM", 8)]
WATCHLIST = ["AMZN", "GOOGL", "TSLA"]


def main() -> int:
    services = ServiceContainer()
    auth = services.supabase_service
    repo = services.portfolio_repository
    market = services.market_data_service

    if not auth.is_configured:
        print("Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.")
        return 1

    # The first sign-in is expected to fail on a fresh database; skip its logged traceback.
    logging.getLogger("src.services.supabase_service").disabled = True
    result = auth.sign_in(DEMO_EMAIL, DEMO_PASSWORD)
    if not result.success:
        result = auth.sign_up(DEMO_EMAIL, DEMO_PASSWORD)
    logging.getLogger("src.services.supabase_service").disabled = False
    print(f"auth: {result.message}")
    session = result.data or {}
    if not session.get("access_token"):
        print("Could not get a signed-in session.")
        return 1
    user_id = session["user_id"]
    repo = repo.for_session(session)
    print(repo.ensure_user_profile(user_id, email=DEMO_EMAIL).message)

    held = {p["symbol"] for p in repo.get_positions(user_id)}
    for symbol, quantity in ORDERS:
        if symbol in held:
            print(f"skip {symbol}: already held")
            continue
        price = market.get_latest_price(symbol)
        if price <= 0:
            print(f"skip {symbol}: no live price")
            continue
        print(repo.buy_stock(user_id, symbol, quantity, price).message)

    for symbol in WATCHLIST:
        print(repo.add_to_watchlist(user_id, symbol).message)

    if not repo.get_alerts(user_id):
        for symbol, factor, condition in (("AAPL", 1.05, "above"), ("TSLA", 0.9, "below")):
            price = market.get_latest_price(symbol)
            if price > 0:
                print(repo.add_alert(user_id, symbol, round(price * factor, 2), condition).message)

    print(f"cash balance: ${repo.get_balance(user_id):,.2f}")
    print(f"sign in with {DEMO_EMAIL} / {DEMO_PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
