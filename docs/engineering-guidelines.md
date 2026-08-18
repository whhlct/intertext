# Intertext Engineering Guidelines

## Purpose

These guidelines are for developers and coding agents modifying Intertext.

## 1. Preserve architectural invariants

Before changing the data model, verify that the change does not violate these rules:

* conceptual text != text version;
* canonical structure != version wording;
* canonical does not mean historically original wording;
* progress is canonical, not version-specific;
* side-by-side alignment is backend/domain behavior;
* source-language token data is structured;
* provenance is preserved where known;
* AI is downstream of the canonical text model.

If a change requires violating one of these rules, document the reason in a new ADR before implementing it.

## 2. Use uv for all Python tooling

All Python portions of Intertext use **uv**.

The repository is organized as a uv workspace.

Current workspace members are:

```text
backend
ingestion
```

Use uv for:

* installing/managing Python;
* virtual environments;
* dependency management;
* dependency locking;
* running applications;
* running tests;
* executing Python scripts and CLI tools.

Do not introduce a parallel dependency-management workflow using:

* raw `pip`;
* `requirements.txt` as the primary dependency source;
* Poetry;
* Pipenv;
* Conda environment files for application dependency management.

If an external deployment system requires `requirements.txt`, generate/export it from the uv-managed dependency graph rather than treating it as an independently maintained source of truth.

### Dependency changes

Use:

```bash
uv add --package <workspace-package> <dependency>
```

and:

```bash
uv remove --package <workspace-package> <dependency>
```

rather than manually mutating environments.

Editing `pyproject.toml` directly is acceptable when appropriate, but the resulting `uv.lock` must remain synchronized.

### Running Python

Document commands using:

```bash
uv run ...
```

rather than assuming that a developer has manually activated `.venv`.

For workspace-specific commands, prefer explicit package selection where it improves clarity:

```bash
uv run --package intertext-backend ...
```

```bash
uv run --package intertext-ingest ...
```

### Lockfile

The repository-level:

```text
uv.lock
```

is committed to version control.

Do not manually edit it.

Dependency changes that affect the lockfile should include the updated lockfile in the same commit.

### Python version

The default Python version is declared through the root:

```text
.python-version
```

and compatible `requires-python` declarations in the relevant `pyproject.toml` files.

Do not assume a system-installed Python version.

### Workspace configuration

Repository-wide uv configuration belongs at the workspace root.

Package-specific dependencies belong in the relevant workspace member's `pyproject.toml`.

Do not place backend-only dependencies in the ingestion project or vice versa merely because both share one uv workspace.

## 3. Avoid corpus-specific assumptions in shared code

Bad universal interface:

```python
def get_verse(book: str, chapter: int, verse: int):
    ...
```

Prefer:

```python
resolve_reference(text_id, reference)
get_canonical_range(...)
get_text_units(...)
```

Similarly, use `TextUnit` rather than `Verse` in universal frontend/domain code.

## 4. Do not use "original edition" as a domain primitive

The product may expose a user-facing action such as **Original Language**.

Internally this resolves to a range-specific preferred text version:

```text
role = default_source
```

Do not represent this as:

```text
is_original = true
```

or:

```text
original_version_id
```

unless a future corpus has a genuinely separate, corpus-specific concept that requires it.

## 5. Separate identity, role, and provenance

These are different questions:

* **What is this representation?** → `text_version` + descriptive metadata.
* **How should Intertext use it here?** → `preferred_versions`.
* **Where did it come from?** → optional `sources` + `version_sources`.

Do not overload one field to answer all three.

## 6. Keep corpus-specific scholarship out of the universal core

Do not create universal tables such as:

* `manuscript_witnesses`;
* `isnad`;
* `qiraat`;
* `shakha`;

until a concrete feature requires that corpus-specific concept.

If needed, add a specialized module that references universal `Text`, `TextVersion`, and `CanonicalUnit` identifiers.

## 7. Keep HTTP routes thin

Routes should:

* parse input;
* resolve dependencies;
* call a service;
* return a schema.

Domain behavior belongs in services.

