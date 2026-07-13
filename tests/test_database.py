from compliance_doc_assistant.database import _with_psycopg_driver


def test_rewrites_bare_postgres_scheme() -> None:
    assert _with_psycopg_driver("postgres://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )


def test_rewrites_bare_postgresql_scheme() -> None:
    assert _with_psycopg_driver("postgresql://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )


def test_leaves_explicit_driver_scheme_unchanged() -> None:
    url = "postgresql+psycopg://user:pass@host/db"
    assert _with_psycopg_driver(url) == url


def test_leaves_other_schemes_unchanged() -> None:
    assert _with_psycopg_driver("sqlite:///./test.db") == "sqlite:///./test.db"
