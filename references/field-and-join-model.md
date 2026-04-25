# Field and Join Model

CVP field naming and endpoint relationships are not intuitive. Use this maintained doc as the baseline for read-only query planning, then verify endpoint-specific behavior against docs and returned data.

Sources are indexed in `references/cvp-docs/data-services-catalog.json`; especially:

- `Media endpoint`
- `Media object`
- `Retrieving Media objects`
- `Using media filters`
- `Using the q query to search for Media objects`
- `Media.thumbnails`
- `MediaFile endpoint`
- `MediaFile object`
- `AccountSettings endpoint (Media)`
- `AccountSettings object (Media)`
- `MediaDefaults endpoint`
- `MediaDefaults object`
- `Custom fields API reference`
- `Media data service object schema history`

## Baseline Identity Fields

For most CVP Data Service objects, start by checking these fields:

| Field | Purpose | Notes |
| --- | --- | --- |
| `id` | Data Services object identity | Treat as the canonical object reference. |
| `guid` | Stable external-ish identifier when present | Useful for exact lookup and user handoff, but still endpoint-specific. |
| `ownerId` | Owning account/context | Required for disambiguation and access-scope checks. |
| `added` | Creation timestamp | Useful for duplicate or freshness analysis. |
| `updated` | Last update timestamp | Useful for troubleshooting stale metadata. |
| `title` | User-facing label on Media-like objects | Not guaranteed unique. Use for display and discovery, not identity. |

## Media Data Service Objects

| Object | Use For | Starter Fields |
| --- | --- | --- |
| `Media` | Title-level media metadata and top-level publishing/availability context | `id`, `guid`, `title`, `ownerId`, `added`, `updated` |
| `MediaFile` | File-level technical and rendition metadata | `id`, `guid`, `title`, `ownerId`, `added`, `updated`, plus confirmed media reference fields |
| `MediaDefaults` | Account-level Media defaults | `id`, `guid`, `ownerId` |
| `AccountSettings` | Media service account settings | `id`, `guid`, `ownerId` |

## Join Discipline

When moving between endpoints:

1. Preserve the source endpoint, source `id`, source `guid`, and display label.
2. Identify the exact reference field from docs or returned data.
3. Query the owning target endpoint with exact lookup.
4. Include target `id`, `guid`, label, and requested target fields.
5. Record each join row as `resolved`, `missing`, `ambiguous`, or `unverified`.

Do not assume:

- Console labels equal API field names.
- `title` is unique.
- `guid` exists on every object.
- a field ending in `Id` points to the object you expect.
- a relationship field on `Media` has the file fields the user wants.

## Common Query Plans

### Find Media by GUID

1. Query `Media` with `byField=guid|...` only after confirming support.
2. Request `id,guid,title,ownerId,added,updated`.
3. If no row is returned, report the miss and ask before broadening to `q`.

### Find Media by Title

1. Query `Media` with `q` search.
2. Request identity, title, owner, and timestamps.
3. If multiple rows are returned, ask for owner/account/date disambiguation or return a compact candidate table.

### Explain File-Level State for a Title

1. Resolve the `Media` record first.
2. Identify the documented Media-to-MediaFile reference field.
3. Query `MediaFile` using the confirmed reference field.
4. Join results locally and mark unresolved file references.

### Audit Metadata Completeness

1. Define the required fields explicitly.
2. Query only the records in scope.
3. Include identity fields plus required metadata fields.
4. Treat missing field, null field, empty string, and empty array as separate states when relevant.
5. Save a CSV only when requested.

## Maintenance Notes

When a live response reveals a verified field or relationship:

1. Add it to this doc with the endpoint and verification date.
2. Add the field to `service-map.json` only if it is generally useful and non-sensitive.
3. Keep customer-specific notes in a private local doc, not this public repo.
