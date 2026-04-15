# Modular Stock Market Dash App (Python + Supabase)

This project is a class-based, modular Dash app for stock visualization and portfolio simulation.

The app now runs in live-only mode:

- Authentication is handled by Supabase Auth.
- Portfolio, watchlist, alerts, and balance operations read/write directly to Supabase tables.
- Market prices and chart data are fetched from live Yahoo Finance endpoints via yfinance.
- No in-memory fallback data path is used for user portfolio state.

## Features

- Supabase authentication (sign up, sign in, sign out)
- User account profile with cash balance
- Live stock quote and historical graph tracker
- Buy/Sell shares with balance calculation
- Portfolio value calculation and allocation chart
- Watchlist management
- Smart alerts (above/below target)
- Clear app sections for Market, Trading, Portfolio, Watchlist, Alerts, Authentication, and Details

## Project Structure

- `app.py` - application entry point
- `src/core` - app host class and DI container
- `src/config` - environment settings
- `src/services` - Supabase and market data services
- `src/repositories` - data access and business operations
- `src/features` - feature modules (each in separate class/module)
- `dbdesign.md` - Supabase schema design and feature mapping

## Live Data Requirements

Before running the app, apply `supabase_setup.sql` in Supabase SQL Editor.

This script creates/updates:

- `profiles`, `portfolios`, `transactions`, `watchlists`, `alerts`
- RLS policies for authenticated users
- `auth.users` -> `profiles` signup trigger (`SECURITY DEFINER`) to avoid profile-creation failures

If Supabase is not configured or DB tables are missing, the app will show explicit errors instead of simulating data.

## Setup

1. Create virtual environment:

```bash
python3 -m venv venv
```

2. Activate it:

```bash
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure environment values:

```bash
cp .env.example .env
# edit .env and set SUPABASE_URL + SUPABASE_ANON_KEY
```

5. Run app:

```bash
python app.py
```

Open browser at `http://127.0.0.1:8050`.

## Re-run

1. Activate virtual environment:

```bash
source venv/bin/activate

```

2. Run app:

```bash
python app.py
```
