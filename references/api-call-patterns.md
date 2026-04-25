# CVP API Call Patterns

Use this maintained knowledge doc before building live CVP Data Services requests.

Sources are indexed in `references/cvp-docs/data-services-catalog.json`; especially:

- `Developing with the Cloud Video Platform's data services`
- `Read-only data services`
- `Selecting objects in Data Service operations`
- `Selecting objects using the q query parameter`
- `Q query syntax reference`
- `Selecting objects using a byField query parameter`
- `Controlling the contents of the response payload`
- `Specifying the data-service response payload format`
- `Business-service API conventions`
- `Index of standard request parameters`

## Default Order of Operations

1. Identify the owning Data Service and object endpoint.
2. Decide whether the user supplied an exact object ID, a stable field value, or human search text.
3. Start with exact lookup:
   - direct object ID when available
   - `byField` only when the target endpoint supports that field
4. Use `q` search for title/text discovery when exact lookup is not available.
5. Select explicit `fields`; include only answer fields, identity fields, and join keys.
6. Add pagination, sort, or format parameters only when needed.
7. Run only `GET` through `scripts/cvp_query.py get`.
8. Validate the returned shape before planning a second endpoint call.
9. Build joins locally and label unresolved or ambiguous references.
10. Cite the endpoint, filters, fields, and docs used.

## Endpoint Selection

Do not infer endpoint ownership from Console labels. Use:

1. `references/endpoints.md` for the current endpoint inventory.
2. `references/service-map.json` for machine-readable endpoint URLs.
3. `references/local-endpoints.private.json` for private local endpoints when present.
4. `references/cvp-docs/data-services-catalog.json` to identify the relevant CVP doc page.

If the needed endpoint is not in the local inventory, produce a dry-run plan and update the endpoint inventory before live use.

## Filter Selection

Use filters in this order:

| User Input | Preferred Query Pattern | Notes |
| --- | --- | --- |
| Full object ID | endpoint URL plus object ID or documented exact lookup | Confirm endpoint URL shape in docs before live use. |
| Stable field value such as `guid` | `byField=guid|value` | Use only when the endpoint docs or prior live response confirms the field. |
| Human title or text | `q=...` | Treat as discovery. Expect multiple matches and ask for disambiguation when needed. |
| Relationship/reference ID | Query the endpoint that owns the referenced object | Do not assume a label field from the source record is authoritative. |

## Field Projection

Always request explicit `fields`.

Minimum discovery fields:

- `id`
- `guid` when available
- user-facing label such as `title` when available
- `ownerId`
- `added`
- `updated`
- join/reference fields needed for the next request

Do not request broad payloads unless the user asks for inspection or export. Large responses can expose more sensitive data than the answer requires.

## Live Request Safety

- Use `GET` only.
- Use HTTPS only.
- Use the Keychain-backed runtime auth path when credentials are needed.
- Use known hosts from `service-map.json` or the private local endpoint overlay.
- Do not add write-capable methods to normal workflow docs.
- Redact tokens, cookies, account secrets, and signed URLs.

## Result Handling

Before answering:

1. Count returned records.
2. Check whether the response is page-limited.
3. Verify each requested field exists.
4. Mark missing fields separately from empty values.
5. Preserve source IDs and target IDs in any join.
6. Separate `Observed`, `Inferred`, and `Not verified` statements.
