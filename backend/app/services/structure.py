import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.queries.library import get_text_by_slug
from app.queries.structure import get_structure_node, select_structure_nodes
from app.schemas.structure import StructureNodeSummary


def list_structure(
    session: Session,
    text_slug: str,
    *,
    parent_id: uuid.UUID | None = None,
) -> list[StructureNodeSummary]:
    text = get_text_by_slug(session, text_slug)
    if text is None:
        raise ResourceNotFoundError(f"Text '{text_slug}' was not found.")

    if parent_id is not None:
        parent = get_structure_node(session, parent_id)
        if parent is None or parent.text_id != text.id:
            raise ResourceNotFoundError(
                f"Structure node '{parent_id}' was not found in text '{text_slug}'."
            )

    return [
        StructureNodeSummary(
            id=node.id,
            parent_id=node.parent_id,
            node_type=node.node_type,
            title=node.title,
            short_title=node.short_title,
            ordinal=node.ordinal,
            path=node.path,
            depth=node.depth,
            start_unit_ordinal=node.start_unit_ordinal,
            end_unit_ordinal=node.end_unit_ordinal,
        )
        for node in session.scalars(select_structure_nodes(text.id, parent_id))
    ]
