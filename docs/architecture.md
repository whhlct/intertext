# Intertext Architecture

## 1. Overview

Intertext is a monorepo containing three major application concerns:

1. **Frontend**
   - reading/study application;
   - side-by-side reader;
   - annotations and progress;
   - source-language interactions;
   - eventually AI chat.

2. **Backend**
   - FastAPI runtime API;
   - authentication/authorization;
   - canonical reference resolution;
   - passage retrieval;
   - version alignment;
   - annotations and progress;
   - search;
   - eventually AI retrieval/orchestration.

3. **Ingestion**
   - imports external text datasets;
   - parses source formats;
   - normalizes text and references;
   - populates canonical structure;
   - creates text versions and segments;
   - tokenizes source-language text;
   - attaches linguistic information;
   - creates alignments;
   - records provenance;
   - validates imported data;
   - eventually generates RAG chunks and embeddings.

The runtime backend must not become the place where heavy ingestion logic lives.

## 2. High-level system

```text
                    ┌─────────────────────────┐
                    │        Frontend         │
                    │ Next.js / React / TS    │
                    └────────────┬────────────┘
                                 │ HTTP/JSON
                                 ▼
                    ┌─────────────────────────┐
                    │         FastAPI         │
                    │    Runtime backend      │
                    └────────────┬────────────┘
                                 │
                   ┌─────────────┼─────────────┐
                   │             │             │
                   ▼             ▼             ▼
             PostgreSQL     Object storage   Redis
             canonical       raw sources     later
             application
             data
                   ▲
                   │
          ┌────────┴────────┐
          │    Ingestion    │
          │ Python package  │
          └─────────────────┘
```

Later, PostgreSQL may additionally hold:

```text
PostgreSQL
├── relational data
├── full-text search
└── pgvector embeddings
```

A dedicated search or vector service should only be introduced if measured scale or search requirements justify it.

## 3. Universal domain model

The core model should stay small and corpus-agnostic:

```text
Text
├── Structure Nodes
│   └── Canonical Units
│
├── Reference Schemes
│
└── Text Versions
    └── Version Segments
        ↕
      Canonical Units
```

This layer must work for the Bible, Quran, Hadith, Vedic texts, and future corpora.

It should not require universal concepts such as:

- verse;
- book;
- manuscript;
- codex;
- critical apparatus;
- isnad;
- recension.

Those may exist as corpus-specific or optional metadata, not universal structure.

## 4. Text versions

`TextVersion` is the universal representation concept.

Examples include:

- translation;
- critical edition;
- transcription;
- transliteration;
- recension;
- reading;
- another digital/source-language edition.

The runtime reader should treat all of these uniformly when retrieving aligned text.

`version_type` is descriptive metadata. Core reader behavior should not depend heavily on a closed set of version types.

### Source-language selection

Intertext should not store an `original_edition`.

Instead, a range-specific preferred-version mapping identifies what the product should show when a user requests the source-language text:

```text
Canonical range
    └── preferred version
          role = default_source
```

This is a product configuration, not a historical claim.

## 5. Provenance and corpus-specific scholarship

Version provenance is optional and generic:

```text
Text Version
    └── Version Source Relationship
            └── Source
```

A source may represent:

- manuscript;
- printed edition;
- digital edition;
- oral tradition;
- dataset;
- critical source;
- other.

The relationship describes the meaning:

- translated_from;
- transcribed_from;
- based_on;
- edited_from;
- derived_from;
- represents.

Do not require every corpus to use manuscript-oriented provenance.

Corpus-specific scholarly structures are added only when features require them.

Examples:

```text
Bible / manuscript studies
- manuscript witnesses
- textual variants
- critical apparatus

Quran
- reading traditions
- transmission metadata
- Quran-specific variant structures

Hadith
- isnad
- transmitters
- matn
- authenticity/classification metadata

Vedic texts
- shakha / recension metadata
- oral transmission metadata
- accent/recitation information
```

These are Level 3 domain extensions, not the Level 1 universal model.

## 6. Backend layering

Preferred runtime layering:

