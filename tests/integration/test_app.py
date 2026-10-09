from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.config import Settings
from app.main import create_app


def test_app_creates_tables_on_startup() -> None:
    app = create_app(Settings(database_url="sqlite://"))

    with TestClient(app):
        table_names = inspect(app.state.engine).get_table_names()

    assert sorted(table_names) == ["payload", "transformcache"]
