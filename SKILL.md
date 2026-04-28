---
name: cvp-query-agent
description: Build and run Cloud Video Platform Data Services queries from natural-language data questions, including endpoint selection, safe read-only request planning, field projection, ID cross-referencing across endpoints, and evidence-backed answers. Use when a user asks what CVP data or metadata says and does not want to manually manage API calls, IDs, or joins.
---

# CVP Query Agent

Use this skill when the user asks natural-language questions about CVP data or metadata and expects the agent to select endpoints, build queries, resolve cross-endpoint IDs, run safe read-only requests when authorized, and return a concise answer with evidence.

Resolve bundled resource paths relative to this skill directory.

## Operating Mode

Default to a read-only analyst workflow.

1. Translate the user question into required entities, filters, output fields, and join keys.
2. Review `references/api-call-patterns.md`, `references/field-and-join-model.md`, and the relevant CVP source entry before using endpoint-specific behavior.
3. Build the smallest safe query that can answer the question.
4. Execute only read-only `GET` requests. Write, delete, ingest, start, update, and complete operations are out of scope for this skill and require a separate reviewed workflow.
5. Cross-reference IDs by querying the endpoint that owns the referenced object.
6. Return the answer, key records, query URLs or redacted request summaries, and any uncertainty.

If credentials, base URLs, or tenant/account context are missing, produce a dry-run query plan and ask only for the missing operational inputs needed to run it.

## Knowledge Update Consent

Never update committed or private knowledge files automatically during normal query answering.

When a query reveals a reusable endpoint, field, relationship, filter, or caveat:

1. Report the candidate learning in the answer or as a short follow-up note.
2. Classify it as committed-safe, private-local, or unclear.
3. Ask the user for explicit permission before editing any knowledge file.
4. Wait for approval before changing `references/*.md`, `references/*.json`, or ignored private knowledge files.
5. After approved edits, run `python3 scripts/verify_skill.py`.

This consent gate applies even when the update would be written only to ignored private files.

## Required Inputs

At minimum, identify:

- user question and desired output shape
- CVP account, tenant, or owner context when needed
- service base URL or endpoint URL
- authentication method available in the current environment

Use `references/endpoints.md` for the human-readable endpoint inventory and `references/service-map.json` for known local base URLs and endpoint templates. Use `references/cvp-docs/data-services-catalog.json` to locate the condensed CVP source docs behind the workflow. If a needed service is not listed, use the CVP documentation lookup workflow before composing the request.

Use `references/verified-endpoints.md` when a task asks which endpoints have been observed as readable in the live account, or when a query needs an account-verified endpoint that is not yet promoted into `service-map.json`.

## Documentation Lookup

