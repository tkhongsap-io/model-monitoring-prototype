-- S1-11 phase 2, run as monitor_app: give every object of monitor_app to monitor_backend.
REASSIGN OWNED BY monitor_app TO monitor_backend;
\echo '== phase 2 result (expected: only monitor_backend; 0 objects left)'
select tableowner, count(*) as tables from pg_tables where schemaname = 'public' group by tableowner;
select count(*) as objects_still_owned_by_monitor_app
from pg_class where relowner = (select oid from pg_roles where rolname = 'monitor_app');
