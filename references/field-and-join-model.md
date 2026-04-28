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
- `Entertainment data service`
- `Program endpoint`
- `ProgramAvailability endpoint`
- `ProgramAvailability.media`

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
| `AssetType` | Media asset/rendition type lookup | `id`, `guid`, `title`, `ownerId` |
| `Category` | Media category lookup | `id`, `guid`, `title`, `ownerId` |
| `Field` | Media custom field metadata | `id`, `guid`, `fieldName`, `searchFieldName`, `ownerId` |
| `MediaFileField` | MediaFile custom field metadata | `id`, `guid`, `fieldName`, `searchFieldName`, `ownerId` |
| `Provider` | Provider/config lookup | `id`, `guid`, `title`, `ownerId` |
| `Release` | Delivery/release records | `id`, `guid`, `mediaId`, `fileId`, `delivery`, `url`, `approved` |
| `Server` | Storage/server config | `id`, `guid`, `title`, `ownerId`, `disabled` |

## Entertainment Data Service Objects

The local ENTERTAINMENT dumps verified these object families, but the live Entertainment base URL is not yet committed in `service-map.json`. Confirm the base URL before live calls.

| Object | Use For | Starter Fields |
| --- | --- | --- |
| `Program` | Program/title/episode metadata | `id`, `guid`, `title`, `ownerId`, `approved`, `programType`, `seriesId`, `tvSeasonId`, `imageMediaIds` |
| `ProgramAvailability` | Availability-aware program records and Media bridges | `id`, `guid`, `title`, `approved`, `media`, `mediaCount`, `distributionRightIds`, `distributionRights`; live schema 2.0 can expose program fields as `plprogram$...` |
| `Credit` | Person-to-program/season credits | `id`, `guid`, `personId`, `programId`, `tvSeasonId`, `creditType`, `characterName` |
| `Person` | Person metadata | `id`, `guid`, `title`, `aliases`, `credits`, `imageMediaIds` |
| `Tag` | Entertainment tag lookup | `id`, `guid`, `title`, `scheme` |
| `TvSeason` | Season-level metadata | `id`, `guid`, `title`, `seriesId`, `seriesTitle`, `tvSeasonNumber` |
| `Station` | Station lookup/config | `id`, `guid`, `title` when available |

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
- `Program` means `Media`; CVP Entertainment has a distinct `Program` object.

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

### Bridge Entertainment ProgramAvailability to Media

1. Query `ProgramAvailability` only after confirming the Entertainment base URL.
2. Start with `schema=2.0` when schema 1.x returns only sparse identity fields. Live program fields may be namespaced, for example `plprogram$programType`, `plprogram$seriesId`, `plprogram$tvSeasonNumber`, `plprogram$tvSeasonEpisodeNumber`, and `plprogram$seriesEpisodeNumber`.
3. Request `id,guid,title,ownerId` plus needed `plprogram$...` fields and any available `media` bridge fields.
4. Inspect the returned `media` shape before joining. Do not assume `ProgramAvailability.media` is present in a live field projection just because local datadumps included it.
5. If `media` is absent, resolve `Media` by matching `ProgramAvailability.guid` to `Media.guid`; prefer `ownerId` matches when multiple Media records are returned.
6. Use the resolved `Media.id` for file joins.
7. Report ProgramAvailability state separately from Media availability state. Fields such as `availableDate`, `expirationDate`, and Media approval should usually be taken from the resolved `Media` record when the ProgramAvailability response does not carry them directly.

### Join Media to MediaFile

1. Resolve the owning `Media.id`.
2. Query `MediaFile` with the confirmed media reference filter, such as `byMediaId=<Media.id>` where supported.
3. Do not assume `q` search or generic `byField` lookup is enabled for `MediaFile`; verify endpoint behavior before using either.
4. For mezzanine reports, filter file records where content type is video and `assetTypes` / `plfile$assetTypes` contains the required mezzanine value.

### Find Artwork/Image Media

1. Query `Media` with explicit image/content fields.
2. Prefer documented filters such as content type or asset type only after confirming syntax.
3. Request `content.contentType,content.height,content.width,content.format,content.assetTypes,content.title,content.url,content.aspectRatio` only when those fields are needed.
4. Treat URL/path fields as sensitive in outputs.

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
