# Intertext

Intertext is a web application for reading, comparing, annotating, and studying religious texts.

The initial focus is the Bible, but the architecture is intentionally designed to support additional corpora such as the Quran, Hadith collections, the Tanakh, the Vedas, and other structured religious or historical texts without requiring a Bible-specific redesign.

This repository documentation is intended to be the primary handoff for developers and coding agents working on the project.

## Product goals

### Core reading features

Intertext must support:

* Reading structured texts in a normal reader interface.
* Bookmarks, notes, and highlights.
* Reading progress tracking:

  * across an entire text;
  * across books, sections, chapters, or equivalent subsections;
  * independently of the version being viewed.
* Simultaneous side-by-side reading of multiple text versions.
* Alignment of versions by canonical textual unit.
* Reading a translation next to a source-language version.

### Priority source-language features

Intertext should support:

* Selecting or highlighting source-language words or phrases.
* Viewing:

  * translations/glosses;
  * lemmas;
  * transliterations;
  * morphology where data is available;
  * contextual explanations where data is available.
* Interlinear display in which a word-level gloss appears beneath the source-language token.
* Source-to-translation span alignment where source data is available.

### Secondary reference features

Where supporting data exists, Intertext should support:

* Cross-references between passages.
* References to people, places, groups, events, concepts, and other entities.
* Short summaries or metadata for referenced entities.
* Navigation from references back into the reader.

### AI features

AI is intentionally a later-stage feature.

Planned capabilities:

* Whole-text chat:

  * ask questions about an entire corpus;
  * retrieve relevant passages;
  * cite canonical passages in answers.
* Reader-section chat:

  * use the currently visible section as high-priority context;
  * retrieve passages elsewhere in the corpus when needed.
* Optional supplementary commentary retrieval:

  * commentaries;
  * dictionaries;
  * lexicons;
  * scholarly or historical notes.

Primary text and supplementary commentary must remain distinguishable in both storage and AI retrieval.

## Initial technology choices

* Frontend: Next.js, React, TypeScript.
* Styling/components: Tailwind CSS and shadcn/ui.
* Backend: FastAPI.
* Python project/package manager: **uv**.
* Python monorepo organization: **uv workspace**.
* ORM: SQLAlchemy 2.x.
* Validation/API schemas: Pydantic.
* Migrations: Alembic.
* Database: PostgreSQL.
* Local development: Docker Compose for PostgreSQL at minimum.
* Query caching / task infrastructure: Redis later if justified.
* Vector retrieval: pgvector later.
* Frontend server state: TanStack Query is preferred.
* Lightweight local UI state: Zustand is acceptable if needed.

Avoid adding standalone Elasticsearch/OpenSearch, a dedicated vector database, Kafka, or microservices until there is a demonstrated need.

## Python tooling

All Python development in Intertext uses **uv**.

This includes:

* Python version management.
* Virtual environment management.
* Dependency installation and resolution.
* Dependency locking.
* Running Python applications and scripts.
* Running tests.
* Adding and removing dependencies.
* Managing the backend and ingestion projects as one workspace.

The repository contains a root uv workspace with:

```text
pyproject.toml
.python-version
uv.lock
```

The Python workspace members are:

```text
backend/
ingestion/
```

Each workspace member has its own `pyproject.toml`, while the repository uses one shared `uv.lock`.

Do not create or maintain:

```text
requirements.txt
requirements-dev.txt
Pipfile
Pipfile.lock
poetry.lock
```

unless a third-party deployment integration explicitly requires an exported format.

Do not use `pip install` as part of the normal development workflow. Add dependencies through uv.

Common commands should be run from the repository root.

Install/synchronize the Python environment:

```bash
uv sync --all-packages
```

Run the backend:

```bash
uv run --package intertext-backend uvicorn app.main:app --reload
```

Run backend tests:

```bash
uv run --package intertext-backend pytest backend/tests
```

Run ingestion commands:

```bash
uv run --package intertext-ingest intertext-ingest import kjv
uv run --package intertext-ingest intertext-ingest import oshb
uv run --package intertext-ingest intertext-ingest import quran
uv run --package intertext-ingest intertext-ingest import quran-saheeh-international
uv run --package intertext-ingest intertext-ingest import sblgnt
```

Add a backend dependency:

```bash
uv add --package intertext-backend <dependency>
```

Add an ingestion dependency:

```bash
uv add --package intertext-ingest <dependency>
```

The exact package names should match the `[project].name` values in each workspace member's `pyproject.toml`.

Commit `uv.lock` to version control.

## Local development

Prerequisites are uv, Node.js 22 LTS (see `.nvmrc`), npm, and Docker with Docker Compose.

Create local configuration and install dependencies from the committed lockfiles:

```bash
cp .env.example .env
uv sync --all-packages --frozen
npm --prefix frontend ci
```

Start PostgreSQL, then apply database migrations:

```bash
docker compose up -d postgres
uv run --package intertext-backend alembic --config backend/alembic.ini upgrade head
```

