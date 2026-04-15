-- Supabase setup script for Stock Dash App
-- Run this in Supabase SQL Editor as a project admin.

begin;

-- Core tables
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique,
  balance numeric(14,2) not null default 100000,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.portfolios (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text not null,
  quantity numeric(16,4) not null default 0,
  avg_cost numeric(14,4) not null default 0,
  updated_at timestamptz not null default now(),
  unique(user_id, symbol)
);

create table if not exists public.transactions (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  action text not null check (action in ('BUY', 'SELL')),
  symbol text not null,
  quantity numeric(16,4) not null,
  price numeric(14,4) not null,
  timestamp timestamptz not null default now()
);

create table if not exists public.watchlists (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text not null,
  created_at timestamptz not null default now(),
  unique(user_id, symbol)
);

create table if not exists public.alerts (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text not null,
  condition text not null check (condition in ('above', 'below')),
  target_price numeric(14,4) not null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

-- Keep updated_at fields current
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_profiles_updated_at on public.profiles;
create trigger trg_profiles_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

drop trigger if exists trg_portfolios_updated_at on public.portfolios;
create trigger trg_portfolios_updated_at
before update on public.portfolios
for each row execute function public.set_updated_at();

-- Auto-create profile when auth user is created.
-- SECURITY DEFINER is important so auth-side insert is not blocked by user RLS.
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

-- RLS
alter table public.profiles enable row level security;
alter table public.portfolios enable row level security;
alter table public.transactions enable row level security;
alter table public.watchlists enable row level security;
alter table public.alerts enable row level security;

-- Profiles policies
drop policy if exists profiles_select_own on public.profiles;
create policy profiles_select_own
  on public.profiles for select
  using (auth.uid() = id);

drop policy if exists profiles_insert_own on public.profiles;
create policy profiles_insert_own
  on public.profiles for insert
  with check (auth.uid() = id);

drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own
  on public.profiles for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

drop policy if exists profiles_delete_own on public.profiles;
create policy profiles_delete_own
  on public.profiles for delete
  using (auth.uid() = id);

-- Portfolio policies
drop policy if exists portfolios_select_own on public.portfolios;
create policy portfolios_select_own
  on public.portfolios for select
  using (auth.uid() = user_id);

drop policy if exists portfolios_insert_own on public.portfolios;
create policy portfolios_insert_own
  on public.portfolios for insert
  with check (auth.uid() = user_id);

drop policy if exists portfolios_update_own on public.portfolios;
create policy portfolios_update_own
  on public.portfolios for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists portfolios_delete_own on public.portfolios;
create policy portfolios_delete_own
  on public.portfolios for delete
  using (auth.uid() = user_id);

-- Transactions policies
drop policy if exists transactions_select_own on public.transactions;
create policy transactions_select_own
  on public.transactions for select
  using (auth.uid() = user_id);

drop policy if exists transactions_insert_own on public.transactions;
create policy transactions_insert_own
  on public.transactions for insert
  with check (auth.uid() = user_id);

drop policy if exists transactions_update_own on public.transactions;
create policy transactions_update_own
  on public.transactions for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists transactions_delete_own on public.transactions;
create policy transactions_delete_own
  on public.transactions for delete
  using (auth.uid() = user_id);

-- Watchlist policies
drop policy if exists watchlists_select_own on public.watchlists;
create policy watchlists_select_own
  on public.watchlists for select
  using (auth.uid() = user_id);

drop policy if exists watchlists_insert_own on public.watchlists;
create policy watchlists_insert_own
  on public.watchlists for insert
  with check (auth.uid() = user_id);

drop policy if exists watchlists_update_own on public.watchlists;
create policy watchlists_update_own
  on public.watchlists for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists watchlists_delete_own on public.watchlists;
create policy watchlists_delete_own
  on public.watchlists for delete
  using (auth.uid() = user_id);

-- Alerts policies
drop policy if exists alerts_select_own on public.alerts;
create policy alerts_select_own
  on public.alerts for select
  using (auth.uid() = user_id);

drop policy if exists alerts_insert_own on public.alerts;
create policy alerts_insert_own
  on public.alerts for insert
  with check (auth.uid() = user_id);

drop policy if exists alerts_update_own on public.alerts;
create policy alerts_update_own
  on public.alerts for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists alerts_delete_own on public.alerts;
create policy alerts_delete_own
  on public.alerts for delete
  using (auth.uid() = user_id);

-- Privileges
grant usage on schema public to authenticated;
grant select, insert, update, delete on table
  public.profiles,
  public.portfolios,
  public.transactions,
  public.watchlists,
  public.alerts
to authenticated;
grant usage, select on all sequences in schema public to authenticated;

commit;
