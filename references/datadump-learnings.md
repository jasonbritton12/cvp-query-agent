# Datadump Learnings

This file captures durable, non-sensitive learnings from partial local CVP datadumps.

Reviewed local sources:

- `/Users/jasonbritton/Desktop/AXINOM_SETUP/CVP_Metadata/MEDIA/`
- `/Users/jasonbritton/Desktop/AXINOM_SETUP/CVP_Metadata/ENTERTAINMENT/`
- `/Users/jasonbritton/Desktop/AXINOM_SETUP/CVP_Metadata/CVP_Query_Notes.txt`

Do not commit raw datadumps, raw API responses, tenant-specific IDs, or customer hostnames. Record only endpoint, field, type, relationship, and query-shaping patterns that are useful for future read-only calls.

## Datadump Shape

The sampled CVP API dumps use a common paginated wrapper:

- root object includes `entryCount`, `itemsPerPage`, `startIndex`, and `entries`
- records live under `entries`
- list endpoints may be partial page pulls, not complete exports

Treat counts from these files as sample counts unless the query plan verifies total pagination behavior live.

## MEDIA Dump Coverage

Observed files covered these object families:

| Dump Family | Sample Size | Notes |
| --- | ---: | --- |
| `Media` | 2,000 records plus 200-record check subset | Title-level Media records with top-level metadata, custom namespaced fields, content arrays, thumbnails, availability, approval, and relationship IDs. |
| `MediaFile` | 100 records | File/rendition records with `mediaId`, storage/source/streaming URLs, technical dimensions, protection, release, and codec fields. |
| `Release` | 100 records | Release records include `mediaId`, `fileId`, `url`, `delivery`, `approved`, `pid`, and restrictions. |
| `Provider` | 100 records | Provider/config records. |
| `Server` | 62 records | Storage/server config records. Treat URL, credential-like, and key-related fields as sensitive. |
| `AssetType`, `Category`, `MediaDefaults`, `Field`, `MediaFileField`, `Restriction` | Small/all-object pulls | Lookup/config/metadata endpoints. |

### Media Fields Observed

Important top-level `Media` fields observed in samples:

- identity/state: `id`, `guid`, `ownerId`, `added`, `updated`, `approved`, `availabilityState`, `availableDate`, `expirationDate`
- labels/text: `title`, `description`, `author`, localized text variants
- relationships: `programId`, `seriesId`, `providerId`, `restrictionId`, `categoryIds`, `originalMediaIds`, `fileSourceMediaId`
- metadata arrays/objects: `content`, `thumbnails`, `categories`, `ratings`, `credits`, `availabilityWindows`
- customer/custom fields: namespace-style fields such as `<namespace>$<fieldName>`

The 200-record Check2 summaries showed many fields are always present but often empty. Do not treat present-but-empty as meaningful data. Preserve separate states for missing, null, empty string, empty array, and populated values.

### MediaFile Fields Observed

Important `MediaFile` fields observed in samples:

- identity/state: `id`, `guid`, `ownerId`, `added`, `updated`, `approved`, `exists`, `allowRelease`
- joins: `mediaId`, `serverId`, `sourceMediaFileId`, `assetTypeIds`
- URLs/paths: `url`, `storageUrl`, `sourceUrl`, `downloadUrl`, `streamingUrl`, `failoverStreamingUrl`, `filePath`
- file traits: `contentType`, `format`, `assetTypes`, `height`, `width`, `aspectRatio`, `displayAspectRatio`, `duration`, `fileSize`, `bitrate`, `frameRate`
- protection: `isProtected`, `protectionKey`, `protectionScheme`, `protectionHeaders`
- media details: `audioCodec`, `videoCodec`, `audioChannels`, `audioSampleRate`, `language`, `closedCaptions`, `secondaryAudio`

Request only the URL/path/protection fields needed for a task because they can expose sensitive delivery and storage information.

Live query caveat: `MediaFile` search capabilities can be restricted. In one validated workflow, `q` search returned search-not-enabled behavior and guessed filters such as generic `byField`, `mediaId`, and `byMedia` were not valid. The working file join was `byMediaId=<Media.id>`.

Mezzanine is represented as a file asset type, not as a `mediaAssetType` field. Match `assetTypes` / `plfile$assetTypes` values such as `Mezzanine`, `Mezzanine Amazon`, `Mezzanine Roku`, `Mezzanine Frndly TV`, or other account-specific mezzanine variants.

## ENTERTAINMENT Dump Coverage

Observed files covered these object families:

| Dump Family | Sample Size | Notes |
| --- | ---: | --- |
| `Program` | 200 records | Title/episode/program metadata with external IDs, season/episode fields, tags, image media IDs, and custom fields. |
| `ProgramAvailability` | 200 records | Program-like records enriched with availability, media/listing relationships, distribution rights, and embedded `media`. |
| `Credit` | 200 records | Joins people to programs/seasons through `personId`, `programId`, and `tvSeasonId`. |
| `Person` | 200 records | Person metadata, aliases, bios, thumbnails, and credits. |
| `Tag` | 244 records | Tag lookup records. |
| `TvSeason` | 200 records | Season-level metadata with `seriesId`, `seriesTitle`, `tvSeasonNumber`, and thumbnails. |
| `Station` | 1 record | Station lookup/config. |
| `ProgramField`, `ProgramAvailabilityField`, `StationField`, `TagField`, `TvSeasonField` | Small/all-object pulls | Field metadata endpoints for custom/search field discovery. |

### Entertainment Fields Observed

