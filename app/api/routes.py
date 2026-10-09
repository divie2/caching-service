"""HTTP endpoints: turn requests into service calls, and results into status codes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app.api.dependencies import get_session, get_transformer
from app.models import Payload
from app.schemas import PayloadCreate, PayloadCreated, PayloadOutput
from app.services.payload import create_payload
from app.transformer import Transformer

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]
TransformerDep = Annotated[Transformer, Depends(get_transformer)]


@router.post("/payload", status_code=status.HTTP_201_CREATED)
def post_payload(
    body: PayloadCreate, response: Response, session: SessionDep, transformer: TransformerDep
) -> PayloadCreated:
    payload, created = create_payload(session, body.list_1, body.list_2, transformer)
    if not created:
        response.status_code = status.HTTP_200_OK
    return PayloadCreated(id=payload.id)


@router.get("/payload/{payload_id}")
def get_payload(payload_id: uuid.UUID, session: SessionDep) -> PayloadOutput:
    payload = session.get(Payload, payload_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payload not found")
    return PayloadOutput(output=payload.output)
