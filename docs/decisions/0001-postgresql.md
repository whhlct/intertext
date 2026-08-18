# ADR 0001: Use PostgreSQL as the Primary Database

- Status: Accepted
- Project: Intertext

## Context

Intertext requires highly relational data:

- conceptual texts;
- hierarchical structures;
- canonical textual units;
- text versions and releases;
- many-to-many segment mappings;
- tokens and lexical records;
- user annotations;
- progress tracking;
- cross references;
- entities;
- supplementary resources.

The system also benefits from semi-structured metadata, full-text search, hierarchical querying, and eventually vector retrieval.

## Decision

Use PostgreSQL as the primary application database.

Use PostgreSQL-native features when they provide clear value, including:

- JSONB for flexible metadata;
- full-text search;
- optional `ltree` for hierarchy operations;
- pgvector later for embeddings/vector search;
- GIN and specialized indexes where justified.

## Consequences

### Benefits

- Strong relational integrity.
- Good fit for the canonical alignment model.
- Flexible JSONB metadata for language/corpus-specific fields.
- One database can initially support relational, text, and vector retrieval.
- Avoids premature introduction of multiple data stores.

### Costs

- Some specialized search workloads may eventually justify an external search engine.
- Advanced PostgreSQL features create some database-specific coupling.
- Care is needed with indexing and query design as the corpus grows.

## Alternatives considered

### MongoDB

Rejected as the primary store because Intertext's core complexity is relational rather than document-shaped.

### Dedicated vector database

Deferred.

Vector search is not needed for the initial reader and can later be added with pgvector.

### Elasticsearch/OpenSearch

Deferred.

PostgreSQL full-text search is sufficient for initial search needs.
