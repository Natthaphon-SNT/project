-- Run with Supabase SQL Editor / a trusted administrative connection.

-- RLS must be true; policy_count must be 0.
select c.relrowsecurity as rls_enabled,
       (select count(*) from pg_policies
        where schemaname = 'public' and tablename = 'access_logs') as policy_count
from pg_class c
where c.oid = 'public.access_logs'::regclass;

-- All anon/authenticated privileges below must be false.
select role_name,
       has_table_privilege(role_name, 'public.access_logs', 'SELECT') as can_read,
       has_table_privilege(role_name, 'public.access_logs', 'INSERT') as can_write
from (values ('anon'), ('authenticated')) as roles(role_name);

-- Latest requests.
select id, created_at, method, path, status, ip, country, user_agent, user_id
from public.access_logs
order by created_at desc, id desc
limit 100;

-- IPs with repeated 401/403 responses in the last 7 days.
select ip, count(*) as denied_requests,
       count(*) filter (where status = 401) as unauthorized,
       count(*) filter (where status = 403) as forbidden,
       max(created_at) as last_seen
from public.access_logs
where created_at >= now() - interval '7 days'
  and status in (401, 403)
group by ip
order by denied_requests desc, last_seen desc;

-- Successful admin APIs, including admin actions outside the /api/admin prefix.
select created_at, method, path, status, ip, country, user_agent, user_id
from public.access_logs
where status = 200 and (
  path like '/api/admin/%' or path = '/api/admin'
  or path like '/admin/%' or path = '/admin'
  or path = '/api/spec-history/all'
  or (method = 'POST' and path = '/api/scrape')
  or (method in ('POST', 'PUT', 'PATCH', 'DELETE') and (
    path in ('/api/products', '/api/promotions')
    or path like '/api/products/%' or path like '/api/promotions/%'
  ))
)
order by created_at desc;

-- Retention: execute separately after reviewing the affected count.
select count(*) as older_than_90_days
from public.access_logs where created_at < now() - interval '90 days';
delete from public.access_logs where created_at < now() - interval '90 days';
