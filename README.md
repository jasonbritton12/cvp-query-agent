# CVP Query Agent

Standalone Codex skill repository for answering Cloud Video Platform data questions by planning safe read-only Data Services queries, resolving IDs across endpoints, and reporting evidence.

## Overview

This repository contains the skill definition, OpenAI surface metadata, helper scripts, and reference notes for the CVP Query Agent workflow.

## Usage

Refer to `SKILL.md` for the core instruction set and execution details.

Common local checks:

```bash
python3 scripts/verify_skill.py
python3 scripts/cvp_query.py objects
python3 scripts/cvp_query.py build-url --object Media --q "title:\"Example\"" --field id --field guid --field title
```

Authentication is runtime-only. Do not store CVP tokens, cookies, signed URLs, or account secrets in this repository.

For live read-only access, prefer macOS Keychain-backed runtime credentials:

```bash
python3 scripts/cvp_query.py get --use-keychain --object Media --field id --field title
```

See `references/runtime-auth.md` for the Keychain setup command, runtime consent model, and credential removal steps.

Endpoint inventory:

- `references/endpoints.md` is the human-readable endpoint knowledge doc.
- `references/service-map.json` is the machine-readable endpoint map used by the helper.
- `references/local-endpoints.private.json` is reserved for local customer-specific endpoints, is ignored by Git, and is merged at runtime when present.

Knowledge docs:

- `references/cvp-docs/` contains the condensed CVP Data Services source catalog.
- `references/api-call-patterns.md` captures the maintained API call-building workflow.
- `references/field-and-join-model.md` captures baseline field naming and endpoint join rules.
- `references/datadump-learnings.md` captures sanitized local datadump and query-note findings.
- `references/knowledge-maintenance.md` defines the update loop for improving the skill over time.

Knowledge updates are opt-in. The skill should propose candidate updates after useful discoveries, but it must ask before editing committed docs or ignored private knowledge files.
