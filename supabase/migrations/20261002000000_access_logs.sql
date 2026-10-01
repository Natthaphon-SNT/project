begin;

create table public.access_logs (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  method text,
  path text,
  status int,
  ip text,
  country text,
  user_agent text,
  user_id text
);
create index access_logs_created_at_idx on public.access_logs (created_at desc);
create index access_logs_ip_idx on public.access_logs (ip);
alter table public.access_logs enable row level security;

-- No policies. Also revoke table/sequence privileges so anon reads fail rather
-- than returning an empty array; only the backend service_role uses REST.
revoke all on table public.access_logs from public, anon, authenticated;
revoke all on sequence public.access_logs_id_seq from public, anon, authenticated;
grant select, insert, delete on table public.access_logs to service_role;
grant usage, select on sequence public.access_logs_id_seq to service_role;

-- Fail this migration rather than silently accepting an insecure table.
do $$
begin
  if not (select relrowsecurity from pg_class
          where oid = 'public.access_logs'::regclass) then
    raise exception 'access_logs must have RLS enabled';
  end if;
  if exists (select 1 from pg_policies
             where schemaname = 'public' and tablename = 'access_logs') then
    raise exception 'access_logs must have no policies';
  end if;
end;
$$;

commit;
