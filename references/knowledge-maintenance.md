# Knowledge Maintenance

`cvp-query-agent` has two knowledge layers:

1. Condensed source catalog: selected CVP documentation entries in `references/cvp-docs/data-services-catalog.json`.
2. Maintained operating knowledge: curated workflow docs in `references/`.

The maintained docs are intentionally smaller than the CVP documentation. They should capture what the agent needs to build correct read-only API calls without carrying the full doc corpus.

## Maintained Docs

| File | Purpose |
| --- | --- |
| `references/api-call-patterns.md` | Order of operations for selecting endpoints, filters, fields, auth, and response handling. |
| `references/field-and-join-model.md` | Baseline field naming and cross-endpoint join rules. |
| `references/datadump-learnings.md` | Sanitized learnings from local partial datadumps and query notes. |
| `references/endpoints.md` | Human-readable endpoint inventory and private overlay rules. |
| `references/query-workflow.md` | Natural-language-to-query workflow and answer contract. |
| `references/runtime-auth.md` | Runtime credential handling and Keychain setup. |
| `references/service-map.json` | Machine-readable endpoint and alias map. |

## Update Loop

When the agent answers a new kind of CVP question:

1. Use `cvp-agent` lookup or the condensed catalog to find relevant CVP doc pages.
2. Build the smallest safe dry-run query plan.
3. Run live `GET` only with user-approved runtime credentials.
4. Compare returned fields and relationships against the docs.
5. Identify any candidate knowledge update and classify it as committed-safe, private-local, or unclear.
6. Ask the user for explicit permission before editing any committed or private knowledge file.
7. Add only approved durable findings to the appropriate maintained or private docs.
8. Keep tenant-specific endpoints, IDs, hosts, accounts, tokens, and customer details out of committed files.
9. Run `python3 scripts/verify_skill.py`.

## Consent Gate

Knowledge updates are always opt-in.

The agent may suggest a knowledge update after a query, but it must not edit any of these without explicit user approval for that specific update:

- committed docs such as `references/*.md`
- committed maps/catalogs such as `references/*.json`
- ignored private files such as `references/local-endpoints.private.json`
- ignored private notes such as `references/local-*.private.md`

Before making an approved update, state:

- what was learned
- where it should be recorded
- whether it is safe for the public repo or should stay private
- what verification will be run

If the user does not approve the update, answer the query and leave files unchanged.

## What Not to Commit

- Full CVP HTML/PDF exports.
- Internal Confluence exports or links unless explicitly approved.
- Tokens, cookies, signed URLs, account secrets, tenant IDs, private account names, or customer hosts.
- Customer-specific custom field names or exact internal namespace prefixes unless the repo owner explicitly approves publishing them.
- Raw API responses containing sensitive data.
- One-off live query artifacts unless the user specifically asks for a sanitized report.

Use ignored local files such as `references/local-datadump-learnings.private.md` when exact customer field names or tenant-specific observations are useful locally but should not be published.

## Refresh Triggers

Refresh the condensed catalog and maintained docs when:

- CVP documentation indexes are regenerated.
- New endpoint families are added to the skill.
- A recurring question exposes a missing field or relationship pattern.
- A live response contradicts the maintained docs.
- The service map changes.
- New local datadumps or query notes reveal stable field/join patterns.
