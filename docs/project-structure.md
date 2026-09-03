# Intertext Project Structure

## 1. Repository strategy

Use a monorepo.

`README.md` lives at the repository root. Detailed documentation lives under `docs/`.

All Python portions of the repository use **uv**.

The backend and ingestion projects are members of a single uv workspace. Each member maintains its own `pyproject.toml`, while dependency resolution is captured in a single repository-level `uv.lock`.

Recommended long-term structure:

```text
intertext/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── .python-version
├── pyproject.toml
├── uv.lock
├── compose.yaml
├── Makefile
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── public/
│   └── src/
│       ├── app/
│       ├── components/
│       ├── hooks/
│       ├── lib/
│       ├── stores/
│       ├── types/
│       └── styles/
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── dependencies.py
│   │   │   └── routes/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── queries/
│   │   ├── repositories/
│   │   ├── search/
│   │   ├── ai/
│   │   └── utils/
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── fixtures/
│
├── ingestion/
│   ├── pyproject.toml
│   ├── intertext_ingest/
│   │   ├── cli.py
│   │   ├── pipeline.py
│   │   ├── importers/
│   │   ├── normalizers/
│   │   ├── tokenizers/
│   │   ├── aligners/
│   │   ├── enrichers/
│   │   ├── provenance/
│   │   ├── rag/
│   │   └── validation/
│   └── tests/
│
├── data/
│   ├── README.md
│   ├── raw/
│   ├── processed/
│   └── samples/
│
├── scripts/
│
├── infra/
│
└── docs/
    ├── architecture.md
    ├── data-model.md
    ├── project-structure.md
    ├── implementation-roadmap.md
    ├── engineering-guidelines.md
    └── decisions/
        ├── 0001-postgresql.md
        ├── 0002-sqlalchemy.md
        ├── 0003-canonical-text-model.md
        └── 0004-text-versions-and-provenance.md
```

## 2. uv workspace

The repository root is the uv workspace root.

The root `pyproject.toml` should define the workspace and should not contain application dependencies that belong specifically to the backend or ingestion project.

A representative root configuration is:

```toml
[project]
name = "intertext"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.uv]
package = false

[tool.uv.workspace]
members = [
    "backend",
    "ingestion",
]
```

The exact supported Python version may be changed before implementation begins, but the repository should maintain one default version in:

```text
.python-version
```

unless a concrete need for different member Python versions appears.

### Workspace members

Each Python subsystem remains its own project.

Example:

```text
backend/
└── pyproject.toml

ingestion/
└── pyproject.toml
```

The backend project should have a distinct package name such as:

```toml
[project]
name = "intertext-backend"
```

The ingestion project should likewise have a distinct name such as:

```toml
[project]
name = "intertext-ingest"
```

Each member declares its own runtime dependencies.

For example, backend-only dependencies such as FastAPI and SQLAlchemy belong in:

```text
backend/pyproject.toml
```

Ingestion-only dependencies belong in:

```text
ingestion/pyproject.toml
```

Dependencies shared by both packages may initially be declared in both projects.

Do not create a shared package merely to deduplicate dependency declarations.

### Lockfile

The workspace uses one root:

```text
uv.lock
```

Commit it to version control.

Do not manually edit `uv.lock`.

### Virtual environment

The normal workspace environment is managed by uv.

Do not commit:

```text
.venv/
```

to version control.

Developers should not need to manually create a virtual environment with:

```bash
python -m venv
```

as part of the standard setup.

### Dependency management

Use uv for dependency changes.

Backend dependency:

```bash
uv add --package intertext-backend <dependency>
```

Backend development dependency:

```bash
uv add --package intertext-backend --dev <dependency>
```

Ingestion dependency:

```bash
uv add --package intertext-ingest <dependency>
```

Ingestion development dependency:

```bash
uv add --package intertext-ingest --dev <dependency>
```

Do not use normal `pip install` commands to mutate the project environment.

### Running commands

Prefer running Python commands through uv.

Examples:

```bash
uv run --package intertext-backend uvicorn app.main:app --reload
```

```bash
uv run --package intertext-backend pytest backend/tests
```

```bash
uv run --package intertext-ingest python -m intertext_ingest.cli
```

Repository scripts that invoke Python should use uv as well.

For example, prefer:

```bash
uv run --package intertext-ingest python -m intertext_ingest.cli
```

over:

```bash
python -m intertext_ingest.cli
```

in documented development commands.

## 3. Do not scaffold everything immediately

The full tree is a target organization, not an instruction to create dozens of empty files.

Initial structure should be closer to:

