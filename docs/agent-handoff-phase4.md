# Agent handoff: Phase 4 user accounts and annotations

## Purpose and scope

This document hands off Phase 4 of `docs/implementation-roadmap.md`. The next
agent should implement user accounts and account-owned annotation data in this
order:

1. account creation and storage;
2. authentication and authorization;
3. account-specific data management for bookmarks, notes, highlights, and
   their anchors;
4. the corresponding frontend account and annotation workflows.

Phase 5 remains a separate milestone. Do not add reading positions or reading
progress as part of Phase 4 unless the scope is explicitly expanded.

## Read before making decisions

Read the project documentation in this order:

1. `README.md`
2. `docs/architecture.md`
3. `docs/data-model.md`
4. `docs/project-structure.md`
5. `docs/implementation-roadmap.md`
6. `docs/engineering-guidelines.md`
7. every accepted ADR in `docs/decisions/`
8. `docs/endpoints.md`
9. this handoff

The accepted ADRs and architectural invariants are authoritative. Flag a
concrete contradiction instead of silently changing the architecture. The
most relevant invariants for Phase 4 are:

- a conceptual `Text` and a `TextVersion` are different entities;
- canonical units identify locations and alignment targets, not authoritative
  wording;
- passage annotations can be version-independent by anchoring to canonical
  units;
- version- or token-specific annotations add optional anchors rather than
  replacing the canonical range;
- progress is canonical and version-independent;
- FastAPI routes stay thin, SQLAlchemy models remain separate from Pydantic
  schemas, and complex reads belong in queries while ordinary user/annotation
  persistence may use repositories.

## What is implemented now

### Development and deployment foundation

- The repository is a monorepo with `backend/`, `frontend/`, and `ingestion/`.
- Python 3.12 packages are members of one root uv workspace with a committed
  `uv.lock`. Use uv exclusively; do not introduce pip requirements, Poetry, or
  another Python dependency workflow.
- `compose.yaml` runs PostgreSQL 17, FastAPI, and Next.js. It includes database
  persistence and health checking, service-name networking, development watch
  rules, and development/production Docker targets.
- The backend runs Alembic migrations before Uvicorn starts in Compose.
- The ignored root `.env` is the active local runtime configuration. Compose
  loads it automatically for interpolation and explicitly passes each service
  only the variables it needs. `.env.example` is a developer template and is
  never used directly by the application or Compose. Inside Compose, the
  backend connects to `db`, and Next.js connects to `backend`; browser requests
  remain same-origin through the Next.js proxy.

### Canonical backend and reader API

The database currently has Alembic migrations for:

- texts, structure nodes, canonical units, and reference schemes/labels;
- languages, text versions, releases, segments, and segment-to-unit mappings;
- range-specific preferred versions;
- enrichment imports, lexemes, tokens, and token glosses.

The runtime backend has layered routes, services, queries, SQLAlchemy models,
and Pydantic response schemas. Existing endpoints are documented in
`docs/endpoints.md` and include:

```http
GET /health
GET /api/v1/texts
GET /api/v1/texts/{text_slug}/versions
GET /api/v1/texts/{text_slug}/versions/available?reference=...
GET /api/v1/texts/{text_slug}/structure
GET /api/v1/texts/{text_slug}/structure/{node_id}/children
GET /api/v1/texts/{text_slug}/references/resolve?reference=...
GET /api/v1/reader/{text_slug}/{reference}?versions=...
```

The reader response is aligned by canonical unit. It returns only versions and
per-unit segment keys with actual content. Persisted tokens and contextual
glosses are included with segments.

### Ingestion and available content

The corpus-neutral acquisition, parsing, normalization, canonical mapping,
persistence, and validation pipeline supports:

- KJV from eBible USFM;
- SBLGNT from Faithlife XML;
- OSHB/WLC Hebrew from Open Scriptures OSIS XML;
- Tanzil simple Arabic Quran XML;
- Saheeh International Quran translation text;
- TAGNT contextual English gloss enrichment aligned to SBLGNT tokens.

