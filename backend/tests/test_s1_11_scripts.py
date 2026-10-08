"""S1-11: static checks of the database account scripts (deploy/sql/s1-11).

The scripts run on the test host VM; this computer cannot run them. These checks make sure
that no password is written in a file and that every shell script stops on the first error.
"""
from __future__ import annotations

import re
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[2] / "deploy" / "sql" / "s1-11"


def test_every_password_comes_from_the_environment():
    for path in FOLDER.glob("*.sql"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"PASSWORD\s+(\S+)", text, flags=re.IGNORECASE):
            assert match.group(1).startswith(":'pw_"), (path.name, match.group(0))
        for variable in re.findall(r":'(pw_\w+)'", text):
            assert f"\\getenv {variable} " in text, (path.name, variable)


def test_shell_scripts_stop_on_errors_and_print_no_password():
    scripts = sorted(FOLDER.glob("*.sh"))
    assert {p.name for p in scripts} >= {"run-sql.sh", "phase0-passwords.sh",
                                         "phase4-switch.sh", "phase4-rollback.sh",
                                         "phase6-cleanup.sh"}
    for path in scripts:
        text = path.read_text(encoding="utf-8")
        assert text.startswith("#!/usr/bin/env bash\n"), path.name
        assert "set -euo pipefail" in text, path.name
        for line in text.splitlines():
            if "echo" in line:
                # no echo of a password file's content or of a password variable
                assert not re.search(r"\$\(\s*(cat|<)[^)]*\.password", line), (path.name, line)
                assert "$PGPASSWORD" not in line and "NEWPW" not in line, (path.name, line)


def test_read_users_cannot_write_and_backend_is_no_admin():
    read = (FOLDER / "phase5-read.sql").read_text(encoding="utf-8")
    assert "INSERT INTO batch_runs" in read and "insufficient_privilege" in read
    phase1 = (FOLDER / "phase1.sql").read_text(encoding="utf-8")
    assert "CREATE ROLE monitor_backend LOGIN NOCREATEROLE NOCREATEDB" in phase1
    assert "ALTER DATABASE monitor OWNER TO monitor_backend" in phase1
    phase3 = (FOLDER / "phase3.sql").read_text(encoding="utf-8")
    assert "REVOKE monitor_backend FROM monitor_app" in phase3
    assert "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO monitor_read" in phase3
