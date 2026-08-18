from fastapi import APIRouter, HTTPException

from app.api.dependencies import DatabaseSession
from app.core.exceptions import ResourceNotFoundError
from app.schemas.library import TextSummary, VersionSummary
from app.services.library import list_texts, list_versions

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