```text
intertext/
├── README.md
├── .env.example
├── .python-version
├── pyproject.toml
├── uv.lock
├── compose.yaml
│
├── frontend/
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── texts.py
│   │   │       ├── versions.py
│   │   │       └── reader.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/
│   │   │   ├── text.py
│   │   │   ├── structure.py
│   │   │   ├── canonical_unit.py
│   │   │   ├── reference.py
│   │   │   ├── language.py
│   │   │   ├── version.py
│   │   │   └── segment.py
│   │   ├── schemas/
│   │   │   └── reader.py
│   │   ├── services/
│   │   │   └── reader.py
│   │   └── queries/
│   │       └── reader.py
│   └── tests/
│
├── ingestion/
│   ├── pyproject.toml
│   ├── intertext_ingest/
│   │   ├── pipeline.py
│   │   └── importers/
│   │       ├── base.py
│   │       └── usfm.py
│   └── tests/
│
├── data/
│   └── samples/
│
└── docs/
    ├── architecture.md
    ├── data-model.md
    ├── project-structure.md
    ├── implementation-roadmap.md
    ├── engineering-guidelines.md
    └── decisions/
```

Add directories as functionality appears.

## 4. Backend organization

### `app/api/`

HTTP boundary only.

### `app/core/`

Configuration and cross-cutting concerns.

### `app/db/`

Database setup and custom types.

### `app/models/`

SQLAlchemy persistence models.

Expected areas:

```text
text.py
structure.py
canonical_unit.py
reference.py
language.py
version.py
segment.py
token.py
lexeme.py
alignment.py
annotation.py
progress.py
entity.py
cross_reference.py
resource.py
rag.py
user.py
```

Provenance-specific models may be added later when needed.

### `app/schemas/`

Pydantic API schemas.

### `app/services/`

Domain/business behavior.

Likely:

```text
reader.py
reference.py
version_selection.py
alignment.py
annotations.py
progress.py
search.py
entities.py
chat.py
```

### `app/queries/`

Complex SQLAlchemy read queries.

Especially reader and preferred-version resolution.

### `app/repositories/`

Simple entity-oriented persistence only where useful.

### `app/search/`

Later full-text/vector/hybrid search code.

### `app/ai/`

Later AI code.

Do not add it until AI work begins.

## 5. Frontend organization

Suggested:

```text
src/
├── app/
├── components/
│   ├── ui/
│   ├── layout/
│   ├── reader/
│   ├── annotations/
│   ├── language/
│   ├── references/
│   ├── progress/
│   └── chat/
├── hooks/
├── lib/
│   └── api/
├── stores/
├── types/
└── styles/
```

Use `TextUnit` rather than `Verse` as the universal internal component name.

## 6. Ingestion organization

Suggested:

```text
intertext_ingest/
├── cli.py
├── pipeline.py
├── importers/
├── normalizers/
├── tokenizers/
├── aligners/
├── enrichers/
├── provenance/
├── rag/
└── validation/
```

The ingestion package is a separate uv workspace member rather than a collection of ad hoc Python scripts.

Prefer exposing ingestion operations through the package/CLI rather than accumulating standalone scripts with independently managed dependencies.

`provenance/` is optional initially and should appear when imported datasets require source relationships beyond basic `source_imports` metadata.

## 7. Repository scripts

The `scripts/` directory may contain shell scripts or lightweight orchestration helpers.

Python logic of meaningful size should generally live inside a workspace package rather than as an unmanaged root script.

If a root Python script is genuinely appropriate, it must still be executed and dependency-managed with uv.

Do not add inline `pip install` commands to project scripts.

## 8. Shared Python package

Do not introduce a shared Python package on day one.

If backend and ingestion duplicate substantial domain logic, introduce a new workspace member:

```text
packages/
└── intertext-core/
    ├── pyproject.toml
    └── src/
        └── intertext_core/
```

Then update the root workspace:

```toml
[tool.uv.workspace]
members = [
    "backend",
    "ingestion",
    "packages/intertext-core",
]
```

This package could eventually hold truly shared code such as:

* canonical reference primitives;
* common normalization;
* shared enums;
* shared domain value objects.

Use actual duplication as the signal to create it.

## 9. Tests

Use:

```text
tests/
├── unit/
├── integration/
└── fixtures/
```

Run Python tests through uv.

Examples:

```bash
uv run --package intertext-backend pytest backend/tests
```

```bash
uv run --package intertext-ingest pytest ingestion/tests
```

Golden import fixtures are strongly encouraged.

A tiny fixture such as Mark 1:1-3 can validate:

* parsing;
* canonical-unit creation;
* version segment mapping;
* token creation;
* serialized reader output.

## 10. CI

CI should use uv for Python installation, dependency synchronization, and Python commands.

CI should validate that the checked-in lockfile is current rather than silently accepting an out-of-date dependency graph.

Do not maintain a separate CI-only Python dependency installation strategy unless technically required by the deployment platform.

## 11. Naming

Use domain-neutral internal naming where possible.

Prefer:

* `Text`;
* `TextVersion`;
* `VersionSegment`;
* `TextUnit`;
* `CanonicalUnit`;
* `StructureNode`.

Avoid using these as universal architecture terms:

* `Verse`;
* `Chapter`;
* `Book`;
* `OriginalEdition`;
* `Manuscript`.

They may be valid corpus-specific concepts, but they are not universal.
