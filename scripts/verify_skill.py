#!/usr/bin/env python3
"""Verify the CVP query agent skill package has the expected shape."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "SKILL.md",
    "agents/openai.yaml",
    "references/api-call-patterns.md",
    "references/cvp-docs/README.md",
    "references/cvp-docs/data-services-catalog.json",
    "references/datadump-learnings.md",
    "references/endpoints.md",
    "references/field-and-join-model.md",
    "references/knowledge-maintenance.md",
    "references/service-map.json",
    "references/query-workflow.md",
    "references/runtime-auth.md",
    "references/smoke-tests.md",
    "scripts/cvp_query.py",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_files() -> None:
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.exists():
            fail(f"missing {relative}")
        if path.is_file() and path.stat().st_size == 0:
            fail(f"empty {relative}")


def check_skill_frontmatter() -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail("SKILL.md missing YAML frontmatter")
    frontmatter = text.split("---", 2)[1]
    for key in ("name:", "description:"):
        if key not in frontmatter:
            fail(f"SKILL.md frontmatter missing {key}")


def check_service_map() -> None:
    data = json.loads((ROOT / "references" / "service-map.json").read_text(encoding="utf-8"))
    services = data.get("services", {})
    if "media" not in services:
        fail("service-map.json missing media service")
    objects = services["media"].get("objects", {})
    for object_name in ("Media", "MediaFile", "Release", "Provider", "Server", "Field"):
        if object_name not in objects:
            fail(f"service-map.json missing {object_name}")
        endpoint = objects[object_name].get("endpoint", "")
        if not endpoint.startswith("https://"):
            fail(f"{object_name} endpoint must be HTTPS")
    aliases = data.get("aliases", {})
    if aliases.get("program") == "Media":
        fail("service-map.json must not alias program to Media")


def check_cvp_docs_catalog() -> None:
    data = json.loads((ROOT / "references" / "cvp-docs" / "data-services-catalog.json").read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    if not entries:
        fail("data-services-catalog.json has no entries")
    required_titles = {
        "Selecting objects in Data Service operations",
        "Selecting objects using a byField query parameter",
        "Controlling the contents of the response payload",
        "Media endpoint",
        "MediaFile endpoint",
        "Program endpoint",
        "ProgramAvailability endpoint",
        "Entertainment data service",
    }
    titles = {entry.get("title") for entry in entries}
    missing = sorted(required_titles - titles)
    if missing:
        fail(f"data-services-catalog.json missing required titles: {', '.join(missing)}")
    for entry in entries:
        url = entry.get("source_url", "")
        if not url.startswith("https://docs.theplatform.com/"):
            fail(f"data-services-catalog.json contains non-CVP-docs URL: {url}")


def check_helper_script() -> None:
    script = ROOT / "scripts" / "cvp_query.py"
    result = subprocess.run(
        [sys.executable, str(script), "build-url", "--object", "Media", "--q", 'title:"Example"', "--field", "id"],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        fail(f"cvp_query.py build-url failed: {result.stderr.strip()}")
    output = result.stdout.strip()
    if "https://data.media.theplatform.com/media/data/Media" not in output:
        fail("build-url output missing Media endpoint")
    if "fields=id" not in output:
        fail("build-url output missing fields projection")
    if "title%3A%22Example%22" not in output:
        fail("build-url output did not URL-encode q")


def check_request_guards() -> None:
    script = ROOT / "scripts" / "cvp_query.py"
    http_result = subprocess.run(
        [sys.executable, str(script), "get", "--url", "http://data.media.theplatform.com/media/data/Media"],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    if http_result.returncode == 0:
        fail("cvp_query.py allowed a non-HTTPS request")
    if "Refusing non-HTTPS request" not in http_result.stderr:
        fail("non-HTTPS refusal message changed unexpectedly")

    host_result = subprocess.run(
        [sys.executable, str(script), "get", "--url", "https://example.com/media/data/Media"],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    if host_result.returncode == 0:
        fail("cvp_query.py allowed an unlisted host")
    if "Refusing request to unlisted host" not in host_result.stderr:
        fail("unlisted-host refusal message changed unexpectedly")


def main() -> int:
    check_files()
    check_skill_frontmatter()
    check_service_map()
    check_cvp_docs_catalog()
    check_helper_script()
    check_request_guards()
    print("OK: cvp-query-agent package sanity checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
