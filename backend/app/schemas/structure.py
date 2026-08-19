import uuid

from pydantic import BaseModel


class StructureNodeSummary(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    node_type: str
    title: str
    short_title: str | None
    ordinal: int
    path: str | None
    depth: int
    start_unit_ordinal: int | None
    end_unit_ordinal: int | None
