# Verified Endpoint Inventory

This file captures sanitized, read-only endpoint probes that were verified against a live CVP account. Treat this as operational evidence for future query planning, not as a guarantee that every CVP account has the same services or permissions.

Verification method:

- read-only `GET`
- `schema=2.0`
- `form=json`
- `range=1-1`
- `fields=id`
- response body checked for `isException: true`
- verified on 2026-04-28

Do not store credentials, account IDs, raw response payloads, or customer-specific secrets in this file.

## Verified Readable Endpoints

| Service | Object | Endpoint | Source |
| --- | --- | --- | --- |
| Delivery Data Service | `Restriction` | `https://data.delivery.theplatform.com/delivery/data/Restriction` | Local metadata record ID |
| Entertainment Data Service | `Credit` | `https://data.entertainment.tv.theplatform.com/entertainment/data/Credit` | Local metadata record ID |
| Entertainment Data Service | `Person` | `https://data.entertainment.tv.theplatform.com/entertainment/data/Person` | Local metadata record ID |
| Entertainment Data Service | `Program` | `https://data.entertainment.tv.theplatform.com/entertainment/data/Program` | Local metadata record ID |
| Entertainment Data Service | `Program/Field` | `https://data.entertainment.tv.theplatform.com/entertainment/data/Program/Field` | Local metadata record ID |
| Entertainment Data Service | `ProgramAvailability` | `https://data.entertainment.tv.theplatform.com/entertainment/data/ProgramAvailability` | Local metadata record ID |
| Entertainment Data Service | `ProgramAvailability/Field` | `https://data.entertainment.tv.theplatform.com/entertainment/data/ProgramAvailability/Field` | Local metadata record ID |
| Entertainment Data Service | `Station` | `https://data.entertainment.tv.theplatform.com/entertainment/data/Station` | Local metadata record ID |
| Entertainment Data Service | `Station/Field` | `https://data.entertainment.tv.theplatform.com/entertainment/data/Station/Field` | Local metadata record ID |
| Entertainment Data Service | `Tag` | `https://data.entertainment.tv.theplatform.com/entertainment/data/Tag` | Local metadata record ID |
| Entertainment Data Service | `Tag/Field` | `https://data.entertainment.tv.theplatform.com/entertainment/data/Tag/Field` | Local metadata record ID |
| Entertainment Data Service | `TvSeason` | `https://data.entertainment.tv.theplatform.com/entertainment/data/TvSeason` | Local metadata record ID |
| Entertainment Data Service | `TvSeason/Field` | `https://data.entertainment.tv.theplatform.com/entertainment/data/TvSeason/Field` | Local metadata record ID |
| Media Data Service | `AccountSettings` | `https://data.media.theplatform.com/media/data/AccountSettings` | Service map probe |
| Media Data Service | `AssetType` | `https://data.media.theplatform.com/media/data/AssetType` | Service map probe |
| Media Data Service | `Category` | `https://data.media.theplatform.com/media/data/Category` | Service map probe |
| Media Data Service | `Media` | `https://data.media.theplatform.com/media/data/Media` | Service map probe |
| Media Data Service | `Media/Field` | `https://data.media.theplatform.com/media/data/Media/Field` | Local metadata record ID |
| Media Data Service | `MediaDefaults` | `https://data.media.theplatform.com/media/data/MediaDefaults` | Service map probe |
| Media Data Service | `MediaFile` | `https://data.media.theplatform.com/media/data/MediaFile` | Service map probe |
| Media Data Service | `MediaFile/Field` | `https://data.media.theplatform.com/media/data/MediaFile/Field` | Local metadata record ID |
| Media Data Service | `Provider` | `https://data.media.theplatform.com/media/data/Provider` | Service map probe |
| Media Data Service | `Release` | `https://data.media.theplatform.com/media/data/Release` | Service map probe |
| Media Data Service | `Server` | `https://data.media.theplatform.com/media/data/Server` | Service map probe |

## Invalid Shorthand Endpoint Shapes

These guessed endpoint names returned `BadParameterException` with a message that the endpoint is not valid. Use the verified slash-form endpoint when present.

| Service | Invalid Object | Use Instead |
| --- | --- | --- |
| Entertainment Data Service | `ProgramAvailabilityField` | `ProgramAvailability/Field` |
| Entertainment Data Service | `ProgramField` | `Program/Field` |
| Entertainment Data Service | `StationField` | `Station/Field` |
| Entertainment Data Service | `TagField` | `Tag/Field` |
| Entertainment Data Service | `TvSeasonField` | `TvSeason/Field` |
| Media Data Service | `Field` | `Media/Field` |
| Media Data Service | `MediaFileField` | `MediaFile/Field` |

## Usage Notes

- Prefer `references/service-map.json` for machine-driven query building when an object is already configured there.
- Use this file as evidence when planning a task-local script or a private endpoint overlay for account-specific live calls.
- If promoting one of these endpoints to `service-map.json`, update `references/endpoints.md` and rerun `python3 scripts/verify_skill.py`.
- Keep raw probe output in local workspaces, not in the skill repository.
