# Intertext Text Ingestion

## Pipeline boundaries

Text imports run through six explicit stages:

```text
source acquisition
    → format parsing
    → normalized intermediate representation
    → canonical/reference mapping
    → database persistence
    → validation
```

Providers and formats are independent. The eBible adapter happens to deliver USFM, while the Faithlife Git adapter happens to deliver SBLGNT XML. Persistence receives only `NormalizedVersion` and `NormalizedSegment` records plus canonical mappings; it contains no provider- or format-specific behavior.

## Supported datasets

### KJV

- Source page: `https://ebible.org/find/show.php?id=eng-kjv2006`
- Artifact: `https://ebible.org/Scriptures/eng-kjv2006_usfm.zip`
- Provider: eBible
- Format: USFM
- Text: standardized 1769 KJV, protocanon only
- License: Public Domain outside the United Kingdom, with the source's stated UK Crown printing restrictions

The importer removes USFM markers from displayed plain text. Strong's annotations are retained under each segment's `content_markup.strongs` as surface/identifier records. They are not promoted to Intertext token or lexical tables yet. Footnote bodies are omitted from normalized plain text and their omission count is recorded in segment markup; the raw USFM remains preserved.

### SBLGNT

- Repository: `https://github.com/Faithlife/SBLGNT.git`
- Input path: `data/sblgnt/xml/`
- Provider: Faithlife Git repository
- Format: SBLGNT XML
- Textual version: 1.2, as recorded in the repository version history
- License: Creative Commons Attribution 4.0 International

The importer resolves and records the exact Git commit rather than assuming a version tag. XML word, prefix, and suffix elements are retained in semantic segment markup. SBLGNT is configured as `default_source` for its New Testament coverage. It is never represented as an "original edition." MorphGNT is not part of this import.

## Running imports

From the repository root:

```bash
docker compose up -d postgres
uv sync --all-packages --frozen
uv run --package intertext-backend alembic --config backend/alembic.ini upgrade head
uv run --package intertext-ingest intertext-ingest import kjv
uv run --package intertext-ingest intertext-ingest import sblgnt
```

By default raw artifacts are stored below `data/raw/` and ignored by Git. Use `--raw-dir` to select another archive location. Cached artifacts are reused unless `--refresh` is supplied:

```bash
uv run --package intertext-ingest intertext-ingest import sblgnt --refresh
```

Run ingestion tests with:

```bash
uv run --package intertext-ingest pytest ingestion/tests
```

## Reproducibility and provenance

Each raw acquisition has a sidecar `source.json` containing:

- provider;
- source URL or repository URL;
- HTTP revision headers or resolved Git commit;
- UTC retrieval time;
- SHA-256 artifact checksum;
- textual version where known;
- license;
- raw artifact path.

The same data is copied into `version_releases.metadata.source`, together with importer and parser versions. HTTP archives are stored by checksum so refreshed downloads do not overwrite older artifacts. Git checkouts retain the resolved commit SHA, and the checksum is computed from a deterministic `git archive` of that commit.

An already imported version/checksum is a no-op. A new checksum creates a new immutable `VersionRelease`, retains the old release and segments, and becomes the sole current release.

## Extension points

### New provider using an existing format

Implement the `SourceAdapter` acquisition protocol and register a `DatasetDefinition` with the existing parser. For example, a publisher API returning USFM would require a new source adapter but would reuse `UsfmParser`, normalization, mapping, persistence, and validation.

### New format

Implement the `SourceParser` protocol so it emits the common normalized records. Acquisition adapters, persistence, and release provenance do not change. Format-specific fields belong in normalized metadata or semantic markup, not in persistence code.

### Different corpus

A Quran source uses the same acquisition and parser interfaces and the same normalized records. It supplies a Quran-specific canonical mapper/reference scheme that resolves normalized keys to Quran canonical units and structure nodes. The text-version, release, segment, segment-mapping, provenance, idempotency, and validation infrastructure remains unchanged; Bible book/chapter/verse components are not required by the shared representation.
