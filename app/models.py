"""Database tables for cached transformer results and stored payloads."""

import uuid

from sqlmodel import Field, SQLModel


class TransformCache(SQLModel, table=True):
    """One row per distinct input string, so each string is transformed at most once."""

    input: str = Field(primary_key=True)
    output: str


class Payload(SQLModel, table=True):
    """A stored payload; the output is saved so reads never call the transformer."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Fingerprint of both input lists; unique so an identical request reuses this row.
    input_hash: str = Field(unique=True)
    output: str
