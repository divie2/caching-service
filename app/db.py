"""Database engine construction, shared by the app and the tests."""

from typing import Any

from sqlalchemy import Engine
from sqlmodel import create_engine


def build_engine(database_url: str) -> Engine:
    """Create the engine; SQLite needs extra options because FastAPI uses several threads."""
    connect_args: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args)
