# Condensed CVP Documentation

This folder is the skill's compact CVP documentation copy.

It intentionally does not include the full local HTML/PDF export. The full export is large, can contain internal context, and should remain outside this public repository. Instead, this folder keeps a small, maintained index of the most relevant CVP Data Services pages for building safe read-only API calls.

## Included Files

- `data-services-catalog.json`: selected CVP Data Services documentation titles, source URLs, local export filenames, index IDs, domain labels, and service labels. It now includes the Media and Entertainment service entries needed by the maintained endpoint and join docs.

## Source Corpus

The catalog was condensed from the installed `cvp-agent` documentation index:

- source index: `${CODEX_HOME:-$HOME/.codex}/skills/cvp-agent/references/docs_index.json`
- source map: `${CODEX_HOME:-$HOME/.codex}/skills/cvp-agent/references/docs_map.md`
- local export source noted by that map: `/Users/jasonbritton/Documents/PDF_Collections/CVP_Dupe`
- source index generated: `2026-01-29`

The local map reports 27 CVP docs files and 2,687 CVP doc pages, plus 2 Confluence files and 107 Confluence pages. This skill catalog excludes Confluence/internal entries and full document text.

## How to Refresh

1. Refresh or rebuild the installed `cvp-agent` documentation indexes.
2. Search for the relevant Data Services, endpoint, object, filter, and field pages.
3. Update `data-services-catalog.json` with the selected public CVP doc entries.
4. Update the maintained knowledge docs in `references/`.
5. Run `python3 scripts/verify_skill.py`.
