# Endpoint Knowledge

Use this file as the human-readable endpoint inventory for `cvp-query-agent`.

The machine-readable endpoint inventory is `references/service-map.json`. Keep this Markdown file aligned with that JSON whenever committed endpoints change.

At runtime, `scripts/cvp_query.py` also merges `references/local-endpoints.private.json` when that local file exists.

## Current Committed Endpoints

These are generic CVP Data Services endpoints currently committed with the skill.

| Service | Object | Endpoint | Notes |
| --- | --- | --- | --- |
| Media Data Service | `AssetType` | `https://data.media.theplatform.com/media/data/AssetType` | Asset/rendition type lookup. |
| Media Data Service | `Category` | `https://data.media.theplatform.com/media/data/Category` | Category lookup. |
| Media Data Service | `Field` | `https://data.media.theplatform.com/media/data/Field` | Custom field metadata; useful for `fieldName` and `searchFieldName`. |
| Media Data Service | `Media` | `https://data.media.theplatform.com/media/data/Media` | Media-level records. Confirm fields and filters against CVP docs before live use. |
| Media Data Service | `MediaFile` | `https://data.media.theplatform.com/media/data/MediaFile` | File-level records. Use for media-to-file joins only after confirming relationship fields. |
| Media Data Service | `MediaFileField` | `https://data.media.theplatform.com/media/data/MediaFileField` | MediaFile custom field metadata. |
| Media Data Service | `MediaDefaults` | `https://data.media.theplatform.com/media/data/MediaDefaults` | Default Media configuration records. |
| Media Data Service | `AccountSettings` | `https://data.media.theplatform.com/media/data/AccountSettings` | Media service account settings records. |
| Media Data Service | `Provider` | `https://data.media.theplatform.com/media/data/Provider` | Provider/config lookup. |
| Media Data Service | `Release` | `https://data.media.theplatform.com/media/data/Release` | Release records; useful for `mediaId`, `fileId`, `delivery`, and `url`. |
| Media Data Service | `Server` | `https://data.media.theplatform.com/media/data/Server` | Server/storage config; request only needed fields. |

## Known But Not Yet Live-Configured

These object families were observed in local datadumps and matched to CVP documentation, but the service base URL is not yet committed in `service-map.json`.

| Service | Object | Docs | Notes |
| --- | --- | --- | --- |
| Entertainment Data Service | `Credit` | `Credit endpoint` | Joins people to programs/seasons through `personId`, `programId`, and `tvSeasonId`. |
| Entertainment Data Service | `Person` | `Person endpoint` | Person metadata, aliases, bios, thumbnails, and credits. |
| Entertainment Data Service | `Program` | `Program endpoint` | Program/title/episode metadata. Do not alias this to Media. |
| Entertainment Data Service | `ProgramAvailability` | `ProgramAvailability endpoint` | Availability-aware program records with `media` bridge fields. |
| Entertainment Data Service | `Station` | `Station endpoint` | Station lookup/config. |
| Entertainment Data Service | `Tag` | `Tag endpoint` | Tag lookup. |
| Entertainment Data Service | `TvSeason` | `TvSeason endpoint` | Season-level metadata. |

Before enabling live calls for these objects, confirm the Entertainment service base URL and add it to `references/service-map.json`.

## Where to Add Endpoints

For non-sensitive, reusable CVP endpoints:

1. Add the service, object, endpoint, display fields, and docs in `references/service-map.json`.
2. Add a matching row in this file.
3. Add aliases only when they are unambiguous.
4. Run `python3 scripts/verify_skill.py`.

For customer-specific, tenant-specific, or otherwise sensitive endpoints:

1. Do not commit them to this public repository.
2. Store them in `references/local-endpoints.private.json`.
3. Keep that file local; it is ignored by Git.
4. Run normal `build-url` or `get` commands with the private object names from that overlay.
5. Pass any additional host needed for one-off calls with `--allow-host`.

## Private Overlay Shape

Use the same service/object shape as `service-map.json`:

```json
{
  "services": {
    "customer_media": {
      "display_name": "Customer Media Data Service",
      "base_url": "https://example.customer.cvp.invalid/media",
      "endpoint_base": "https://example.customer.cvp.invalid/media/data",
      "docs": ["Media endpoint"],
      "objects": {
        "Media": {
          "endpoint": "https://example.customer.cvp.invalid/media/data/Media",
          "common_display_fields": ["id", "guid", "title", "ownerId", "updated"],
          "notes": "Private customer endpoint. Do not commit."
        }
      }
    }
  },
  "aliases": {
    "customer media": "Media"
  }
}
```

## Review Rules

- Endpoint URLs are not credentials, but customer-specific hosts can still reveal sensitive operational context.
- Do not store credentials, tokens, cookies, signed URLs, or account secrets in endpoint files.
- Prefer exact service/object names over broad aliases.
- Keep write-capable endpoint notes out of normal query paths unless the user explicitly requests a write workflow.
