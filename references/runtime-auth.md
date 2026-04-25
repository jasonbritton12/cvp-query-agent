# Runtime Authentication

Use runtime-only credentials for CVP access. Do not store tokens, cookies, signed URLs, or account secrets in this repository.

## Recommended Flow

1. Create a dedicated CVP account with read-only access to the minimum required owner, tenant, account, and Data Services.
2. Store only a short-lived read-only credential in macOS Keychain.
3. Run `scripts/cvp_query.py get --use-keychain` when live data is required.
4. Let the helper retrieve the credential only after explicit runtime confirmation.
5. Rotate the credential after use or on a short schedule.

The helper refuses non-HTTPS requests and refuses hosts that are not listed in `references/service-map.json` unless a user passes `--allow-host` for that request.

## Store a Bearer Token in macOS Keychain

Run this from a local terminal. The final `-w` prompts for the token instead of placing it in the command line.

```bash
security add-generic-password -U \
  -s cvp-query-agent.readonly-token \
  -a cvp-readonly \
  -D "CVP read-only bearer token" \
  -l "CVP Query Agent read-only token" \
  -j "Read-only CVP Data Services token for cvp-query-agent. No write/delete privileges." \
  -T "" \
  -w
```

`-T ""` removes the default trusted application entry. macOS can then prompt before a process is allowed to read the item. The helper also asks for a typed confirmation before it calls Keychain.

## Run a Read-Only Query

```bash
python3 scripts/cvp_query.py get \
  --use-keychain \
  --keychain-service cvp-query-agent.readonly-token \
  --keychain-account cvp-readonly \
  --object Media \
  --by-field guid=abc123 \
  --field id \
  --field guid \
  --field title \
  --field updated
```

By default, the stored value is treated as a bearer token and sent as:

```text
Authorization: Bearer [REDACTED]
```

If the stored value is already a full authorization header, use:

```bash
--keychain-auth-type authorization
```

If the stored value is a cookie header, use:

```bash
--keychain-auth-type cookie
```

## Emergency Removal

```bash
security delete-generic-password \
  -s cvp-query-agent.readonly-token \
  -a cvp-readonly
```

## Operational Rules

- Use read-only CVP roles only.
- Prefer short-lived credentials.
- Keep service scope as narrow as possible.
- Do not use `--header Authorization=...` for normal operation because it can expose secrets in shell history and process listings.
- Do not pass `--yes` unless another human-approved wrapper is already handling runtime consent.
- Treat exports and result files as sensitive data even when credentials are read-only.