Complicated SQL belongs in queries/repositories.

## 8. Keep persistence and API schemas separate

SQLAlchemy models describe storage.

Pydantic models describe API inputs/outputs.

Do not automatically expose ORM models as public API contracts.

## 9. Use repositories selectively

Repositories are useful for ordinary entity operations.

Prefer specialized query modules for:

* aligned passage retrieval;
* progress aggregation;
* source-version resolution;
* text search;
* RAG retrieval.

## 10. Avoid premature abstraction

Do not create:

* generic base repositories with dozens of unused methods;
* plugin systems before multiple implementations exist;
* shared packages before meaningful duplication exists;
* microservices without a scaling/ownership reason;
* generic transmission schemas trying to unify fundamentally different traditions.

If backend and ingestion eventually need substantial shared Python code, create an additional uv workspace member rather than copying the package or using ad hoc path manipulation.

## 11. Database migrations

Every schema change must have an Alembic migration.

Run Alembic through the backend uv project environment.

For example:

```bash
uv run --package intertext-backend alembic upgrade head
```

Review migrations for:

* foreign-key behavior;
* indexes;
* nullability;
* backfills;
* destructive changes;
* rollback feasibility.

## 12. Provenance

Whenever data is imported, generated, aligned, glossed, or enriched, preserve enough metadata to answer:

* Where did this data come from?
* What version was imported?
* When was it imported?
* Was it curated, algorithmic, or generated?
* What license applies?
* What confidence/quality information exists?

Do not mix generated and curated data without marking it.

## 13. Licensing

Do not assume a translation or scholarly edition is freely redistributable because the underlying ancient text is old.

Record:

* license;
* copyright/rights statement;
* redistribution restrictions;
* attribution requirements.

## 14. Ingestion validation

At minimum consider:

* duplicate canonical keys;
* missing expected structure;
* unmapped segments;
* impossible canonical ranges;
* invalid token offsets;
* malformed Unicode;
* missing language metadata;
* broken foreign references;
* invalid alignment spans.

Use small golden fixtures.

Run ingestion tests and tools through the ingestion uv workspace package.

## 15. Reader performance

Avoid N+1 patterns.

The reader may request:

* canonical units;
* multiple versions;
* source tokens;
* annotations;
* references.

Use deliberate query/loading strategies.

Do not denormalize prematurely.

## 16. Source-language data

Never assume:

```text
token == word
```

Keep tokenization source/version metadata where appropriate.

## 17. Alignments

Never assume:

```text
1 source token == 1 translated token
```

Use span-based alignments.

Do not fabricate word alignment from order alone.

## 18. Progress semantics

Before implementing automatic "read" detection, define the behavior.

Storage remains canonical regardless of UI strategy.

## 19. AI behavior

When AI is introduced:

* cite canonical passages;
* distinguish primary text from commentary;
* keep retrieval observable/debuggable;
* store embedding model/version metadata;
* make re-embedding possible;
* avoid embedding-only search;
* do not let LLM output become authoritative lexical data without provenance.

AI-related Python dependencies should remain in the appropriate uv workspace project and should not be installed through separate unmanaged environments.

## 20. Scripts and automation

Avoid standalone Python scripts with undocumented dependencies.

If a script belongs to the backend domain, place its logic in the backend package.

If it belongs to ingestion, place it in the ingestion package.

Use `scripts/` primarily for lightweight orchestration.

All Python execution documented by the project should run through uv.

## 21. CI and deployment

CI should:

* install uv;
* install the configured Python version;
* validate/synchronize from `uv.lock`;
* run Python checks through uv.

Prefer lockfile-enforcing CI behavior so an outdated `uv.lock` causes the build to fail rather than being silently regenerated.

Deployment containers should likewise install dependencies from the uv-managed project definition and lockfile.

## 22. Documentation

Update documentation when changing:

* Python workspace organization;
* Python version policy;
* canonical data model;
* text-version model;
* preferred source selection;
* repository organization;
* backend layering;
* corpus import expectations;
* AI retrieval architecture.

For major architectural decisions, add an ADR under `docs/decisions/`.
