import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import StructureNode


def select_structure_nodes(
    text_id: uuid.UUID, parent_id: uuid.UUID | None
) -> Select[tuple[StructureNode]]:
    parent_filter = (
        StructureNode.parent_id.is_(None)
        if parent_id is None
        else StructureNode.parent_id == parent_id
    )
    return (
        select(StructureNode)
        .where(StructureNode.text_id == text_id, parent_filter)
        .order_by(StructureNode.ordinal, StructureNode.title, StructureNode.id)
    )


def get_structure_node(session: Session, node_id: uuid.UUID) -> StructureNode | None:
    return session.get(StructureNode, node_id)
