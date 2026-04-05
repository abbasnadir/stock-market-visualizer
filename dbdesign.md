# Stock Dash App - Supabase DB Design

## Overview

This app is modular and class-based, and uses a single Dash host application that combines:

- User Authentication
- User Account Management
- Share Price Fetch/API Data Source
- Buy/Sell Shares with Balance Calculation
- Portfolio Value Calculation
- Stock Value Graph and Tracker
- Watchlist
- Smart Alerts
- User Data Storage

The database is designed for Supabase Postgres and assumes authentication is handled by `auth.users`.

## Entity Relationship Summary

- One `auth.users` row can have one `profiles` row.
- One user can have many `portfolios` rows (one per symbol).
- One user can have many `transactions` rows.
- One user can have many `watchlists` rows.
- One user can have many `alerts` rows.

## SQL Schema

```sql
-- User profile and account balance storage
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique,
  balance numeric(14,2) not null default 100000,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Current holdings per symbol
create table if not exists public.portfolios (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text not null,
  quantity numeric(16,4) not null default 0,
  avg_cost numeric(14,4) not null default 0,
  updated_at timestamptz not null default now(),
  unique(user_id, symbol)
);

-- Buy/Sell transaction ledger
create table if not exists public.transactions (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  action text not null check (action in ('BUY', 'SELL')),
  symbol text not null,
  quantity numeric(16,4) not null,
  price numeric(14,4) not null,
  timestamp timestamptz not null default now()
);

-- Saved symbols to monitor
create table if not exists public.watchlists (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text not null,
  created_at timestamptz not null default now(),
  unique(user_id, symbol)
);

-- Price alert rules
create table if not exists public.alerts (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text not null,
  condition text not null check (condition in ('above', 'below')),
  target_price numeric(14,4) not null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);
```

## Recommended Row Level Security (RLS)

Enable RLS for all user-owned tables (`profiles`, `portfolios`, `transactions`, `watchlists`, `alerts`).

Policy pattern for each table:

```sql
alter table public.profiles enable row level security;
create policy "users_own_profile" on public.profiles
  for all using (auth.uid() = id) with check (auth.uid() = id);
```

Use equivalent `auth.uid() = user_id` policies for all other tables.

## Feature to Table Mapping

- User Authentication: `auth.users` (Supabase Auth)
- User Account Management: `profiles`
- User Data Storage: `profiles`, `portfolios`, `transactions`, `watchlists`, `alerts`
- Buy/Sell Share and Balance Calculation: `profiles`, `portfolios`, `transactions`
- Portfolio Value Calculation: `profiles`, `portfolios` + market API
- Stock Value Graph and Tracker: market API (Yahoo Finance) + optional local caching
- Watchlist: `watchlists`
- Smart Alerts: `alerts`

## Optional Enhancements

- Add `price_cache` table to store fetched intraday snapshots.
- Add `notification_logs` table for alert delivery history.
- Add DB triggers to update `updated_at` columns automatically.
