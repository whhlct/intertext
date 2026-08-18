# Intertext Implementation Roadmap

## Goal

Build Intertext incrementally while protecting the core canonical data model.

The project should first become a reliable reading application. Source-language study features come next. AI comes later.

## Phase 0 — Repository and development environment

Deliver:

- monorepo;
- root `README.md`;
- `frontend/`, `backend/`, `ingestion/`, and `docs/`;
- PostgreSQL through Docker Compose;
- FastAPI health endpoint;
- Next.js app;
- SQLAlchemy session;
- Alembic;
- `.env.example`;
- basic test commands.

## Phase 1 — Canonical text foundation

Implement:

- `texts`;
- `structure_nodes`;
- `canonical_units`;
- `reference_schemes`;
- `reference_labels`;
- `languages`;
- `text_versions`;
- `version_releases`;
- `version_segments`;
- `segment_unit_mappings`;
- `preferred_versions`.

Initial scope:

- Gospel of Mark;
- at minimum Mark 1;
- one source-language Greek version;
- one English translation;
- add a second English translation early.

Required capabilities:

```http
GET /api/v1/texts
GET /api/v1/texts/{text_slug}/versions
GET /api/v1/reader/{text_slug}/{reference}
```

Exit criterion:

The backend can resolve a reference such as `Mark 1`, retrieve canonical units, resolve the configured preferred source-language version, and return aligned selected-version segments.

## Phase 2 — Basic reader UI

Build:

- text/library selector;
- reference navigation;
- reader;
- one-column version display;
- version selector;
- responsive layout.

## Phase 3 — Side-by-side version alignment

Build:

- multi-version selection;
- multiple reader columns;
- canonical-row alignment;
- responsive stacked/horizontal behavior.

The frontend consumes backend-resolved alignment.

Do not implement a frontend-only verse matching algorithm.

## Phase 4 — User accounts and annotations

Select authentication strategy.

Build:

- internal `users` table;
- bookmarks;
- notes;
- highlights;
- canonical-range anchors;
- version/token-specific anchors where needed.

## Phase 5 — Reading position and progress

Build:

- last reading position;
- canonical-unit completion tracking;
- progress aggregation across structural nodes.

Progress must work independently of version selection.

## Phase 6 — Source-language token data

Implement:

- `tokens`;
- `lexemes`;
- glosses;
- morphology;
- token selection UI;
- token detail popover/panel.

Clicking/selecting a source-language token should be able to display:

- surface form;
- lemma;
- transliteration;
- part of speech;
- morphology;
- glosses;
- provenance/source metadata where appropriate.

## Phase 7 — Interlinear mode

Build:

- token-level gloss rendering;
- optional transliteration;
- optional morphology;
- line wrapping that preserves token/gloss relationships.

## Phase 8 — Source-to-translation span alignment

Implement:

- `span_alignments`;
- alignment import/storage;
- hover/click synchronized highlighting.

Do not invent alignments where reliable alignment data is unavailable.

## Phase 9 — Generic provenance as required

When real imported datasets require it, add:

- `sources`;
- `version_sources`;
- optionally `version_coverage`.

Do not build manuscript-witness or textual-variant subsystems merely because they may be useful someday.

Add corpus-specific provenance/scholarly structures only when a concrete feature requires them.

## Phase 10 — Search and references

Build:

- structured reference lookup;
- PostgreSQL full-text search;
- cross references;
- entities;
- entity mentions;
- entity/reference UI.

## Phase 11 — Broaden corpus support

Add at least one non-Biblical corpus before AI if practical.

This validates that the model is genuinely generic.

A new corpus should not require replacing the universal model with corpus-specific tables.

## Phase 12 — RAG/search foundation

Implement:

- `rag_chunks`;
- chunk generation;
- PostgreSQL full-text search metadata;
- pgvector;
- embeddings;
- hybrid retrieval;
- canonical citation resolution.

Do not use one verse as the only chunk size.

## Phase 13 — Section chat

Build:

- chat panel within the reader;
- current canonical range as direct high-priority context;
- broader retrieval when required;
- clickable passage citations.

## Phase 14 — Whole-text chat

Build:

- corpus-level chat;
- hybrid retrieval;
- citation handling;
- optional conversation persistence.

## Phase 15 — Supplementary resources

Implement:

- resources;
- resource entries;
- commentary ingestion;
- commentary RAG chunks;
- primary-text-only vs primary+commentary modes.

## Immediate first milestone

> Open Mark 1, choose a configured Greek source-language version plus two English translations, display all three aligned, select a Greek word and see its gloss/lexical information, add a note, bookmark a passage, leave, and later return to the same reading position.

## Things not to prioritize early

Do not spend substantial early effort on:

- microservices;
- Kubernetes;
- Kafka;
- standalone vector databases;
- Elasticsearch/OpenSearch;
- elaborate caching;
- AI agents;
- commentary ingestion;
- manuscript witness databases;
- textual apparatus modeling;
- tradition-specific transmission graphs;
- broad corpus coverage before the first reader works.

Optimize for a correct canonical model and a strong reader first.
