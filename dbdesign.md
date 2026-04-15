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

Use the ready-to-run script in `supabase_setup.sql`.

If you are applying manually, ensure these key rules are present:

```sql
alter table public.profiles enable row level security;

create policy "profiles_select_own" on public.profiles
  for select using (auth.uid() = id);

create policy "profiles_insert_own" on public.profiles
  for insert with check (auth.uid() = id);

create policy "profiles_update_own" on public.profiles
  for update using (auth.uid() = id) with check (auth.uid() = id);
```

Use equivalent `auth.uid() = user_id` policies for all other tables.

## Critical Sign-up Trigger Setup

To avoid `Database error saving new user` during sign-up when `profiles` is auto-created,
the trigger function must be `SECURITY DEFINER` and target `public.profiles` safely.

Use this pattern:

```sql
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, balance)
  values (new.id, new.email, 100000)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
```

This is included in `supabase_setup.sql`.

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
