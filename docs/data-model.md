# Intertext Data Model

## 1. Core modeling principle

The most important design rule in Intertext is:

> A conceptual text, its canonical reference/alignment structure, and a particular text version are different entities.

Do not model the Bible as:

```text
verse
-----
book
chapter
verse
kjv_text
esv_text
greek_text
```

That model breaks down when:

- versions use different numbering;
- one version merges or splits textual units differently;
- passages are omitted or combined;
- non-Biblical texts use different structures;
- source-language linguistic data must be attached;
- different reference schemes coexist;
- a corpus has multiple source-language recensions/readings/editions.

Intertext instead uses a canonical representation to which version-specific segments are mapped.

## 2. What "canonical" means here

`canonical_unit` means:

> Intertext's normalized reference/alignment/progress unit.

It does **not** mean:

> the historically original wording or theologically authoritative reading.

A canonical unit identifies where content belongs in the conceptual text. Actual wording belongs to text versions.

## 3. Three levels of modeling

### Level 1 — universal model

Required across corpora:

```text
Text
Structure Node
Canonical Unit
Reference Scheme
Language
Text Version
Version Segment
Segment ↔ Canonical Unit Mapping
```

### Level 2 — generic optional metadata

Add when needed:

```text
Preferred Version
Source
Version ↔ Source Relationship
Version Coverage
```

### Level 3 — corpus-specific scholarly data

Add only when a feature requires it.

Examples:

```text
Bible / manuscript studies
- manuscript witnesses
- textual variants
- apparatus data

Quran
- reading traditions
- transmission metadata

Hadith
- isnad
- transmitters
- matn
- classification metadata

Vedic texts
- recension/shakha metadata
- oral transmission metadata
- accent/recitation information
```

Do not standardize these prematurely.

## 4. `texts`

Represents the conceptual corpus.

Examples:

- Bible;
- Quran;
- Sahih al-Bukhari;
- Rigveda.

Suggested fields:

```text
id                    UUID PK
slug                  text UNIQUE
title                 text
description           text nullable
default_reference_scheme_id UUID nullable
metadata              JSONB
created_at            timestamp
updated_at            timestamp
```

The schema must not assume every text has a book/chapter/verse hierarchy.

## 5. `structure_nodes`

Represents arbitrary hierarchical structure.

Examples:

Bible:

```text
Bible
└── New Testament
    └── Mark
        └── Chapter 1
```

Quran:

```text
Quran
└── Al-Baqarah
```

Hadith:

```text
Sahih al-Bukhari
└── Book
    └── Chapter
```

Rigveda:

```text
Rigveda
└── Mandala
    └── Hymn
```

Suggested fields:

```text
id                  UUID PK
text_id             UUID FK -> texts
parent_id           UUID FK -> structure_nodes nullable
node_type           text
title               text
short_title         text nullable
ordinal             integer
path                ltree or equivalent nullable
depth               integer
start_unit_ordinal  integer nullable
end_unit_ordinal    integer nullable
metadata            JSONB
```

Treat `node_type` as domain data, not as a reason to create universal tables for every corpus-specific structure.

## 6. `canonical_units`

Represents the smallest normalized internal unit used for alignment and progress tracking.

Suggested fields:

```text
id            UUID PK
text_id       UUID FK -> texts
ordinal       integer
internal_key  text
unit_type     text
metadata      JSONB
```

Example:

```text
internal_key      ordinal
bible.mark.1.1    ...
bible.mark.1.2    ...
bible.mark.1.3    ...
```

The internal key is not necessarily the reference shown to the user.

## 7. Reference schemes

Different traditions or versions may display references differently.

### `reference_schemes`

```text
id            UUID PK
text_id       UUID FK -> texts
name          text
description   text nullable
metadata      JSONB
```

### `reference_labels`

```text
id                   UUID PK
reference_scheme_id  UUID FK -> reference_schemes
start_unit_id        UUID FK -> canonical_units
end_unit_id          UUID FK -> canonical_units
label                text
normalized_label     text
sort_order           integer
metadata             JSONB
```

A reference label may point to a range of canonical units.

This allows numbering/boundary differences without changing the canonical core.

## 8. `languages`

Suggested fields:

```text
id           UUID PK
iso_code     text
name         text
native_name  text nullable
script       text nullable
direction    text        # ltr / rtl
metadata     JSONB
```

Rendering direction should be data-driven.

## 9. `text_versions`

