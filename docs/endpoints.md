# Backend endpoints

The FastAPI backend serves the following application endpoints. Interactive OpenAPI documentation is available at `/docs`, with the schema at `/openapi.json`.

## Health

### `GET /health`

Returns the application health status.

```json
{"status": "ok"}
```

## Text library

### `GET /api/v1/texts`

Lists conceptual texts available in the library.

### `GET /api/v1/texts/{text_slug}/versions`

Lists versions of a conceptual text, including language metadata and the current release ID when one exists.

Returns `404` when `text_slug` does not exist.

### `GET /api/v1/texts/{text_slug}/versions/available`

Lists versions whose current release has at least one segment mapped to a
canonical unit in the requested section. The section is supplied with the
required `reference` query parameter and uses the same reference resolution as
the reader.

```http
GET /api/v1/texts/bible/versions/available?reference=Mark%201
```

This endpoint reports content availability, not complete range coverage. A
version with mapped content for only part of the requested range is included.
It returns an empty list when the reference is valid but no current version has
mapped content, `404` when the text or reference is unknown, and `422` when the
resolved canonical range is invalid.

## Structure navigation

### `GET /api/v1/texts/{text_slug}/structure`

Lists top-level structure nodes in ordinal order. For the Bible these are books; other corpora may use different node types.

Each item includes its ID, parent ID, node type, titles, ordinal, canonical path, depth, and covered canonical-unit ordinals.

### `GET /api/v1/texts/{text_slug}/structure/{node_id}/children`

Lists the direct children of a structure node in ordinal order. For example, use a Bible book node ID to retrieve its chapters. A valid leaf node returns an empty list.

Returns `404` if the text does not exist or the node does not belong to that text.

## Reference resolution

### `GET /api/v1/texts/{text_slug}/references/resolve`

Resolves a user-facing label through the text's default reference scheme.

Query parameters:

- `reference` — required reference label, such as `Mark 1`.

Example:

```http
GET /api/v1/texts/bible/references/resolve?reference=Mark%201
```

The response contains the original and normalized inputs, matched label and scheme, and canonical start/end unit IDs, keys, and ordinals.

Returns `404` when the text or reference is unknown, and `422` if a stored reference has an invalid canonical range.

## Reader

### `GET /api/v1/reader/{text_slug}/{reference}`

Returns canonical units and already-aligned version segments for a resolved reference.

Query parameters:

- `versions` — optional comma-separated version slugs. The response preserves the requested order and removes duplicates. When omitted, all versions with current releases are returned.

Example:

```http
GET /api/v1/reader/bible/Mark%201?versions=sblgnt,kjv
```

Returns `404` when the text, reference, or requested current version is unavailable. Returns `422` for an invalid canonical range or malformed `versions` value such as `kjv,,sblgnt`.
