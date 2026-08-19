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

Providers, formats, and corpora are independent. The eBible adapter happens to deliver USFM, the Faithlife Git adapter delivers SBLGNT XML, the Open Scriptures Git adapter delivers OSIS XML, and Tanzil delivers Quran XML and pipe-delimited translation text. Format parsers emit format-native `SourceReference` values and do not construct Intertext canonical references. The responsible corpus mapper interprets those values and emits resolved canonical targets. Persistence receives only the resolved version and canonical unit IDs; it contains no provider-, format-, or corpus-specific behavior.

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

### TAGNT contextual gloss enrichment

- Repository: `https://github.com/STEPBible/STEPBible-Data.git`
- Input path: `Translators Amalgamated OT+NT/`
- Provider: STEP Bible Git repository
- Format: TAGNT 17-column tab-delimited records
- Target: the current SBLGNT release and its existing token stream
- License: Creative Commons Attribution 4.0 International

TAGNT is an enrichment source, not an authoritative text version. It never
creates or replaces an SBLGNT `TextVersion`, `VersionRelease`, or segment.
The parser retains source references, surfaces, lemmas, dictionary glosses,
contextual English glosses, grammatical analysis, edition memberships and
movement markers, source filenames, and line numbers.

Alignment is performed independently within each canonical verse. Only TAGNT
readings marked for SBL are considered. Greek comparison is diacritic- and
punctuation-insensitive and includes explicit movable-nu equivalence, while
stored SBLGNT surfaces remain unchanged. The aligner uses the complete token
sequence and tests TAGNT's base and edition-displacement orders. A mismatch or
more than one possible match fails strict mode; glosses are never attached by
unchecked row position.

Strict mode is the default. `--allow-partial` skips an entire verse when it
cannot be aligned uniquely and records its reference and diagnostic in the
`enrichment_imports` provenance row. This is needed for the current upstream
combination because TAGNT and SBLGNT have a small number of edition-membership,
token-boundary, and versification disagreements, including the SBLGNT-bracketed
Mark 16:9–20 and John 7:53–8:11 passages. No partial glosses are written for a
skipped verse.

### Open Scriptures Hebrew Bible / WLC

- Repository: `https://github.com/openscriptures/morphhb.git`
- Input path: `wlc/`
- Provider: Open Scriptures Git repository
- Format: OSIS XML using the OSHB profile
- Source metadata: WLC 4.20 and the repository's 2018.12.14 full-morphology release
- License: WLC text is Public Domain; OSHB lemma and morphology data are CC BY 4.0

The importer records the resolved Git commit and a deterministic checksum of
that commit. OSIS book identifiers remain parser-native until `BibleMapper`
resolves them to Intertext Bible book, chapter, and verse units. The version is
configured as `default_source` across its Old Testament coverage.

OSHB word surfaces, immutable word IDs, lemmas, morphology, optional `n`
cantillation-hierarchy values, ketiv/qere structures, notes, and OSIS
attributes are retained in normalized token and semantic-markup records. Token
tables are not populated yet. Display text removes only the source's `/`
morpheme delimiter and applies spacing around OSIS segments such as maqqef; the
raw word surface remains available in markup. No Unicode normalization,
including NFC, is applied because reordering Hebrew points and cantillation
marks would change the authoritative encoding.

References currently preserve the WLC/MT chapter and verse numbering expressed
by the OSIS files. The repository's separate `VerseMap.xml` documents places
where this differs from KJV numbering; segment-level cross-versification for
those exceptional ranges should be modeled as explicit many-to-many mappings
rather than rewriting the source text.

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
uv run --package intertext-ingest intertext-ingest import oshb
uv run --package intertext-ingest intertext-ingest import quran
uv run --package intertext-ingest intertext-ingest import quran-saheeh-international
uv run --package intertext-ingest intertext-ingest import sblgnt
uv run --package intertext-ingest intertext-ingest enrich tagnt-sblgnt --allow-partial
```

By default raw artifacts are stored below `data/raw/` and ignored by Git. Use `--raw-dir` to select another archive location. Cached artifacts are reused unless `--refresh` is supplied:

```bash
uv run --package intertext-ingest intertext-ingest import sblgnt --refresh
uv run --package intertext-ingest intertext-ingest enrich tagnt-sblgnt --refresh --allow-partial
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

The same data is copied into `version_releases.metadata.source`, together with importer and parser versions. Enrichment acquisitions are instead copied into `enrichment_imports.metadata.source`, with the target release, alignment edition, parser version, and any skipped-verse diagnostics. HTTP archives are stored by checksum so refreshed downloads do not overwrite older artifacts. Git checkouts retain the resolved commit SHA, and the checksum is computed from a deterministic `git archive` of that commit.

An already imported version/checksum is a no-op. A new checksum creates a new immutable `VersionRelease`, retains the old release and segments, and becomes the sole current release.

An identical enrichment checksum for the same target release is also a no-op.
A different TAGNT revision creates a separate enrichment provenance record and
set of `TokenGloss` rows; it does not mutate the SBLGNT release.

## Extension points

### New provider using an existing format

Implement the `SourceAdapter` acquisition protocol and register a `DatasetDefinition` with the existing parser. For example, a publisher API returning USFM would require a new source adapter but would reuse `UsfmParser`, normalization, mapping, persistence, and validation.

`HttpFileSource`, `HttpZipSource`, `GitRepositorySource`, and `LocalSource` are currently available. None interprets textual references or canonical structure.

### New format

Implement the `SourceParser` protocol so it emits `ParsedSource` records containing generic segments and format-native `SourceReference` values. Add the corresponding source-reference interpretation to the responsible corpus mapper. Acquisition adapters, persistence, and release provenance do not change. Format-specific fields belong in source-reference components, normalized metadata, or semantic markup, not in persistence code.

### Different corpus

The Tanzil import demonstrates the different-corpus path: it uses the same acquisition, normalized records, persistence, provenance, idempotency, and generic validation infrastructure as the Bible imports, while supplying Quran XML parsing and a Quran-specific canonical mapper, reference scheme, coverage validator, and surah structure. Bible book/chapter/verse components are not required by the shared representation.