Imports are provenance-aware and idempotent. Raw artifacts live separately
under ignored `data/raw/`. Details and exact commands are in
`docs/ingestion.md`. Phase 4 must not move ingestion behavior into the runtime
backend.

### Frontend reader

The Next.js/React/TypeScript frontend currently provides:

- library/text selection and corpus-neutral structure navigation;
- reference resolution and chapter/section navigation;
- aligned multi-version reader columns;
- version availability filtering and URL-backed reader state;
- default English-first ordering with configured source-language versions at
  the far right;
- draggable and keyboard-reorderable columns, with ordering reflected in the
  version picker;
- responsive left-to-right and right-to-left text display;
- word-by-word contextual English gloss display for enriched SBLGNT tokens;
- TanStack Query for server state and Vitest/Testing Library tests.

There are no login, registration, account menu, annotation controls, or
account-state providers yet.

## Phase 4 is not implemented

There is currently no:

- `users` table or SQLAlchemy user model;
- selected authentication strategy or auth ADR;
- credential, external identity, session, or refresh-token storage;
- password hashing/authentication dependency;
- current-user API, registration, login, or logout endpoint;
- authorization policy for user-owned records;
- bookmark, note, highlight, annotation, or annotation-anchor table;
- account/annotation backend service, repository, schema, or route;
- account or annotation frontend UI;
- account/annotation tests.

The backend dependency module currently exposes only `DatabaseSession`, and
the backend project has no authentication libraries. Do not assume an identity
provider or credential model has already been chosen.

## Required implementation sequence

### 1. Select and document the authentication strategy

This is an explicit Phase 4 roadmap decision. Add an ADR before building a
schema whose shape depends on the choice. Decide at least:

- locally managed email/password credentials versus an external identity
  provider;
- browser session cookies versus bearer access/refresh tokens;
- session persistence and revocation behavior;
- email normalization, verification, password reset, and account lifecycle
  expectations;
- CSRF protection if cookie authentication is used.

A conventional first-party web baseline is an internal user plus a revocable,
opaque server-side session in an `HttpOnly`, `Secure` in production,
`SameSite` cookie. If local passwords are selected, hash them with a current
password-hashing algorithm and keep credential fields separate from public
profile data. This is a recommendation to evaluate and record, not an accepted
project decision.

Do not put long-lived credentials in browser local storage, return password
hashes through the API, log secrets, or trust a client-supplied user ID.

Put any new local auth/session configuration in the ignored root `.env`, add
non-secret placeholder keys and setup guidance to `.env.example`, and pass
only the required values to the backend through its explicit `environment`
block in `compose.yaml`. Do not give auth secrets to the frontend or database
containers, and do not use `.env.example` as a runtime env file.

### 2. Implement account creation and storage

At minimum add a `users` model, migration, Pydantic schemas, account service,
and focused repository/query code. The final fields depend on the auth ADR,
but the model should have:

- UUID primary key, consistent with existing tables;
- stable unique login identity, with explicit case/normalization semantics;
- timezone-aware `created_at` and `updated_at` values using the existing
  `TimestampMixin` where appropriate;
- an explicit active/disabled state if accounts can be revoked;
- no secret fields in public API responses.

Add separate credential, identity, or session tables if required by the
selected strategy. Use PostgreSQL constraints and indexes for invariants; do
not rely only on application-level duplicate checks. Every schema change needs
an Alembic migration with a reviewed downgrade.

