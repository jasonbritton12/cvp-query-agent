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
