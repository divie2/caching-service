from sqlalchemy import text

from app.db import build_engine


def test_build_engine_connects_to_in_memory_sqlite() -> None:
    engine = build_engine("sqlite://")

    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
