#!/usr/bin/env python3
"""Small helper for building and running read-only CVP Data Services requests."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


SKILL_ROOT = Path(__file__).resolve().parents[1]
SERVICE_MAP_PATH = SKILL_ROOT / "references" / "service-map.json"
DEFAULT_KEYCHAIN_SERVICE = "cvp-query-agent.readonly-token"
DEFAULT_KEYCHAIN_ACCOUNT = "cvp-readonly"
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(cookie\s*[:=]\s*)[^;\n\r]+"),
    re.compile(r"(?i)((?:access_)?token=)[^&\s]+"),
    re.compile(r"(?i)((?:signature|sig|policy)=)[^&\s]+"),
]


def load_service_map() -> dict:
    with SERVICE_MAP_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_objects(service_map: dict) -> Iterable[tuple[str, str, str]]:
    for service_name, service in sorted(service_map.get("services", {}).items()):
        for object_name, config in sorted(service.get("objects", {}).items()):
            yield service_name, object_name, config["endpoint"]


def known_hosts(service_map: dict) -> set[str]:
    hosts: set[str] = set()
    for service in service_map.get("services", {}).values():
        for key in ("base_url", "endpoint_base"):
            url = service.get(key)
            if url:
                parsed = urlparse(url)
                if parsed.netloc:
                    hosts.add(parsed.netloc.lower())
        for config in service.get("objects", {}).values():
            endpoint = config.get("endpoint")
            if endpoint:
                parsed = urlparse(endpoint)
                if parsed.netloc:
                    hosts.add(parsed.netloc.lower())
    return hosts


def resolve_object(service_map: dict, object_name: str) -> dict:
    aliases = service_map.get("aliases", {})
    canonical = aliases.get(object_name, object_name)
    canonical = aliases.get(canonical.lower(), canonical)
    for _service_name, candidate, endpoint in iter_objects(service_map):
        if candidate.lower() == canonical.lower():
            return {"name": candidate, "endpoint": endpoint}
    known = ", ".join(sorted({name for _svc, name, _url in iter_objects(service_map)}))
    raise SystemExit(f"Unknown object '{object_name}'. Known objects: {known}")


def parse_key_value(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("expected KEY=VALUE")
    key, value = raw.split("=", 1)
    if not key:
        raise argparse.ArgumentTypeError("key cannot be empty")
    return key, value


def add_query_params(url: str, params: list[tuple[str, str]]) -> str:
    parsed = urlparse(url)
    existing = parse_qsl(parsed.query, keep_blank_values=True)
    query = urlencode(existing + params, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment))


def redact_sensitive(text: str) -> str:
    redacted = text
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]", redacted)
    return redacted


def build_url(args: argparse.Namespace) -> str:
    service_map = load_service_map()
    if args.url:
        endpoint = args.url
    else:
        endpoint = resolve_object(service_map, args.object)["endpoint"]

    params: list[tuple[str, str]] = []
    if args.q:
        params.append(("q", args.q))
    for key, value in args.by_field or []:
        params.append(("byField", f"{key}|{value}"))
    if args.field:
        params.append(("fields", ",".join(args.field)))
    for key, value in args.param or []:
        params.append((key, value))
    if args.pretty:
        params.append(("_pretty", "true"))
    return add_query_params(endpoint, params)


def require_keychain_consent(args: argparse.Namespace) -> None:
    if args.yes:
        return
    prompt = (
        "Retrieve the CVP read-only credential from macOS Keychain now?\n"
        f"  service: {args.keychain_service}\n"
        f"  account: {args.keychain_account}\n"
        "Type 'yes' to continue: "
    )
    if input(prompt).strip() != "yes":
        raise SystemExit("Cancelled before reading Keychain.")


def read_keychain_secret(args: argparse.Namespace) -> str:
    require_keychain_consent(args)
    command = [
        "security",
        "find-generic-password",
        "-w",
        "-s",
        args.keychain_service,
        "-a",
        args.keychain_account,
    ]
    result = subprocess.run(command, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        message = redact_sensitive(result.stderr.strip() or result.stdout.strip())
        raise SystemExit(f"Unable to read CVP credential from Keychain: {message}")
    secret = result.stdout.strip()
    if not secret:
        raise SystemExit("Keychain item was found but did not contain a credential.")
    return secret


def apply_keychain_header(headers: dict[str, str], args: argparse.Namespace) -> None:
    secret = read_keychain_secret(args)
    if args.keychain_auth_type == "bearer":
        headers["Authorization"] = f"Bearer {secret}"
    elif args.keychain_auth_type == "authorization":
        headers["Authorization"] = secret
    elif args.keychain_auth_type == "cookie":
        headers["Cookie"] = secret
    else:
        raise SystemExit(f"Unsupported keychain auth type: {args.keychain_auth_type}")


def headers_from_runtime(args: argparse.Namespace) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    authorization = os.environ.get("CVP_AUTHORIZATION")
    bearer = os.environ.get("CVP_BEARER_TOKEN")
    cookie = os.environ.get("CVP_COOKIE")
    if args.use_keychain:
        apply_keychain_header(headers, args)
    elif authorization:
        headers["Authorization"] = authorization
    elif bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    if cookie:
        headers["Cookie"] = cookie
    for key, value in args.header or []:
        headers[key] = value
    return headers


def validate_get_url(url: str, args: argparse.Namespace) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise SystemExit("Refusing non-HTTPS request. Use build-url to inspect the URL instead.")
    service_map = load_service_map()
    allowed_hosts = known_hosts(service_map) | {host.lower() for host in args.allow_host or []}
    if parsed.netloc.lower() not in allowed_hosts:
        known = ", ".join(sorted(allowed_hosts))
        raise SystemExit(f"Refusing request to unlisted host '{parsed.netloc}'. Known hosts: {known}")


def get_url(args: argparse.Namespace) -> int:
    url = args.url or build_url(args)
    validate_get_url(url, args)
    request = Request(url, headers=headers_from_runtime(args), method="GET")
    try:
        with urlopen(request, timeout=args.timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.reason}", file=sys.stderr)
        error_body = exc.read().decode("utf-8", errors="replace")
        if error_body:
            print(redact_sensitive(error_body[:4000]), file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Request failed: {redact_sensitive(str(exc.reason))}", file=sys.stderr)
        return 1
    print(body)
    return 0


def cmd_services(_args: argparse.Namespace) -> int:
    service_map = load_service_map()
    for service_name, service in sorted(service_map.get("services", {}).items()):
        print(f"{service_name}\t{service.get('display_name', service_name)}\t{service.get('endpoint_base', '')}")
    return 0


def cmd_objects(_args: argparse.Namespace) -> int:
    for service_name, object_name, endpoint in iter_objects(load_service_map()):
        print(f"{service_name}\t{object_name}\t{endpoint}")
    return 0


def add_url_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--object", default="Media", help="Known object name from service-map.json")
    parser.add_argument("--url", help="Explicit endpoint URL. Overrides --object.")
    parser.add_argument("--q", help="q query text. Confirm endpoint support in docs before live use.")
    parser.add_argument("--by-field", action="append", type=parse_key_value, help="Exact field filter as KEY=VALUE.")
    parser.add_argument("--field", action="append", help="Field to include in the fields projection.")
    parser.add_argument("--param", action="append", type=parse_key_value, help="Additional query parameter as KEY=VALUE.")
    parser.add_argument("--pretty", action="store_true", help="Request pretty JSON when supported.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("services", help="List known services.").set_defaults(func=cmd_services)
    subparsers.add_parser("objects", help="List known objects and endpoints.").set_defaults(func=cmd_objects)

    build_parser = subparsers.add_parser("build-url", help="Build an encoded CVP Data Services URL.")
    add_url_args(build_parser)
    build_parser.set_defaults(func=lambda args: print(build_url(args)) or 0)

    get_parser = subparsers.add_parser("get", help="Run a read-only GET request.")
    add_url_args(get_parser)
    get_parser.add_argument("--header", action="append", type=parse_key_value, help="Runtime request header as KEY=VALUE.")
    get_parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds.")
    get_parser.add_argument("--allow-host", action="append", help="Additional HTTPS host allowed for this request.")
    get_parser.add_argument("--use-keychain", action="store_true", help="Read the runtime credential from macOS Keychain.")
    get_parser.add_argument("--keychain-service", default=DEFAULT_KEYCHAIN_SERVICE, help="Keychain service name.")
    get_parser.add_argument("--keychain-account", default=DEFAULT_KEYCHAIN_ACCOUNT, help="Keychain account name.")
    get_parser.add_argument(
        "--keychain-auth-type",
        choices=("bearer", "authorization", "cookie"),
        default="bearer",
        help="How to apply the Keychain secret to the request.",
    )
    get_parser.add_argument("--yes", action="store_true", help="Skip the extra CLI confirmation before Keychain access.")
    get_parser.set_defaults(func=get_url)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
