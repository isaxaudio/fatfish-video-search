-- ============================================================
-- VIDEO SEARCH — PRODUCTION SCHEMA
-- Paste this entire file into Supabase SQL Editor and Run.
-- Safe to re-run: drops and recreates cleanly.
-- ============================================================

-- 0. Extensions
create extension if not exists pg_trgm;

-- 1. Status enum
do $$ begin
  create type video_status as enum (
    'editing',    -- being cut by editor
    'ready',      -- approved, waiting for upload
    'uploading',  -- currently being uploaded to SmugMug
    'uploaded',   -- in SmugMug, URLs captured, not yet searchable
    'live',       -- active in public search
    'hidden'      -- manually suppressed
  );
exception
  when duplicate_object then null;
end $$;

-- 2. Drop and recreate table
drop table if exists public.videos cascade;

create table public.videos (
  id             uuid primary key default gen_random_uuid(),
  student_name   text not null,
  search_name    text generated always as (lower(student_name)) stored,
  first_name     text,
  last_name      text,
  school_name    text,
  event_name     text,
  event_year     smallint,
  program_name   text,
  degree_name    text,
  thumbnail_url  text,
  smugmug_url    text,
  download_url   text,
  status         video_status not null default 'editing',
  is_active      boolean not null default false,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

-- 3. Indexes
create index idx_videos_search_name      on public.videos (search_name);
create index idx_videos_search_name_trgm on public.videos using gin (search_name gin_trgm_ops);
create index idx_videos_status           on public.videos (status);
create index idx_videos_school           on public.videos (school_name);
create index idx_videos_event_year       on public.videos (event_name, event_year);
create index idx_videos_is_active        on public.videos (is_active);

-- 4. Auto-update updated_at
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_videos_updated_at on public.videos;
create trigger trg_videos_updated_at
  before update on public.videos
  for each row execute procedure public.set_updated_at();

-- 5. Auto-sync is_active when status changes to live or hidden
create or replace function public.sync_is_active()
returns trigger language plpgsql as $$
begin
  if new.status = 'live' then
    new.is_active = true;
  elsif new.status = 'hidden' then
    new.is_active = false;
  end if;
  return new;
end;
$$;

drop trigger if exists trg_videos_sync_active on public.videos;
create trigger trg_videos_sync_active
  before insert or update on public.videos
  for each row execute procedure public.sync_is_active();

-- 6. Row Level Security
alter table public.videos enable row level security;

drop policy if exists "Public can read active videos" on public.videos;
create policy "Public can read active videos"
  on public.videos
  for select
  using (is_active = true);

-- Done. Run SELECT * FROM public.videos LIMIT 1; to verify table exists.
