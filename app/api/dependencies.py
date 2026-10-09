"""Per-request access to the objects the app built once at startup."""

from collections.abc import Iterator

from fastapi import Request
from sqlmodel import Session

from app.transformer import Transformer


def get_session(request: Request) -> Iterator[Session]:
    """Give each request its own session, closed once the response is sent."""
    with Session(request.app.state.engine) as session:
        yield session


def get_transformer(request: Request) -> Transformer:
    transformer: Transformer = request.app.state.transformer
    return transformer
