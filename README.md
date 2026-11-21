# Signal Market: stock charts and paper trading (Python + Dash + Supabase)

A Dash web app for looking up US stocks and practising trades with play money. Market data comes live from Yahoo Finance through `yfinance`; accounts, cash balances, holdings, the trade ledger, watchlists and price alerts are stored in Supabase (Auth + Postgres with row-level security).

![Buying 4 AMZN shares at the live price on the Trading page, then opening the Portfolio page, which already shows the new position and cash](docs/demo/paper-trade.gif)

*Recorded locally against a local Supabase stand-in (`local-supabase/`) with a demo account created by `scripts/seed_demo.py`. Prices are live Yahoo Finance quotes at the time of recording.*

## Features

- **Market overview** (works without signing in): quote with day change, market cap, volume, shares outstanding, P/E, and a closing-price chart over 1 month to 2 years (Plotly).
- **Accounts**: sign up, log in and log out with Supabase Auth. A new account starts with $100,000 of paper cash (`DEFAULT_CASH_BALANCE`).
- **Trading**: buy or sell shares at the latest Yahoo Finance price. Buys are rejected if cash is short, sells if you don't hold enough shares. Each order updates the position (with a running average cost), the cash balance and the transaction ledger.
- **Portfolio**: total value, cash, invested amount, a cash and holdings donut chart, and per-position weight and unrealised P/L.
- **Watchlist**: add and remove tickers, with current price and day change.
- **Price alerts**: "above" or "below" rules per ticker. "Check Alerts" compares them with live prices and lists the ones that have triggered.
- **Feature status panel**: shows whether market data, auth and each account feature are reachable, refreshed every 45 seconds.

| Market overview | Portfolio |
| --- | --- |
| ![Market overview with AAPL quote, key figures and one-year price chart](docs/demo/market.png) | ![Portfolio analytics with summary figures and allocation donut](docs/demo/portfolio.png) |

![Price alerts table with one above and one below rule](docs/demo/alerts.png)

*Screenshots recorded locally at 1440×960 with seed data and live Yahoo Finance prices.*

## How it works

- `app.py` builds `StockDashApplication` (`src/core/dash_application.py`), which creates one Dash app and mounts seven feature classes from `src/features/` (auth, market, trading, portfolio, watchlist, alerts, profile). Each feature supplies its layout and registers its own callbacks.
- `src/core/service_container.py` creates the shared services once: settings from environment variables, `SupabaseService` (auth calls and per-user clients), `MarketDataService` (yfinance) and `PortfolioRepository` (all table reads and writes).
- The five pages (`/`, `/trading`, `/portfolio`, `/watchlist`, `/alerts`) are all in one layout. A callback on the URL shows one pane and hides the rest, so moving between pages does not reload data; the portfolio view refreshes on login, after each trade, and with "Refresh Analytics".
- After login the user id, email and Supabase access and refresh tokens go into a session-scoped `dcc.Store` in the browser. Feature callbacks read them from there and stay locked until they are set. Each callback queries Supabase with a client built from that browser's access token (`PortfolioRepository.for_session`), so row-level security applies to the right user and the server keeps no login state of its own. The token is renewed when less than 10 minutes remain (checked on page load and every 5 minutes); if renewal fails, the browser is signed out.
- Buys and sells are done in `PortfolioRepository.buy_stock` / `sell_stock` as separate writes (position upsert, balance update, ledger insert), not in a single database transaction.
- `supabase_setup.sql` creates the five tables (`profiles`, `portfolios`, `transactions`, `watchlists`, `alerts`), turns on RLS with "own rows only" policies, and adds a trigger that creates a profile row when an auth user is created. `dbdesign.md` describes the schema.

## Tech stack

Python (run here with 3.12), Dash 4 and Plotly, pandas, yfinance, supabase-py 2.22, python-dotenv. Database and auth: Supabase (Postgres + GoTrue + PostgREST).

## Run it locally

You need Python 3.10+ and either a Supabase project or Docker for the local stand-in.

### 1. Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Database and auth

**Option A, hosted Supabase:** create a project, run `supabase_setup.sql` in the SQL Editor, and copy the project URL and anon key into `.env` (see below). If email confirmation is on, new users must confirm before they can log in.

**Option B, local stand-in (what the demos above used):** `local-supabase/docker-compose.yml` runs Postgres, Supabase Auth and PostgREST behind an nginx gateway on port 54321, and applies `supabase_setup.sql` once Auth is up. Email confirmation is off.

```bash
cd local-supabase
docker compose up -d
cd ..
```

Then use these values (the anon key is the public demo key that the Supabase CLI uses for local development; it only works against this local stack):

```bash
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
```

Stop it with `docker compose down -v` (in `local-supabase/`).

### 3. Configure and seed

```bash
cp .env.example .env    # then set SUPABASE_URL and SUPABASE_ANON_KEY
python scripts/seed_demo.py
```

The seed script creates `demo@example.com` / `demo-password-123`, buys a few positions through the app's own `PortfolioRepository` at live prices, and adds a watchlist and two alerts. Output from the run used for the demos:

```text
auth: Sign-up successful. Check your mailbox if email confirmation is enabled.
Profile synced with Supabase.
Bought 10 share(s) of AAPL at $342.56.
Bought 6 share(s) of MSFT at $484.52.
Bought 12 share(s) of NVDA at $125.53.
Bought 8 share(s) of JPM at $310.53.
Added AMZN to watchlist.
Added GOOGL to watchlist.
Added TSLA to watchlist.
Alert created for AAPL.
Alert created for TSLA.
cash balance: $89,676.68
sign in with demo@example.com / demo-password-123
```

### 4. Start the app

```bash
python app.py
```

Open `http://127.0.0.1:8050` and sign in from the Account panel. The layout puts the account panel beside the page content at widths above 1280 px and below it on narrower screens.

### Environment variables

| Name | Purpose |
| --- | --- |
| `SUPABASE_URL` | Supabase project URL (or the local stand-in) |
| `SUPABASE_ANON_KEY` | Supabase anon (public) key |
| `APP_TITLE` | Browser tab title |
| `HOST`, `PORT` | Address for the Dash server (default `127.0.0.1:8050`) |
| `DEBUG` | `true` turns on Dash debug mode and dev tools |
| `DEFAULT_SYMBOL` | Ticker shown on first load (default `AAPL`) |
| `DEFAULT_CASH_BALANCE` | Starting paper cash for a profile (default `100000`) |

Without Supabase settings the market overview still works and the account features show as unavailable.

There are no automated tests in this repo. The session handling was checked with Playwright: two users signed in from separate browser contexts each saw only their own cash and holdings, a third browser that never signed in stayed signed out with trading locked, the seeded account kept the cash the seed script left when it logged in again, and a renewed token kept working after a page reload.

## Project structure

```text
app.py                      entry point
assets/styles.css           all styling
src/
  config/settings.py        AppSettings from environment variables
  core/dash_application.py  builds the app, page switching, feature status panel
  core/service_container.py creates and shares services
  services/market_data_service.py   yfinance quotes, metadata, history
  services/supabase_service.py      Supabase client and auth
  repositories/portfolio_repository.py  balances, positions, ledger, watchlist, alerts
  features/                 one class per feature (layout + callbacks)
  ui/                       dashboard shell and number formatting
supabase_setup.sql          tables, RLS policies, signup trigger, grants
dbdesign.md                 schema notes
local-supabase/             docker compose stand-in for local development
scripts/seed_demo.py        demo account and sample portfolio
```

There is no license file in this repo.
