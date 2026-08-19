import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import DatabaseSession
from app.core.exceptions import InvalidRequestError, ResourceNotFoundError
from app.schemas.library import TextSummary, VersionSummary
from app.schemas.references import ReferenceResolution
from app.schemas.structure import StructureNodeSummary
from app.services.library import list_texts, list_versions
from app.services.references import get_reference_resolution
from app.services.structure import list_structure

router = APIRouter(prefix="/api/v1/texts", tags=["texts"])


@router.get("", response_model=list[TextSummary])
def get_texts(session: DatabaseSession) -> list[TextSummary]:
    return list_texts(session)


@router.get("/{text_slug}/versions", response_model=list[VersionSummary])
def get_versions(text_slug: str, session: DatabaseSession) -> list[VersionSummary]:
    try:
        return list_versions(session, text_slug)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{text_slug}/structure", response_model=list[StructureNodeSummary])
def get_structure(
    text_slug: str, session: DatabaseSession
) -> list[StructureNodeSummary]:
    try:
        return list_structure(session, text_slug)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/{text_slug}/structure/{node_id}/children",
    response_model=list[StructureNodeSummary],
)
def get_structure_children(
    text_slug: str,
    node_id: uuid.UUID,
    session: DatabaseSession,
) -> list[StructureNodeSummary]:
    try:
        return list_structure(session, text_slug, parent_id=node_id)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{text_slug}/references/resolve", response_model=ReferenceResolution)
def resolve_reference(
    text_slug: str,
    session: DatabaseSession,
    reference: Annotated[str, Query(min_length=1)],
) -> ReferenceResolution:
    try:
        return get_reference_resolution(session, text_slug, reference)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except InvalidRequestError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
