-- S1-11 phase 1, run as postgres: the new backend user owns the database monitor.
-- Why: a user made with `gcloud sql users create` is in cloudsqlsuperuser, and postgres
-- cannot remove it (no ADMIN OPTION on that group). A role made with SQL is not in it.
\getenv pw_backend PW_BACKEND
CREATE ROLE monitor_backend LOGIN NOCREATEROLE NOCREATEDB PASSWORD :'pw_backend';
-- postgres made the role, so it has ADMIN on it; ALTER ... OWNER also needs SET
GRANT monitor_backend TO postgres WITH SET TRUE;
ALTER DATABASE monitor OWNER TO monitor_backend;
-- temporary: monitor_app needs SET on monitor_backend for REASSIGN OWNED (phase 2)
GRANT monitor_backend TO monitor_app WITH SET TRUE;
\echo '== phase 1 result (expected: owner monitor_backend; f, f)'
select datname, pg_get_userbyid(datdba) as owner from pg_database where datname = 'monitor';
select rolname, rolcreaterole, rolcreatedb from pg_roles where rolname = 'monitor_backend';
