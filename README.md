# CVP Query Agent

Standalone Codex skill repository for answering Cloud Video Platform data questions by planning safe read-only Data Services queries, resolving IDs across endpoints, and reporting evidence.

## Overview

This repository contains the skill definition, OpenAI surface metadata, helper scripts, and reference notes for the CVP Query Agent workflow.

## Usage

Refer to `SKILL.md` for the core instruction set and execution details.

## Install

Install or update the skill by copying this repository into your Codex skills directory:

```bash
mkdir -p "$CODEX_HOME/skills"
rsync -a --delete ./ "$CODEX_HOME/skills/cvp-query-agent/"
python3 "$CODEX_HOME/skills/cvp-query-agent/scripts/verify_skill.py"
```

If `CODEX_HOME` is not set, use `~/.codex`.

## Release Contents

- `SKILL.md`: core skill instructions.
- `agents/openai.yaml`: OpenAI surface metadata.
- `scripts/`: deterministic URL building, guarded live GET helper, and verification.
- `references/`: maintained CVP query knowledge, endpoint maps, runtime auth, smoke tests, and condensed source catalog.

Common local checks:

```bash
python3 scripts/verify_skill.py
python3 scripts/cvp_query.py objects
python3 scripts/cvp_query.py build-url --object Media --q "title:\"Example\"" --field id --field guid --field title
```

Authentication is runtime-only. Do not store CVP tokens, cookies, signed URLs, or account secrets in this repository.

## First Safe Query

1. Build a dry-run URL with explicit fields and filters:

```bash
python3 scripts/cvp_query.py build-url \
  --object Media \
  --by-field guid=abc123 \
  --field id \
  --field guid \
  --field title \
  --field updated
```

2. Store a short-lived read-only token in Keychain using `references/runtime-auth.md`.
3. Run the live read with the same explicit scope:

```bash
python3 scripts/cvp_query.py get \
  --use-keychain \
  --object Media \
  --by-field guid=abc123 \
  --field id \
  --field guid \
  --field title \
  --field updated
```

4. Review the live-request summary and type `RUN` only if the host, path, fields, filters, and auth source are correct.
5. Treat returned metadata as sensitive. Candidate knowledge updates must be approved before any files are edited.

For live read-only access, prefer macOS Keychain-backed runtime credentials:

```bash
python3 scripts/cvp_query.py get --use-keychain --object Media --by-field guid=abc123 --field id --field title
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
