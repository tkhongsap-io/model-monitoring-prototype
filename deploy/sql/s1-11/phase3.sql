-- S1-11 phase 3, run as postgres: read-only users through one group role.
\getenv pw_readonly PW_READONLY
\getenv pw_itthisak PW_DEV_ITTHISAK
\getenv pw_prakasit PW_DEV_PRAKASIT
REVOKE monitor_backend FROM monitor_app;
CREATE ROLE monitor_read NOLOGIN;
CREATE ROLE monitor_readonly LOGIN NOCREATEROLE NOCREATEDB PASSWORD :'pw_readonly' IN ROLE monitor_read;
CREATE ROLE dev_itthisak LOGIN NOCREATEROLE NOCREATEDB PASSWORD :'pw_itthisak' IN ROLE monitor_read;
CREATE ROLE dev_prakasit LOGIN NOCREATEROLE NOCREATEDB PASSWORD :'pw_prakasit' IN ROLE monitor_read;
GRANT CONNECT ON DATABASE monitor TO monitor_read;
-- grants on the objects of monitor_backend are made as monitor_backend (the owner)
SET ROLE monitor_backend;
GRANT USAGE ON SCHEMA public TO monitor_read;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO monitor_read;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO monitor_read;
-- also for the tables that later migrations create
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO monitor_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO monitor_read;
RESET ROLE;
\echo '== phase 3 result (expected: no CREATEROLE/CREATEDB; monitor_read cannot log in)'
select rolname, rolcreaterole, rolcreatedb, rolcanlogin from pg_roles
where rolname in ('monitor_backend', 'monitor_read', 'monitor_readonly', 'dev_itthisak', 'dev_prakasit')
order by 1;
