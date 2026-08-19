from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import DatabaseSession
from app.core.exceptions import InvalidRequestError, ResourceNotFoundError
from app.schemas.reader import ReaderResponse
from app.services.reader import get_reader

router = APIRouter(prefix="/api/v1/reader", tags=["reader"])


@router.get("/{text_slug}/{reference:path}", response_model=ReaderResponse)
def read_reference(
    text_slug: str,
    reference: str,
    session: DatabaseSession,
    versions: Annotated[
        str | None,
        Query(description="Comma-separated version slugs, in response order"),
    ] = None,
) -> ReaderResponse:
    try:
        return get_reader(session, text_slug, reference, versions)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except InvalidRequestError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
