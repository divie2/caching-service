"""Database engine construction, shared by the app and the tests."""

from sqlalchemy import Engine, StaticPool
from sqlmodel import create_engine


def build_engine(database_url: str) -> Engine:
    """Create the engine; SQLite needs extra options because FastAPI uses several threads."""
    if not database_url.startswith("sqlite"):
        return create_engine(database_url)

    connect_args = {"check_same_thread": False}
    if database_url == "sqlite://":
        # An in-memory database lives inside one connection, so every thread must share it.
        return create_engine(database_url, connect_args=connect_args, poolclass=StaticPool)
    return create_engine(database_url, connect_args=connect_args)