```text
FastAPI route
    ↓
service/domain layer
    ↓
specialized query or repository layer
    ↓
SQLAlchemy
    ↓
PostgreSQL
```

### `api/`

Responsibilities:

- HTTP routing;
- dependency injection;
- authentication dependencies;
- request/response mapping;
- status codes.

Routes should remain thin.

### `services/`

Responsibilities:

- business/domain behavior;
- reference resolution;
- reader composition;
- version selection;
- preferred-source resolution;
- annotations/progress orchestration;
- AI orchestration later.

### `queries/`

Use for sophisticated reads that do not map naturally onto CRUD-style repository methods.

Especially:

- retrieve a canonical range;
- retrieve segments for N selected versions;
- retrieve source-language tokens;
- retrieve annotations anchored to a range;
- retrieve cross-references;
- resolve preferred source versions by range.

### `repositories/`

Use selectively for conventional entity-oriented operations.

Good examples:

- annotation CRUD;
- user retrieval;
- reading-position persistence.

Do not create a repository for every table simply to conform to a pattern.

### `models/`

SQLAlchemy persistence models only.

### `schemas/`

Pydantic request/response models only.

API schemas may intentionally differ substantially from persistence models.

## 7. Reader architecture

The reader is driven by canonical units.

Conceptually:

```text
Canonical unit: Mark 1:1
    ├── Greek source-version segment
    ├── Translation A segment
    └── Translation B segment

Canonical unit: Mark 1:2
    ├── Greek source-version segment
    ├── Translation A segment
    └── Translation B segment
```

The backend must return already-aligned data.

The frontend should not fetch unrelated version payloads and attempt to align them itself.

A reader response may resemble:

```json
{
  "text": {
    "id": "bible",
    "title": "Bible"
  },
  "reference": {
    "label": "Mark 1",
    "start": "bible.mark.1.1",
    "end": "bible.mark.1.45"
  },
  "versions": [
    {
      "id": "greek-source",
      "name": "Configured Greek Source Version",
      "language": "grc",
      "roles": ["default_source"]
    },
    {
      "id": "kjv",
      "name": "King James Version",
      "language": "en"
    }
  ],
  "units": [
    {
      "id": "bible.mark.1.1",
      "label": "1",
      "segments": {
        "greek-source": {
          "text": "...",
          "tokens": []
        },
        "kjv": {
          "text": "The beginning of the gospel..."
        }
      }
    }
  ]
}
```

Exact response shapes may evolve, but backend canonical alignment should not.

## 8. Frontend reader composition

Suggested component hierarchy:

```text
Reader
├── ReaderToolbar
├── ReaderNavigation
├── ReaderColumn × N
│   └── Passage
│       └── TextUnit
│           └── Token
├── AnnotationPanel
├── ReferencePanel
└── ChatPanel          # later
```

Use generic names such as `TextUnit` or `CanonicalUnit` internally rather than making Bible-specific terms such as `Verse` foundational.

UI labels can remain corpus-specific.

## 9. Search

Expected progression:

1. structured reference lookup;
2. PostgreSQL full-text search;
3. lexical/entity search;
4. hybrid search;
5. vector retrieval with pgvector.

Do not make embeddings the only search representation.

## 10. AI architecture

AI is a later layer.

### Whole-text chat

```text
question
    ↓
query analysis
    ↓
hybrid retrieval
    ├── vector similarity
    ├── full-text search
    └── structured filters
    ↓
canonical passages
    ↓
LLM
    ↓
answer + clickable passage citations
```

### Section chat

The reader's currently visible canonical range should be provided directly as high-priority context.

If the question requires broader context, the same corpus-level retriever may be used.

### Commentary

Supplementary resources must be tagged separately from primary text.

The AI layer should support modes such as:

- primary text only;
- primary text + commentary.

It should not silently blur those sources.

## 11. Infrastructure principles

Start simple.

Initial local environment:

```text
PostgreSQL
FastAPI
Next.js
```

Add only when justified:

- Redis;
- background task worker;
- object storage service;
- pgvector;
- reverse proxy;
- managed cloud infrastructure.

Prefer a modular monolith over microservices in the early and middle stages of the project.
