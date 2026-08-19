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

Providers, formats, and corpora are independent. The eBible adapter happens to deliver USFM, the Faithlife Git adapter happens to deliver SBLGNT XML, and Tanzil happens to deliver Quran XML. Format parsers emit format-native `SourceReference` values and do not construct Intertext canonical references. The responsible corpus mapper interprets those values and emits resolved canonical targets. Persistence receives only the resolved version and canonical unit IDs; it contains no provider-, format-, or corpus-specific behavior.

Corpus resolution happens before persistence. Consequently both `MRK 1:1` from USFM and `Mark 1:1` from SBLGNT persist as the canonical segment identifier `Mark 1:1`, target `bible.mark.1.1`, and structure path `bible.mark.1`. Parser-native identifiers remain confined to the in-memory parsed representation and the preserved raw artifact.

Version metadata such as language, script, direction, title, and rights belongs to the dataset definition rather than reusable parsers. Generic normalization is limited to Unicode, whitespace, text, and markup cleanup. Generic validation checks segment ordering, duplicates, empty content, and resolved mappings; Bible coverage and testament expectations are checked under `corpora/bible/validation.py`.

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

### Tanzil Quran Text (Simple)

- Artifact: `https://tanzil.net/pub/download/index.php?marks=true&sajdah=true&tatweel=true&quranType=simple&outType=xml&agree=true`
- Provider: Tanzil Project
- Format: Quran XML (`quran` / `sura` / `aya`)
- Textual version: 1.1, as recorded in the downloaded copyright block
- License: Creative Commons Attribution 3.0, together with the attribution, link, copyright-notice, and verbatim-text terms embedded in the artifact

The XML is preserved unchanged, including its copyright block. Ayah text is
stored exactly from each `text` attribute. The separate `bismillah` attribute
and any future source attributes are retained under segment
`content_markup.attributes`; they are not silently concatenated into the
numbered ayah text. Quran mapping creates the separate conceptual `Quran` text,
114 top-level `surah` structure nodes, 6,236 `ayah` canonical units, and
references such as `2:255`, `Surah 2`, and the source Arabic surah name. The
Tanzil version is configured as `default_source` for its coverage without being
described internally as an original edition.

### Saheeh International

- Artifact: `https://tanzil.net/trans/?transID=en.sahih&type=txt-2`
- Provider: Tanzil Project
- Format: pipe-delimited Quran translation text (`surah|ayah|content`)
- Translation ID: `en.sahih`
- Last update: April 24, 2011, as recorded in the downloaded artifact
- Rights: non-commercial use only through Tanzil; other use requires permission from the translator or publisher

The parser ignores empty lines and metadata/comment lines beginning with `#`,
splits each content line at only the first two `|` delimiters, validates
contiguous surah/ayah ordering, and preserves translation content without
normalizing or rewriting it. It emits Quran source references that map all
6,236 translated segments to the shared Quran canonical units. Saheeh
International is a translation and is not configured with a source-language
role.

## Running imports

From the repository root:

```bash
docker compose up -d postgres
uv sync --all-packages --frozen
uv run --package intertext-backend alembic --config backend/alembic.ini upgrade head
uv run --package intertext-ingest intertext-ingest import kjv
uv run --package intertext-ingest intertext-ingest import quran
uv run --package intertext-ingest intertext-ingest import quran-saheeh-international
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

`HttpFileSource`, `HttpZipSource`, `GitRepositorySource`, and `LocalSource` are currently available. None interprets textual references or canonical structure.

### New format

Implement the `SourceParser` protocol so it emits `ParsedSource` records containing generic segments and format-native `SourceReference` values. Add the corresponding source-reference interpretation to the responsible corpus mapper. Acquisition adapters, persistence, and release provenance do not change. Format-specific fields belong in source-reference components, normalized metadata, or semantic markup, not in persistence code.

### Different corpus

The Tanzil import demonstrates the different-corpus path: it uses the same acquisition, normalized records, persistence, provenance, idempotency, and generic validation infrastructure as the Bible imports, while supplying Quran XML parsing and a Quran-specific canonical mapper, reference scheme, coverage validator, and surah structure. Bible book/chapter/verse components are not required by the shared representation.
