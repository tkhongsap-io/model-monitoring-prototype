-- S1-11 phase 5a, run as monitor_backend: it can write and migrate, and it has no admin rights.
\echo '== monitor_backend (expected: f, f, f; create and drop work)'
select current_user,
       pg_has_role(current_user, 'cloudsqlsuperuser', 'MEMBER') as in_cloudsqlsuperuser,
       (select rolcreaterole from pg_roles where rolname = current_user) as createrole,
       (select rolcreatedb from pg_roles where rolname = current_user) as createdb;
CREATE TABLE s1_11_migration_check (id int);
DROP TABLE s1_11_migration_check;
select count(*) as batch_runs from batch_runs;
\echo 'monitor_backend: OK'