When endpoint behavior, query parameters, object fields, or relationships are not already certain, use the installed CVP documentation skill if available:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/cvp-agent/scripts/cvp_lookup.py" "Media endpoint retrieving Media objects fields byField" --top 8
```

Use the installed `cvp-agent` skill when available. If it is not installed, rely on `references/cvp-docs/data-services-catalog.json` and keep the request plan conservative.

Then open the cited local documentation file if accessible. If the full export is blocked by filesystem permissions, state that only the index was available and keep the request plan conservative.

Relevant CVP doc topics to search first:

- `Business-service API conventions`
- `REST API conventions`
- `Selecting objects in Data Service operations`
- `Selecting objects using a byField query parameter`
- `Using the q query to search for Media objects`
- endpoint-specific pages such as `Media endpoint`, `MediaFile endpoint`, or the target object endpoint
- object pages for field names and relationship IDs

## Query Workflow

Read these maintained knowledge docs before building non-trivial calls:

1. `references/api-call-patterns.md` for endpoint/filter/field selection order.
2. `references/field-and-join-model.md` for baseline field names and cross-endpoint join discipline.
3. `references/datadump-learnings.md` for sanitized field, join, and query-note patterns observed in local partial datadumps.
4. `references/verified-endpoints.md` for sanitized live endpoint probe results when endpoint availability is part of the question.
5. `references/query-workflow.md` for natural-language planning, reporting, and answer format.

For simple single-endpoint reads:

1. Pick the endpoint.
2. Add exact filters first, then broader search terms.
3. Add a field projection so the response includes only fields needed for the answer and join keys.
4. Use `scripts/cvp_query.py build-url` to build a properly encoded URL.
5. Use `scripts/cvp_query.py get` only when credentials are available and the user asked for live results.

## Helper Script

Use `scripts/cvp_query.py` for deterministic URL building and optional GET execution.

Examples:

```bash
python3 scripts/cvp_query.py objects
python3 scripts/cvp_query.py build-url --object Media --q "title:\"Example\"" --field id --field guid --field title
python3 scripts/cvp_query.py build-url --object Media --by-field guid=12345 --field id --field guid --field title
python3 scripts/cvp_query.py get --url "https://data.media.theplatform.com/media/data/Media?fields=id,title"
```

Authentication is runtime-only. The script reads optional environment variables:

- `CVP_AUTHORIZATION`: full `Authorization` header value
- `CVP_BEARER_TOKEN`: token used as `Authorization: Bearer <token>`
- `CVP_COOKIE`: cookie header value

For operator workflows on macOS, prefer the Keychain-backed runtime path:

```bash
python3 scripts/cvp_query.py get --use-keychain --object Media --by-field guid=12345 --field id --field guid --field title
```

Use `references/runtime-auth.md` for the Keychain storage command and access-removal steps. The helper asks for runtime confirmation before reading Keychain, requires a separate `RUN` confirmation before live requests, refuses non-HTTPS requests, and restricts live requests to configured CVP Data Services endpoint prefixes.

Never write credentials into skill files, references, logs, or final answers.

## Cross-Endpoint ID Resolution

When a response contains IDs from another endpoint:

1. Preserve the source record ID, source field, target endpoint, target ID, and confidence.
2. Query the target endpoint by exact field match where documented.
3. Fetch only fields needed for display and the next join.
4. Build a local join table before summarizing.
5. If a referenced ID is missing or ambiguous, report it as an unresolved reference rather than guessing.

Use `references/query-workflow.md` for common join patterns.

## Answer Contract

Return:

- direct answer first
- endpoint(s) queried or planned
- filters and fields used
- record count and important IDs
- unresolved IDs, missing fields, or permission gaps
- citations to CVP doc titles or local files used for endpoint behavior

For live results, distinguish observed data from inference. For dry runs, label the output as a query plan, not an answer from data.

## Guardrails

- Prefer read-only `GET` requests.
- Do not call update/delete/start/complete methods; hand them off to a separate reviewed workflow.
- Do not infer object relationships from similar field names without validating through docs or returned data.
- Do not broaden filters silently when an exact lookup returns no rows; report the miss and ask whether to broaden.
- Do not update knowledge files without explicit user permission for that update.
- Redact tokens, cookies, account secrets, and signed URLs.
- Keep raw response dumps out of the final answer unless the user asks for them.
- Save large result sets to a file only when the user asks for an artifact.

## Resources

- `references/service-map.json`: known base URLs, object endpoint templates, and service aliases.
- `references/endpoints.md`: human-readable endpoint inventory and update rules.
- `references/verified-endpoints.md`: sanitized live read-only endpoint probes for account-verified availability and invalid shorthand endpoint shapes.
- `references/api-call-patterns.md`: maintained CVP API call-building order of operations.
- `references/field-and-join-model.md`: maintained field naming and cross-endpoint join baseline.
- `references/datadump-learnings.md`: sanitized local datadump and query-note findings.
- `references/knowledge-maintenance.md`: rules for improving the skill's knowledge docs safely.
- `references/cvp-docs/`: condensed source catalog of selected CVP Data Services documentation entries.
- `references/query-workflow.md`: detailed natural-language-to-query, cross-reference, and answer workflow.
- `references/runtime-auth.md`: Keychain-backed runtime authentication setup and rules.
- `references/smoke-tests.md`: validation prompts and expected behaviors.
- `scripts/cvp_query.py`: URL builder and optional read-only request helper.
- `scripts/verify_skill.py`: local package sanity checks.