Represents a user-selectable or system-addressable representation of a conceptual text.

Examples may include:

- translation;
- critical edition;
- transcription;
- transliteration;
- recension;
- reading;
- other digital/source-language edition.

Suggested fields:

```text
id                   UUID PK
text_id              UUID FK -> texts
slug                 text
title                text
abbreviation         text nullable
default_language_id  UUID FK -> languages
reference_scheme_id  UUID FK -> reference_schemes nullable
version_type         text
publisher            text nullable
publication_year     integer nullable
source_name          text nullable
license              text nullable
rights_statement     text nullable
source_url           text nullable
metadata             JSONB
created_at           timestamp
updated_at           timestamp
```

Possible `version_type` values may initially include:

```text
translation
critical_edition
transcription
transliteration
recension
reading
other
```

This field is descriptive metadata.

Core reader logic should not rely on every future corpus fitting perfectly into this enum.

### Important terminology rule

Do not use `original` as a universal `version_type`.

A surviving manuscript, a critical edition, a recension, and a canonical reading tradition are not all the same concept.

## 10. `version_releases`

Separates the logical version from an exact imported revision.

Suggested fields:

```text
id            UUID PK
version_id    UUID FK -> text_versions
version_label text
source_sha256 text
imported_at   timestamp
is_current    boolean
metadata      JSONB
```

This allows corrected imports or source updates without silently mutating historical data.

It also makes generated embeddings reproducible.

## 11. `version_segments`

Stores actual version text.

Suggested fields:

```text
id                 UUID PK
version_release_id UUID FK -> version_releases
language_id        UUID FK -> languages
sequence           integer
text_plain         text
content_markup     JSONB
block_type         text nullable
source_identifier  text nullable
metadata           JSONB
```

Do not use rendered HTML as the authoritative stored representation.

`content_markup` may preserve semantic information such as:

- paragraph boundaries;
- poetry;
- footnotes;
- headings;
- source formatting spans;
- editorial notes.

Rendering belongs in the frontend.

## 12. `segment_unit_mappings`

This table enables side-by-side reading.

Suggested fields:

```text
segment_id         UUID FK -> version_segments
canonical_unit_id  UUID FK -> canonical_units
sequence           integer
mapping_type       text
confidence         numeric nullable
source             text nullable
metadata           JSONB
```

The model must support:

```text
one segment -> one canonical unit
one segment -> multiple canonical units
multiple segments -> one canonical unit
```

Do not assume all versions have perfect 1:1 verse boundaries.

## 13. Preferred source-language versions

Intertext needs to answer a product question:

> What version should be shown when the user requests the source-language text for this passage?

This is not the same as claiming a version is historically "the original."

Suggested table:

```text
preferred_versions

id             UUID PK
text_id        UUID FK -> texts
start_unit_id  UUID FK -> canonical_units
end_unit_id    UUID FK -> canonical_units
version_id     UUID FK -> text_versions
role           text
priority       integer
notes          text nullable
metadata       JSONB
```

Suggested roles:

```text
default_source
alternate_source
```

Example:

```text
Bible
├── one canonical range -> configured Hebrew/Aramaic source version
└── another canonical range -> configured Greek source version
```

The UI may label `default_source` as **Original Language**, but code and documentation should not call the selected version "the original edition."

## 14. Generic provenance

Provenance should be available without forcing every corpus into a manuscript-centric model.

### `sources`

Suggested fields:

```text
id            UUID PK
source_type   text
title         text
description   text nullable
date_label    text nullable
repository    text nullable
shelfmark     text nullable
source_url    text nullable
license       text nullable
metadata      JSONB
```

Possible `source_type` values:

```text
manuscript
printed_edition
digital_edition
oral_tradition
critical_source
dataset
other
```

### `version_sources`

Represents the relationship between a text version and a source/provenance record.

Suggested fields:

```text
id                UUID PK
version_id        UUID FK -> text_versions
source_id         UUID FK -> sources
relationship_type text
start_unit_id     UUID FK -> canonical_units nullable
end_unit_id       UUID FK -> canonical_units nullable
notes             text nullable
metadata          JSONB
```

Possible relationship types:

```text
translated_from
transcribed_from
based_on
edited_from
derived_from
represents
```

The relationship may be range-specific.

### Why this is optional

The normal reader does not need detailed provenance to retrieve aligned passages.

A version can exist and be read before complete source metadata is available.

