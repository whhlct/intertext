# ADR 0003: Use a Canonical Text Model Separate from Text Versions

- Status: Accepted
- Project: Intertext

## Context

Intertext begins with the Bible but must eventually support multiple religious texts and textual traditions.

The application must support:

- multiple translations side by side;
- source-language versions;
- translation alignment;
- different reference/numbering schemes;
- progress tracking independent of version;
- notes/bookmarks on passages;
- word-level lexical data;
- references and AI citations.

A simple schema such as:

```text
verse
├── book
├── chapter
├── verse
├── kjv_text
├── esv_text
└── greek_text
```

would be easy for an initial Bible prototype but create long-term architectural problems.

## Decision

Separate:

1. conceptual text;
2. canonical structure;
3. canonical units;
4. reference schemes;
5. text versions;
6. version segments;
7. mappings between version segments and canonical units.

Conceptually:

```text
Text
├── canonical structure
│   └── canonical units
│
└── text versions
    └── segments
        └── segment-unit mappings
```

## Canonical does not mean "original wording"

A canonical unit is Intertext's normalized alignment/reference/progress unit.

Example:

```text
bible.mark.1.1
bible.mark.1.2
```

It identifies location, not authoritative wording.

Actual wording exists only in text versions.

## Reference schemes

Displayed references are represented separately and may map to ranges of canonical units.

This allows differences in numbering or textual boundaries.

## Version mapping

Version segments map to canonical units through an explicit mapping table.

This supports:

- one segment -> one unit;
- one segment -> multiple units;
- multiple segments -> one unit.

The system must not require perfect 1:1 verse mapping.

## Consequences

### Side-by-side reading

The backend requests a canonical range and retrieves all selected version segments mapped to it.

### Progress

Progress is recorded against canonical units.

Switching versions does not create separate progress histories.

### Annotations

Passage-level annotations can be canonical and version-independent.

Token/version-specific annotations can additionally anchor to version/token data.

### AI citations

RAG chunks point back to canonical ranges, allowing citations to navigate into the reader.

### Multi-corpus support

The same model can support corpora whose hierarchy is not book/chapter/verse.

## Tradeoffs

- More tables/joins than a Bible-only schema.
- Importers must map source structures to canonical units.
- Some corpus-specific reference complexity remains unavoidable.

These costs are accepted because they prevent Intertext from being fundamentally coupled to one translation or textual tradition.
