import os

import pytest
from sqlalchemy import create_engine, inspect, text

from data.postgres import migrate


def test_metadata_migrations_are_idempotent():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    engine = create_engine(url)
    migrate(engine)
    assert migrate(engine) == []
    assert {"workflows", "audit_events", "schema_migrations"}.issubset(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM schema_migrations")).scalar_one() == 4
    engine.dispose()
