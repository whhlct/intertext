# ADR 0004: Use Generic Text Versions, Preferred Source Roles, and Optional Provenance

- Status: Accepted
- Project: Intertext

## Context

Intertext must represent many kinds of textual representations.

For different corpora these may include:

- translations;
- critical editions;
- transcriptions;
- recensions;
- canonical readings;
- transliterations;
- other source-language editions.

The earlier idea of an `original` edition type is too strong and too ambiguous.

For many ancient texts:

- no autograph survives;
- multiple manuscript witnesses exist;
- multiple recensions/readings may exist;
- a scholarly critical text may reconstruct a reading;
- transmission may be substantially oral rather than manuscript-based.

A universal manuscript-witness hierarchy would also be too specific for corpora such as Hadith or Vedic texts.

## Decision

### 1. Use `TextVersion` as the universal representation concept

The universal model contains:

```text
Text
└── Text Versions
    └── Version Segments
```

Possible descriptive `version_type` values may include:

```text
translation
critical_edition
transcription
transliteration
recension
reading
other
```

The enum is descriptive and should not become a hard-coded behavioral taxonomy.

### 2. Do not use `original` as a universal version type

Intertext will not store a universal:

```text
is_original = true
```

or:

```text
original_edition_id
```

### 3. Resolve "Original Language" through range-specific preferred versions

Add a generic preferred-version mapping:

```text
preferred_versions

text_id
start_unit_id
end_unit_id
version_id
role
priority
```

The primary role is:

```text
default_source
```

This answers the product question:

> Which source-language version should Intertext show by default for this passage?

It does not assert that the selected version is the historical autograph/original.

### 4. Keep provenance generic and optional

Where needed, use:

```text
sources
version_sources
```

A source may be:

- manuscript;
- printed edition;
- digital edition;
- oral tradition;
- dataset;
- critical source;
- other.

Relationships may include:

- translated_from;
- transcribed_from;
- based_on;
- edited_from;
- derived_from;
- represents.

Relationships may be range-specific.

### 5. Keep corpus-specific scholarly data outside the universal core

Do not make manuscript witnesses, textual variants, isnads, Quranic reading traditions, or Vedic transmission structures universal tables.

Add specialized modules only when required by concrete features.

## Consequences

### Benefits

- Works across heterogeneous corpora.
- Avoids historically misleading "original edition" claims.
- Keeps the basic reader data model simple.
- Allows source-language defaults without requiring textual-criticism infrastructure.
- Leaves room for detailed provenance later.

### Costs

- The generic `TextVersion` concept is broader and therefore less semantically precise than corpus-specific terminology.
- Some corpus-specific features will require additional specialized tables later.
- A user-facing label such as "Original Language" must be documented carefully so it is not confused with "original manuscript."

## Implementation guidance

The initial schema should include:

```text
text_versions
preferred_versions
```

Generic provenance tables may be introduced when needed by actual imported datasets.

Do not implement manuscript-witness, variant-reading, or tradition-transmission schemas during the initial reader build unless a concrete product feature requires them.
