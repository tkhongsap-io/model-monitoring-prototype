-- S1-11 phase 5b, run as each read user: SELECT works; INSERT and CREATE are refused.
\echo '== read user (expected: a count, then two "refused: OK")'
select current_user, count(*) as batch_runs from batch_runs;
DO $$
BEGIN
  INSERT INTO batch_runs DEFAULT VALUES;
  RAISE EXCEPTION 'INSERT WORKED - THIS USER IS NOT READ-ONLY';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'insert refused: OK';
END $$;
DO $$
BEGIN
  CREATE TABLE s1_11_read_check (id int);
  RAISE EXCEPTION 'CREATE WORKED - THIS USER IS NOT READ-ONLY';
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'create refused: OK';
END $$;
