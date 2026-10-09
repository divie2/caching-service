"""Application factory: wires settings, database and transformer together at startup."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import SQLModel

from app.api.routes import router
from app.config import Settings
from app.db import build_engine
from app.transformer import make_transformer


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app; tests pass their own settings instead of reading the environment."""
    resolved = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        engine = build_engine(resolved.database_url)
        # No migrations tool: tables are created at startup (a documented shortcut).
        SQLModel.metadata.create_all(engine)
        app.state.engine = engine
        app.state.transformer = make_transformer(resolved.transformer_delay_seconds)
        yield
        engine.dispose()

    app = FastAPI(title="Caching service", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