Suggested initial account contract, subject to the ADR:

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
```

Choose predictable status codes and a single safe error shape. Avoid account
enumeration through materially different login/registration errors where the
product does not require it.

### 3. Add authentication dependencies and authorization

Create a reusable FastAPI dependency that resolves the authenticated user from
the selected session/token mechanism. Keep transport parsing in the HTTP/auth
boundary and account rules in a service. Public reader endpoints should remain
public unless a product decision says otherwise.

Authorization is ownership-based for Phase 4:

- every annotation query and mutation must be scoped to the authenticated
  user's ID in the database query itself;
- never load by annotation ID and return/mutate it before checking ownership;
- use a consistent `401` response for missing/invalid authentication and a
  deliberate `403` or non-disclosing `404` policy for another user's record;
- validate canonical, release, segment, and token relationships server-side;
- do not accept `user_id` in annotation create/update payloads.

Test cross-user access explicitly. A test must prove that one user cannot read,
update, or delete another user's records even when the UUID is known.

### 4. Implement account-specific annotations

Follow the model in `docs/data-model.md`:

```text
annotations
  id
  user_id -> users
  type             # bookmark, note, highlight
  body nullable
  color nullable
  created_at
  updated_at
  metadata JSONB

annotation_anchors
  id
  annotation_id -> annotations
  text_id -> texts
  start_unit_id -> canonical_units
  end_unit_id -> canonical_units
  version_release_id -> version_releases nullable
  start_token_id -> tokens nullable
  end_token_id -> tokens nullable
  metadata JSONB