This prevents scholarly provenance complexity from infecting the core reading model.

## 15. Version coverage

If useful, explicit coverage may be recorded:

```text
version_coverage

id             UUID PK
version_id     UUID FK -> text_versions
start_unit_id  UUID FK -> canonical_units
end_unit_id    UUID FK -> canonical_units
coverage_type  text nullable
metadata       JSONB
```

This is especially useful for partial transcriptions, fragmentary sources, or versions that cover only part of a conceptual text.

Do not require it when coverage is obvious from segment mappings.

## 16. Source-language tokens

Suggested fields:

```text
tokens

id             UUID PK
segment_id     UUID FK -> version_segments
token_index    integer
surface        text
normalized     text nullable
char_start     integer nullable
char_end       integer nullable
language_id    UUID FK -> languages
lexeme_id      UUID FK -> lexemes nullable
is_word        boolean
is_punctuation boolean
metadata       JSONB
```

Character offsets are useful for stable selections and source reconstruction.

## 17. `lexemes`

A token is an occurrence. A lexeme is the dictionary-level lexical item.

Suggested fields:

```text
id                  UUID PK
language_id         UUID FK -> languages
lemma               text
normalized_lemma    text nullable
transliteration     text nullable
part_of_speech      text nullable
metadata            JSONB
```

External identifiers should be stored through general identifier/provenance mechanisms rather than baked into the universal schema.

## 18. `token_glosses`

Supports interlinear translation.

Suggested fields:

```text
id                  UUID PK
token_id            UUID FK -> tokens
target_language_id  UUID FK -> languages
enrichment_import_id UUID FK -> enrichment_imports
gloss               text
gloss_type          text
source              text nullable
confidence          numeric nullable
metadata            JSONB
```

Possible `gloss_type` values:

```text
literal
contextual
dictionary
generated
```

A human-curated gloss and generated gloss must remain distinguishable.

`enrichment_imports` records an enrichment's target release, type, provider
label, resolved source revision, SHA-256 checksum, parser version, import time,
complete source metadata, and alignment diagnostics. This keeps token-level
provenance separate from the authoritative `VersionRelease` while making an
enrichment import idempotent and reproducible.

## 19. Morphology

A flexible morphology model is required because languages differ.

Suggested:

```text
token_morphology

id        UUID PK
token_id  UUID FK -> tokens
features  JSONB
source    text nullable
metadata  JSONB
```

Common fields may later be promoted to columns if query needs justify it.

Do not force every language into one language's grammatical schema.

## 20. `span_alignments`

Word/phrase translation alignment must support many-to-many spans.

Suggested fields:

```text
id                    UUID PK
source_segment_id     UUID FK -> version_segments
source_start_token    integer
source_end_token      integer
target_segment_id     UUID FK -> version_segments
target_start_token    integer
target_end_token      integer
alignment_type        text nullable
confidence            numeric nullable
source                text nullable
metadata              JSONB
```

This supports:

- 1 word -> 1 word;
- 1 word -> several words;
- several words -> 1 word;
- phrase -> phrase;
- source span -> no direct target span.

Do not model alignment as one token foreign key to another.

## 21. Annotations

Bookmarks, notes, and highlights share an annotation concept.

### `annotations`

```text
id          UUID PK
user_id     UUID FK -> users
type        text
body        text nullable
color       text nullable
created_at  timestamp
updated_at  timestamp
metadata    JSONB
```

### `annotation_anchors`

```text
id                 UUID PK
annotation_id      UUID FK -> annotations
text_id            UUID FK -> texts

start_unit_id      UUID FK -> canonical_units
end_unit_id        UUID FK -> canonical_units

version_release_id UUID FK -> version_releases nullable

start_token_id     UUID FK -> tokens nullable
end_token_id       UUID FK -> tokens nullable

metadata           JSONB
```

This allows translation-independent and version/token-specific annotations.

## 22. Reading position

Reading position answers:

> Where should the reader reopen?

Suggested table:

```text
reading_positions

user_id            UUID FK -> users
text_id            UUID FK -> texts
version_id         UUID FK -> text_versions nullable
canonical_unit_id  UUID FK -> canonical_units
segment_id         UUID FK -> version_segments nullable
token_index        integer nullable
scroll_fraction    numeric nullable
updated_at         timestamp
```

The selected version may be stored for UX restoration, but completion/progress remains canonical.

## 23. Reading progress

Suggested table:

