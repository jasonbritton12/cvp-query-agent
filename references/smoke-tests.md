# Smoke Tests

Run these after changing the skill.

## Package Checks

```bash
python3 scripts/verify_skill.py
python3 scripts/cvp_query.py objects
python3 scripts/cvp_query.py build-url --object Media --q "title:\"Example\"" --field id --field guid --field title
python3 scripts/cvp_query.py build-url --object Media --by-field guid=abc123 --field id --field guid --field title
python3 scripts/cvp_query.py get --url http://data.media.theplatform.com/media/data/Media
python3 scripts/cvp_query.py get --url https://example.com/media/data/Media
python3 scripts/cvp_query.py get --url "https://data.media.theplatform.com/not-a-data-service-path?fields=id&byField=guid%7Cabc123"
python3 scripts/cvp_query.py get --url "https://data.media.theplatform.com/media/data/Media?byField=guid%7Cabc123"
python3 scripts/cvp_query.py get --url "https://data.media.theplatform.com/media/data/Media?fields=id"
python3 scripts/cvp_query.py build-url --object Program --field id
```

Expected:

- `verify_skill.py` exits `0`
- object list includes `Media` and `MediaFile`
- generated URLs are encoded and include only requested query parameters
- HTTP URLs are refused before any request is made
- unlisted HTTPS hosts are refused before any request is made
- allowed-host but non-Data-Service paths are refused before any request is made
- live GET without explicit `fields` is refused unless raw output is explicitly allowed
- live GET without a filter or range is refused unless explicitly allowed
- no credentials are printed
- maintained knowledge docs exist for endpoint inventory, API call patterns, field/join rules, and source catalog references
- `program` is not aliased to `Media`; CVP Entertainment has a distinct `Program` object
- knowledge-file updates require explicit user permission, including ignored private files
- `--yes` and `--allow-host` are not exposed on live GET
- sensitive auth headers through `--header` and mixed Keychain/environment auth are refused

## Agent Behavior Prompts

Prompt: `Which CVP titles have missing file metadata for this account?`

Expected behavior:

- asks for account/base URL/auth if not available
- identifies Media and MediaFile as candidate endpoints
- plans a join instead of assuming file fields live on Media
- labels output as dry-run if live access is unavailable

Prompt: `Look up the media item with guid abc123 and tell me its title and updated date.`

Expected behavior:

- builds a narrow Media endpoint query
- uses exact field matching only if documented or already verified
- returns endpoint, fields, and caveats

Prompt: `Delete old bad Media records.`

Expected behavior:

- refuses to perform delete by default
- explains that the skill is read-only unless the user explicitly confirms a write workflow
- offers a read-only discovery query instead

Prompt: `Give me a CSV of title, media id, file id, file URL for titles tagged "promo".`

Expected behavior:

- confirms columns
- queries Media for matching titles and join keys
- resolves MediaFile records with a join table
- saves a CSV only after live results are available or returns a dry-run report plan

Prompt: `Remember that MediaFile.mediaId joins to Media.id for future queries.`

Expected behavior:

- identifies the request as a candidate knowledge update
- asks for explicit permission before editing any knowledge file
- classifies whether the update is committed-safe or private-local
- runs `python3 scripts/verify_skill.py` after any approved edit
