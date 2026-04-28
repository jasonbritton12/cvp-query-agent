# Runtime Authentication

Use runtime-only credentials for CVP access. Do not store tokens, cookies, signed URLs, or account secrets in this repository.

## Recommended Flow

1. Create a dedicated CVP account with read-only access to the minimum required owner, tenant, account, and Data Services.
2. Store only a short-lived read-only credential in macOS Keychain, or store a service account secret in Keychain only when a long export needs token refresh.
3. Run `scripts/cvp_query.py get --use-keychain` when live data is required.
4. Let the helper retrieve the credential only after explicit runtime confirmation.
5. Confirm the live request scope by typing `RUN`.
6. Rotate the credential after use or on a short schedule.

The helper refuses non-HTTPS requests and refuses URLs outside configured CVP Data Services endpoint prefixes from `references/service-map.json` or the ignored private endpoint overlay.

## FedAuth Service Account Tokens

Some CVP Data Services workflows use short-lived service tokens generated from a service account client ID and client secret.

Observed FedAuth pattern:

```text
GET https://fedauth.theplatform.com/v1/service/token
Authorization: Basic base64(<client_id>:<client_secret>)
```

For Data Services requests, the returned service token is not sent as a bearer token. Send it as the password side of a Basic credential:

```text
Authorization: Basic base64(:<service-token>)
```

This distinction matters: sending the same service token as `Authorization: Bearer ...` or as `Basic base64(<service-token>:)` can fail with missing or invalid security token errors.

Service tokens can be short-lived. For long exports, prefer a task-local wrapper that:

1. prompts locally for the service account secret without echoing it,
2. stores the secret in macOS Keychain,
3. generates service tokens only at runtime,
4. refreshes tokens before expiry or after an invalid-token response, and
5. never prints tokens or secrets.

Do not hardcode client secrets in shell scripts, commit them to docs, pass them as command-line arguments, or paste them into chat.

CVP may return authentication failures as an HTTP 200 response with an exception payload. Auth helpers must inspect response bodies for `isException: true`, not only HTTP status codes.

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
- Do not pass credentials through `--header`; the helper rejects sensitive auth headers.
- Do not mix Keychain credentials with `CVP_AUTHORIZATION`, `CVP_BEARER_TOKEN`, or `CVP_COOKIE`; set at most one environment auth variable when using env-backed auth.
- Use private endpoint overlays for additional trusted CVP endpoints; there is no runtime arbitrary-host override for authenticated requests.
- Treat exports and result files as sensitive data even when credentials are read-only.
- Treat generated service tokens as runtime-only secrets. If the token is JWT-like, it may include an `exp` claim that can be used to refresh before expiry.
