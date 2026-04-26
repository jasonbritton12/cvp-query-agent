#!/usr/bin/env python3
"""Verify the CVP query agent skill package has the expected shape."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import importlib.util
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
    text = (ROOT / "references" / "service-map.json").read_text(encoding="utf-8")
    forbidden_phrases = [
        "Add customer-specific service base URLs here",
        "--allow-host",
    ]
    for phrase in forbidden_phrases:
        if phrase in text:
            fail(f"service-map.json contains forbidden public/private guidance: {phrase}")
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
        if not entry.get("domain") or not entry.get("service"):
            fail("data-services-catalog.json entries must include domain and service")


def check_knowledge_consent_gate() -> None:
    skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    maintenance_text = (ROOT / "references" / "knowledge-maintenance.md").read_text(encoding="utf-8")
    required_phrases = [
        "Never update committed or private knowledge files automatically",
        "explicit permission before editing any knowledge file",
        "Knowledge updates are always opt-in",
        "ignored private files",
    ]
    combined = skill_text + "\n" + maintenance_text
    for phrase in required_phrases:
        if phrase not in combined:
            fail(f"knowledge consent gate missing phrase: {phrase}")


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

    planned_result = subprocess.run(
        [sys.executable, str(script), "build-url", "--object", "Program", "--field", "id"],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    if planned_result.returncode == 0:
        fail("cvp_query.py built a live URL for unconfigured Program object")
    if "Known but not live-configured object 'Program'" not in planned_result.stderr:
        fail("Program recovery message did not explain private endpoint configuration")

    objects_result = subprocess.run(
        [sys.executable, str(script), "objects", "--include-planned"],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    if objects_result.returncode != 0:
        fail(f"cvp_query.py objects --include-planned failed: {objects_result.stderr.strip()}")
    if "planned\tProgram\t" not in objects_result.stdout:
        fail("objects --include-planned did not list Program")


def check_request_guards() -> None:
    script = ROOT / "scripts" / "cvp_query.py"
    help_result = subprocess.run(
        [sys.executable, str(script), "get", "--help"],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    if help_result.returncode != 0:
        fail("cvp_query.py get --help failed")
    if "--yes" in help_result.stdout:
        fail("get help still exposes --yes Keychain bypass")
    if "--allow-host" in help_result.stdout:
        fail("get help still exposes --allow-host")

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

    path_result = subprocess.run(
        [
            sys.executable,
            str(script),
            "get",
            "--url",
            "https://data.media.theplatform.com/not-a-data-service-path?fields=id&byField=guid%7Cabc123",
        ],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    if path_result.returncode == 0:
        fail("cvp_query.py allowed an allowed-host URL outside Data Services prefixes")
    if "outside configured CVP Data Services endpoint prefixes" not in path_result.stderr:
        fail("path-prefix refusal message changed unexpectedly")

    no_fields_result = subprocess.run(
        [
            sys.executable,
            str(script),
            "get",
            "--url",
            "https://data.media.theplatform.com/media/data/Media?byField=guid%7Cabc123",
        ],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    if no_fields_result.returncode == 0:
        fail("cvp_query.py allowed live GET without fields")
    if "without explicit fields" not in no_fields_result.stderr:
        fail("missing-fields refusal message changed unexpectedly")

    no_filter_result = subprocess.run(
        [sys.executable, str(script), "get", "--url", "https://data.media.theplatform.com/media/data/Media?fields=id"],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    if no_filter_result.returncode == 0:
        fail("cvp_query.py allowed live GET without filter or range")
    if "without a filter or range" not in no_filter_result.stderr:
        fail("missing-filter refusal message changed unexpectedly")

    sensitive_header_result = subprocess.run(
        [
            sys.executable,
            str(script),
            "get",
            "--url",
            "https://data.media.theplatform.com/media/data/Media?fields=id&byField=guid%7Cabc123",
            "--header",
            "Authorization=Bearer bad",
        ],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    if sensitive_header_result.returncode == 0:
        fail("cvp_query.py allowed Authorization through --header")
    if "Refusing sensitive header from CLI" not in sensitive_header_result.stderr:
        fail("sensitive-header refusal message changed unexpectedly")

    mixed_env = os.environ.copy()
    mixed_env["CVP_COOKIE"] = "stale-cookie"
    mixed_auth_result = subprocess.run(
        [
            sys.executable,
            str(script),
            "get",
            "--use-keychain",
            "--url",
            "https://data.media.theplatform.com/media/data/Media?fields=id&byField=guid%7Cabc123",
        ],
        cwd=str(ROOT),
        env=mixed_env,
        check=False,
        text=True,
        capture_output=True,
    )
    if mixed_auth_result.returncode == 0:
        fail("cvp_query.py allowed Keychain auth mixed with env auth")
    if "Refusing mixed auth sources" not in mixed_auth_result.stderr:
        fail("mixed-auth refusal message changed unexpectedly")


def check_response_redaction() -> None:
    script = ROOT / "scripts" / "cvp_query.py"
    spec = importlib.util.spec_from_file_location("cvp_query", script)
    if spec is None or spec.loader is None:
        fail("could not import cvp_query.py for redaction checks")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    body = json.dumps(
        {
            "id": "safe-id",
            "sourceUrl": "https://storage.example.com/private/master.m3u8",
            "nested": {"token": "secret-token", "title": "Visible"},
        }
    )
    output, truncated = module.safe_response_text(body, allow_raw_response=False, max_bytes=10000)
    if truncated:
        fail("redaction fixture unexpectedly truncated")
    if "https://storage.example.com/private/master.m3u8" in output or "secret-token" in output:
        fail("safe_response_text did not redact sensitive URL/token fields")
    if "Visible" not in output:
        fail("safe_response_text over-redacted non-sensitive fields")


def main() -> int:
    check_files()
    check_skill_frontmatter()
    check_service_map()
    check_cvp_docs_catalog()
    check_knowledge_consent_gate()
    check_helper_script()
    check_request_guards()
    check_response_redaction()
    print("OK: cvp-query-agent package sanity checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