```text
user_unit_progress

user_id            UUID FK -> users
text_id            UUID FK -> texts
canonical_unit_id  UUID FK -> canonical_units
status              text
first_read_at       timestamp nullable
last_read_at        timestamp nullable
```

Progress for any structure node can be derived from its canonical-unit range.

Progress is version-independent.

## 24. Entities and cross-references

### `entities`

```text
id              UUID PK
entity_type     text
canonical_name  text
description     text nullable
metadata        JSONB
```

### `entity_names`

```text
id           UUID PK
entity_id    UUID FK -> entities
language_id  UUID FK -> languages nullable
name         text
name_type    text nullable
metadata     JSONB
```

### `entity_mentions`

```text
id                 UUID PK
entity_id          UUID FK -> entities
segment_id         UUID FK -> version_segments
canonical_unit_id  UUID FK -> canonical_units nullable
start_token        integer nullable
end_token          integer nullable
source             text nullable
confidence         numeric nullable
metadata           JSONB
```

### `cross_references`

```text
id                    UUID PK

source_text_id        UUID FK -> texts
source_start_unit_id  UUID FK -> canonical_units
source_end_unit_id    UUID FK -> canonical_units

target_text_id        UUID FK -> texts
target_start_unit_id  UUID FK -> canonical_units
target_end_unit_id    UUID FK -> canonical_units

relation_type         text nullable
description           text nullable
source                text nullable
metadata              JSONB
```

Cross references are deliberately cross-corpus capable.

## 25. Supplementary resources

### `resources`

```text
id             UUID PK
title          text
author         text nullable
publisher      text nullable
publication_date text/date nullable
license        text nullable
resource_type  text
metadata       JSONB
```

Possible types:

```text
commentary
dictionary
lexicon
study_notes
historical_source
```

### `resource_entries`

```text
id             UUID PK
resource_id    UUID FK -> resources
start_unit_id  UUID FK -> canonical_units nullable
end_unit_id    UUID FK -> canonical_units nullable
title          text nullable
content        text
metadata       JSONB
```

Primary text and supplementary material must remain distinguishable.

## 26. Source imports

Suggested table:

```text
source_imports

id              UUID PK
source_name     text
source_uri      text nullable
license         text nullable
sha256          text
imported_at     timestamp
parser_version  text
status          text
metadata        JSONB
```

Preserve original imported files in durable object storage or an equivalent source archive.

## 27. RAG chunks

AI functionality should point back to canonical passages.

Suggested table:

```text
rag_chunks

id                  UUID PK
text_id             UUID FK -> texts
version_release_id  UUID FK -> version_releases nullable

start_unit_id       UUID FK -> canonical_units
end_unit_id         UUID FK -> canonical_units

resource_entry_id   UUID FK -> resource_entries nullable

chunk_type          text
content             text
token_count         integer nullable
content_hash        text

embedding_model     text nullable
embedding           vector nullable
search_vector       tsvector nullable

metadata            JSONB
created_at          timestamp
```

Do not make one verse the only embedding granularity.

AI citations should resolve back to canonical units.

## 28. Recommended initial model subset

Start with:

```text
texts
structure_nodes
canonical_units
reference_schemes
reference_labels
languages
text_versions
version_releases
version_segments
segment_unit_mappings
preferred_versions
```

Then add:

```text
users
annotations
annotation_anchors
reading_positions
user_unit_progress
```

Then:

```text
tokens
lexemes
token_glosses
token_morphology
span_alignments
```

Add generic provenance when the first imported datasets require it:

```text
sources
version_sources
version_coverage
```

Then:

```text
entities
entity_mentions
cross_references
resources
resource_entries
```

Finally:

```text
rag_chunks
```

Corpus-specific scholarly tables should only be introduced when a concrete feature requires them.

## 29. Indexing considerations

Likely important indexes include:

- `texts.slug`;
- `(text_id, ordinal)` on canonical units;
- `internal_key` on canonical units;
- `(version_release_id, sequence)` on segments;
- `segment_unit_mappings.canonical_unit_id`;
- `(segment_id, token_index)` on tokens;
- `(text_id, start_unit_id, end_unit_id, role)` or equivalent lookup support for preferred versions;
- annotation anchors by user + canonical range;
- reading progress by user + text + canonical unit;
- GIN indexes for selected JSONB/search columns where justified;
- vector index only after embeddings are introduced and search volume warrants it.

Avoid speculative indexes on every column.
