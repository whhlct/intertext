from app.db.session import engine


def test_database_engine_uses_postgresql() -> None:
    assert engine.url.get_backend_name() == "postgresql"
    assert engine.url.get_driver_name() == "psycopg"