The initial migration creates the canonical Phase 1 backend schema. It does not insert corpus data.

Run the backend and frontend in separate terminals:

```bash
uv run --package intertext-backend uvicorn app.main:app --reload
npm --prefix frontend run dev
```

The API health check is available at `http://localhost:8000/health`, and the frontend is available at `http://localhost:3000`.

The frontend proxies `/api/*` and `/health` to the backend so browser requests
remain same-origin during local development. It targets `http://127.0.0.1:8000`
by default; set `INTERTEXT_BACKEND_URL` when starting or building the frontend
to use another backend origin.

Reader selections are reflected in the URL (`text`, `reference`, and
`versions`), so a comparison can be bookmarked or shared.

Run the Phase 0 checks:

```bash
uv run --package intertext-backend pytest backend/tests
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
docker compose config --quiet
uv lock --check
```

Stop PostgreSQL without deleting its named data volume:

```bash
docker compose down
```

## Phase 1 backend API

The backend exposes the corpus-neutral reader foundation at:

```http
GET /api/v1/texts
GET /api/v1/texts/{text_slug}/versions
GET /api/v1/texts/{text_slug}/versions/available?reference=Mark%201
GET /api/v1/texts/{text_slug}/structure
GET /api/v1/texts/{text_slug}/structure/{node_id}/children
GET /api/v1/texts/{text_slug}/references/resolve?reference=Mark%201
GET /api/v1/reader/{text_slug}/{reference}
```

Select reader versions with the comma-separated `versions` query parameter:

```http
GET /api/v1/reader/bible/Mark%201?versions=sblgnt,kjv
```

If no versions are requested, the reader considers all versions that have a current release and returns only those with mapped content in the resolved range. Per-unit `segments` objects omit version keys without content rather than returning empty lists. Reader output is organized by canonical unit; each included version key contains a list of mapped segments so split and merged source boundaries do not require 1:1 alignment.

The API returns an empty library until the separate ingestion package populates corpus data.

## Architectural invariants

Treat these as high-priority constraints.

1. **A conceptual text is not the same thing as a particular text version.**
2. **No translation, manuscript, critical edition, recension, or other version is itself the canonical representation of a text.**
3. **Canonical structure is a reference/alignment framework, not a claim about the historically original wording.**
4. **Canonical structure must be generic enough for non-Biblical corpora.**
5. **Side-by-side alignment is resolved by the backend/domain model, not by the frontend.**
6. **User progress is tracked against canonical textual units, not against a particular text version.**
7. **Source-language tokens, lexical entries, glosses, morphology, and translation alignments are distinct data concepts.**
8. **"Original edition" is not a universal domain concept.**
9. **When the product offers "Original Language," it means the configured preferred source-language version for that passage, not a claim that the version is the historical autograph/original.**
10. **Version provenance is generic and optional; manuscript- or tradition-specific scholarship is modeled only when a feature requires it.**
11. **Imported source files and provenance must be preserved.**
12. **The runtime API and the ingestion pipeline are separate subsystems.**
13. **Database models and API response models are separate layers.**
14. **AI/RAG is built on top of the canonical text model, not used as a substitute for one.**

## Documentation map

* [`docs/architecture.md`](docs/architecture.md) — system architecture and responsibilities.
* [`docs/data-model.md`](docs/data-model.md) — canonical storage model and planned tables.
* [`docs/project-structure.md`](docs/project-structure.md) — repository/folder organization and uv workspace layout.
* [`docs/implementation-roadmap.md`](docs/implementation-roadmap.md) — recommended build order and milestones.
* [`docs/engineering-guidelines.md`](docs/engineering-guidelines.md) — conventions for agents and contributors.
* [`docs/ingestion.md`](docs/ingestion.md) — source acquisition, parsing, provenance, and import commands.
* [`docs/endpoints.md`](docs/endpoints.md) — backend HTTP endpoints and request parameters.
* [`docs/decisions/0001-postgresql.md`](docs/decisions/0001-postgresql.md) — PostgreSQL decision.
* [`docs/decisions/0002-sqlalchemy.md`](docs/decisions/0002-sqlalchemy.md) — SQLAlchemy over SQLModel.
* [`docs/decisions/0003-canonical-text-model.md`](docs/decisions/0003-canonical-text-model.md) — canonical-unit architecture.
* [`docs/decisions/0004-text-versions-and-provenance.md`](docs/decisions/0004-text-versions-and-provenance.md) — generic version/source-language/provenance model.

## First meaningful product milestone

The first strong end-to-end milestone should be:

> Open Mark 1, choose one configured Greek source-language version and two English translations, display all selected versions aligned by canonical verse/unit, select a Greek word and view its lexical/gloss information, add a note to a passage, bookmark a passage range, leave the reader, and later return to the saved reading position.

Do not build AI before the reader, canonical model, alignment model, annotations, and progress tracking are reliable.
