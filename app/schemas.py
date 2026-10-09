"""Request and response bodies for the HTTP API."""

import uuid
from typing import Self

from pydantic import BaseModel, model_validator


class PayloadCreate(BaseModel):
    list_1: list[str]
    list_2: list[str]

    @model_validator(mode="after")
    def lists_have_equal_length(self) -> Self:
        # Interleaving pairs items by position, so unequal lists have no defined output.
        if len(self.list_1) != len(self.list_2):
            raise ValueError("list_1 and list_2 must have the same length")
        return self


class PayloadCreated(BaseModel):
    id: uuid.UUID


class PayloadOutput(BaseModel):
    output: str