```

Preserve these semantics:

- a bookmark/note/highlight may anchor to a canonical range and therefore
  survive a version switch;
- optional version-release/token fields make an anchor more specific without
  making all annotations version-specific;
- ranges are inclusive and must have `start.ordinal <= end.ordinal`;
- both canonical endpoints must belong to the anchor's text;
- token bounds, when supplied, must be ordered and belong to compatible
  segments/releases in the anchored range;
- deleting a user should have a deliberate documented effect on owned data;
  deleting canonical/imported content should not silently leave invalid
  anchors.

Define type-specific validation instead of allowing nonsensical combinations.
For example, notes need a body, highlights may have a color, and bookmarks do
not need either. Decide whether one annotation may have multiple anchors before
encoding uniqueness constraints.

Suggested API shape:

```http
GET    /api/v1/annotations?text_slug=...&reference=...
POST   /api/v1/annotations
GET    /api/v1/annotations/{annotation_id}
PATCH  /api/v1/annotations/{annotation_id}
DELETE /api/v1/annotations/{annotation_id}
```

The range-list endpoint should resolve references through the existing
reference service and use a deliberate overlap query; avoid N+1 loading. Keep
annotation CRUD in a selective repository and range-oriented reads in a query
module. Update `docs/endpoints.md` with the final contract.

### 5. Add the frontend account and annotation experience

Build only the UI required to exercise the Phase 4 backend end to end:

- registration, login, logout, and current-account state;
- clear authenticated, unauthenticated, loading, and expired-session states;
- controls to bookmark a canonical range, add/edit a note, and apply/remove a
  highlight;
- an annotation list/panel for the currently resolved canonical range;
- optimistic updates only where rollback/error behavior is reliable;
- TanStack Query keys scoped correctly to the authenticated account and
  invalidated on login/logout and annotation mutations.

The reader already exposes canonical unit IDs/keys plus segment and token IDs
in its typed response. The separate version-list response exposes
`current_release_id`, but the reader's version objects do not. If creating a
version/token-specific anchor needs an unambiguous release in the reader flow,
either consume and validate the version-list value or add a backward-compatible
release ID to the reader response. Reuse authoritative IDs; do not infer
anchors from displayed verse labels or align versions in the browser. On
logout, clear account-specific cached data so it cannot appear for the next
user on the same browser.

Maintain accessible keyboard operation, focus handling, labels, error states,
and the existing responsive reader behavior. New components naturally belong
under `frontend/src/components/annotations/` and account/auth components under
a focused directory rather than inside the reader grid.

## Tests and completion criteria

Backend coverage should include:

- account creation, identity normalization, duplicate handling, and safe
  serialization;
- successful and failed login, logout/revocation, expired/invalid sessions,
  and disabled users as applicable;
- authenticated-user dependency behavior;
- annotation CRUD for bookmarks, notes, and highlights;
- canonical-range, version-release, and token-anchor validation;
- canonical annotations remaining visible across version selections;
- range-overlap retrieval;
- strict cross-user isolation for every read and mutation;
- migration upgrade/downgrade review against PostgreSQL, not SQLite alone.

Frontend coverage should include account state, form errors, session expiry,
annotation creation/edit/delete, cache isolation on logout, and accessible
interaction with reader units/tokens.

Phase 4 is complete when a new user can register, authenticate, create each
annotation type on a passage, retrieve and modify only their own annotations,
log out, log back in, and see the data restored at the correct canonical or
version/token-specific anchor.

Run at least:

```bash
uv lock --check
uv run --package intertext-backend alembic --config backend/alembic.ini upgrade head
uv run --package intertext-backend pytest backend/tests
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
docker compose config --quiet
```

Also exercise the authentication and annotation flow through the running
PostgreSQL-backed stack, not only mocked or in-memory tests.

## Working conventions and commands

The current working copy already has an ignored root `.env`. For a fresh
checkout, create it from the developer template and replace local placeholder
secrets as needed:

```bash
cp .env.example .env
uv sync --all-packages --frozen
npm --prefix frontend ci
docker compose up --build
```

For container hot reload:

```bash
docker compose up --watch --build
```

For host-run development:

```bash
docker compose up -d db
uv run --package intertext-backend alembic --config backend/alembic.ini upgrade head
uv run --package intertext-backend uvicorn app.main:app --reload
npm --prefix frontend run dev
```

Add backend dependencies with:

```bash
uv add --package intertext-backend <dependency>
```

Never edit `uv.lock` manually. Preserve unrelated working-tree changes. Add
models to `backend/app/models/__init__.py` so Alembic metadata sees them.

## Known caveats and session notes

- The actual implementation is ahead of the numbered roadmap in one area:
  tokens, TAGNT gloss persistence, reader token responses, and an interlinear
  gloss UI already exist. Inspect code before scaffolding a roadmap phase.
- The database is not seeded by migrations. A fresh database has schema but no
  texts; run the documented ingestion commands when realistic reader data is
  needed.
- Source-language defaults are range-specific `preferred_versions` records
  with role `default_source`. Do not add an `is_original` account preference or
  otherwise revive the rejected "original edition" concept.
- The frontend currently has one generic `apiFetch` wrapper and no auth-aware
  request behavior. Cookie credentials are same-origin by default; a bearer
  strategy would require explicit secure token handling.
- A recent local verification found that the frontend tests and typecheck pass,
  while the existing backend suite can stall in
  `backend/tests/test_phase_one_api.py` inside the first ASGI request after the
  health/database tests. The Dockerized backend and its PostgreSQL-backed API
  were healthy. Reproduce and resolve or isolate this test-lifecycle issue
  before treating Phase 4's test suite as reliable; do not hide it with broad
  timeouts or skipped authorization tests.
- Compose development, Compose Watch synchronization, Uvicorn reload, Next.js
  recompilation, database connectivity, service-name communication, and both
  production image targets were verified during the Docker work. Compose was
  also revalidated and started without `--env-file`, proving that it resolves
  the active root `.env`. The default development stack was left running at
  ports 3000, 8000, and 5432 at that time, but agents should still inspect
  current container state rather than assuming it remains active.

## Explicit non-goals for this handoff

Unless separately requested, do not implement:

- Phase 5 reading positions, completion tracking, or progress aggregation;
- social profiles, follows, sharing, teams, organizations, or admin consoles;
- OAuth providers in addition to the selected minimal auth strategy;
- AI/RAG, search, cross-references, or new text ingestion;
- a generic authorization framework beyond the concrete ownership rules Phase
  4 needs;
- frontend-only canonical/reference or version-alignment logic.
