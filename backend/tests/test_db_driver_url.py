"""S1-07: the driver URL rule is shared by the backend and the trace check tool."""
from app import db


def test_postgres_urls_select_psycopg3():
    assert db.driver_url("postgres://u:p@h:5432/d") == "postgresql+psycopg://u:p@h:5432/d"
    assert db.driver_url("postgresql://u:p@h/d?sslmode=verify-ca") == \
        "postgresql+psycopg://u:p@h/d?sslmode=verify-ca"


def test_other_urls_do_not_change():
    assert db.driver_url("postgresql+psycopg://u@h/d") == "postgresql+psycopg://u@h/d"
    assert db.driver_url("sqlite:///x.db") == "sqlite:///x.db"