Important `Program` fields observed in samples:

- identity/state: `id`, `guid`, `ownerId`, `added`, `updated`, `approved`
- title metadata: `title`, `longTitle`, `shortTitle`, `sortTitle`, localized variants
- program shape: `programType`, `runtime`, `year`, `partNumber`, `partTotal`
- series/season: `seriesId`, `tvSeasonId`, `tvSeasonNumber`, `seriesEpisodeNumber`, `tvSeasonEpisodeNumber`
- relationships: `credits`, `tagIds`, `tags`, `imageMediaIds`, `externalIds`
- customer/custom fields: namespace-style fields such as `<namespace>$<fieldName>`

Important `ProgramAvailability` fields observed in samples:

- most core `Program` fields
- availability/listing fields: `availableTvSeasonIds`, `distributionRightIds`, `distributionRights`, `listingCount`, `listings`
- media relationship fields: `mediaCount`, `media`

The `ProgramAvailability.media` field is the primary observed bridge in local samples. Live responses may omit `media` from field projections, so confirm the returned shape before joining to Media. A validated fallback is `ProgramAvailability.guid` -> `Media.guid`, with `ownerId` used to disambiguate when multiple Media records share a GUID.

## Join Patterns

Observed useful joins:

| Source | Field | Target | Notes |
| --- | --- | --- | --- |
| `MediaFile` | `mediaId` / `byMediaId` | `Media.id` | File-to-title join; use `byMediaId=<Media.id>` where supported for live MediaFile lookup. |
| `Release` | `mediaId` | `Media.id` | Release-to-title join. |
| `Release` | `fileId` | `MediaFile.id` | Release-to-file join. |
| `Media` | `programId` | `Program.id` | Media-to-Entertainment join; verify account scope and object existence. |
| `ProgramAvailability` | `media` or `guid` | `Media` | Prefer embedded/referenced Media when present; if absent, resolve `ProgramAvailability.guid` to `Media.guid` and disambiguate by `ownerId`. |
| `Program` | `imageMediaIds` | `Media.id` | Image/artwork Media references. |
| `Program` | `seriesId`, `tvSeasonId` | Entertainment series/season objects | Confirm target endpoints before use. |
| `Credit` | `personId`, `programId`, `tvSeasonId` | `Person`, `Program`, `TvSeason` | Credit relationship joins. |

Always build a local join table and mark `resolved`, `missing`, `ambiguous`, or `unverified`.

## Query Notes Triage

The local `CVP_Query_Notes.txt` contains useful intent but some parameter placement is unclear. Carry these forward as patterns to verify, not as canonical syntax.

### Streaming / Non-DRM Media Discovery

Observed desired fields:

- Media identity/state: `id`, `guid`, `title`, `approved`, `availabilityState`, `availableDate`, `expirationDate`
- content fields: `content`, `content.storageUrl`, `content.assetTypes`, `content.format`, `content.duration`, `content.releases`, `content.releases.delivery`
- tagging/filtering: `adminTags`

Observed intent:

- exclude DRM-tagged records, using a `q` expression like `NOT adminTags:"DRM"`
- require approved and available Media, using `byApproved=true` and `byAvailabilityState=available`
- constrain content/release delivery, using `byContent` and nested encoded release filters

Clarification needed before canonicalizing:

- whether `byReleases=...` belongs only inside `byContent`, `contentFilter`, or another documented parameter for the specific endpoint
- which nested URL-encoding level CVP expects for release filters in this account
- whether `contentFilter` and `byContent` are interchangeable in the workflows that produced the notes

Known bad pattern from notes:

- top-level `byReleases` returned `BadParameterException` because `byReleases` was not a valid parameter in that context.

### ProgramAvailability Query

Observed desired fields:

- `id`, `guid`, `title`, `approved`
- `media`, `media.id`, `media.guid`, `media.availabilityState`
- account-specific alternate-ID fields when present

Observed intent:

- filter by available Media state
- filter by approved status

Clarification needed before canonicalizing:

- exact documented parameter syntax for `byMediaAvailabilityState`
- whether `byApproved=true` applies to ProgramAvailability itself, embedded Media, or both in the intended query

Live schema note:

- `schema=1.x` can return sparse ProgramAvailability payloads with only basic identity fields. Use `schema=2.0` when program fields are missing.
- In `schema=2.0`, core program fields can be namespaced as `plprogram$programType`, `plprogram$seriesId`, `plprogram$tvSeasonNumber`, `plprogram$tvSeasonEpisodeNumber`, and `plprogram$seriesEpisodeNumber`.
- Availability fields requested for the associated media object, such as `availableDate`, `expirationDate`, and approval state, may need to come from the resolved `Media` record rather than the ProgramAvailability row.

### Artwork / Image Backup Queries

Observed desired Media fields:

- identity and title: `id`, `guid`, `title`
- external IDs/custom fields: account-specific external ID fields when present
- program linkage: `seriesId` plus account-specific program type, season, and episode fields when present
- image traits: `content.contentType`, `content.height`, `content.width`, `content.format`, `content.assetTypes`, `content.title`, `content.url`, `content.aspectRatio`

Observed desired MediaFile fields:

- `title`, `mediaId`, `height`, `width`, `assetTypes`, `format`, `aspectRatio`, `streamingUrl`, `contentType`

Observed intent:

- image discovery uses content or file fields such as `contentType=image`
- art-file review often needs dimensions, aspect ratio, format, asset type, and URL/path fields

Use caution with URL fields and treat output artifacts as sensitive.
