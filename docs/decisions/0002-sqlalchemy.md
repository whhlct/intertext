# ADR 0002: Use SQLAlchemy 2.x with Pydantic Instead of SQLModel

- Status: Accepted
- Project: Intertext

## Context

The backend uses FastAPI and PostgreSQL.

Two reasonable ORM approaches were considered:

1. SQLModel.
2. SQLAlchemy 2.x plus separate Pydantic schemas.

SQLModel offers good FastAPI ergonomics and reduces boilerplate.

Intertext, however, is expected to have a sophisticated relational model involving:

- association objects with metadata;
- version-to-canonical mappings;
- self-referential hierarchical structures;
- source-language tokens and lexical data;
- span alignments;
- annotation anchors;
- PostgreSQL-specific types/indexes;
- sophisticated reader queries;
- later full-text and vector retrieval.

## Decision

Use:

- SQLAlchemy 2.x for persistence and querying.
- Pydantic for API request/response schemas.
- Alembic for migrations.

Do not use SQLModel as the primary ORM abstraction.

## Rationale

### Direct control

SQLModel is built on SQLAlchemy.

Intertext is expected to need direct SQLAlchemy capabilities regularly.

### Persistence and API models have different jobs

The reader API will often return composite objects that do not correspond to one table.

Separating SQLAlchemy models from Pydantic schemas makes this explicit.

### Complex association objects

Many mappings contain domain data of their own.

### PostgreSQL-specific behavior

The project is expected to use features such as:

- JSONB;
- GIN indexes;
- `ltree`;
- pgvector;
- full-text search;
- specialized indexes.

## Consequences

### Benefits

- Maximum ORM/query flexibility.
- Clear persistence/API separation.
- Easier use of advanced PostgreSQL behavior.

### Costs

- More boilerplate.
- Separate ORM and Pydantic classes may duplicate some fields.
- Slightly steeper learning curve.
