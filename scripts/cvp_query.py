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
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


SKILL_ROOT = Path(__file__).resolve().parents[1]
SERVICE_MAP_PATH = SKILL_ROOT / "references" / "service-map.json"
LOCAL_SERVICE_MAP_PATH = SKILL_ROOT / "references" / "local-endpoints.private.json"
DEFAULT_KEYCHAIN_SERVICE = "cvp-query-agent.readonly-token"
DEFAULT_KEYCHAIN_ACCOUNT = "cvp-readonly"
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(cookie\s*[:=]\s*)[^;\n\r]+"),
    re.compile(r"(?i)((?:access_)?token=)[^&\s]+"),
    re.compile(r"(?i)((?:signature|sig|policy)=)[^&\s]+"),
]
SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
    "x-authorization",
}
RUNTIME_AUTH_ENV_VARS = ("CVP_AUTHORIZATION", "CVP_BEARER_TOKEN", "CVP_COOKIE")
SENSITIVE_JSON_KEY_RE = re.compile(
    r"(?i)(url|uri|password|private[_-]?key|protection[_-]?(key|headers)|"
    r"token|cookie|secret|signature|policy|username|user_name)"
)
SAFE_QUERY_PARAMS = {"fields", "_pretty", "form", "pretty"}
DEFAULT_MAX_BYTES = 20000
PLANNED_OBJECTS = {
    "Credit": "Entertainment Data Service object known from docs/datadumps. Configure an Entertainment endpoint in references/local-endpoints.private.json before live use.",
    "Person": "Entertainment Data Service object known from docs/datadumps. Configure an Entertainment endpoint in references/local-endpoints.private.json before live use.",
    "Program": "Entertainment Data Service object known from docs/datadumps. Configure an Entertainment endpoint in references/local-endpoints.private.json before live use.",
    "ProgramAvailability": "Entertainment Data Service object known from docs/datadumps. Configure an Entertainment endpoint in references/local-endpoints.private.json before live use.",
    "Station": "Entertainment Data Service object known from docs/datadumps. Configure an Entertainment endpoint in references/local-endpoints.private.json before live use.",
    "Tag": "Entertainment Data Service object known from docs/datadumps. Configure an Entertainment endpoint in references/local-endpoints.private.json before live use.",
    "TvSeason": "Entertainment Data Service object known from docs/datadumps. Configure an Entertainment endpoint in references/local-endpoints.private.json before live use.",
}


def merge_service_maps(base: dict, overlay: dict) -> dict:
    merged = dict(base)
    services = dict(base.get("services", {}))
    for service_name, service_config in overlay.get("services", {}).items():
        current = dict(services.get(service_name, {}))
        current.update({key: value for key, value in service_config.items() if key != "objects"})
        objects = dict(services.get(service_name, {}).get("objects", {}))
        objects.update(service_config.get("objects", {}))
        current["objects"] = objects
        services[service_name] = current
    merged["services"] = services
    aliases = dict(base.get("aliases", {}))
    aliases.update(overlay.get("aliases", {}))
    merged["aliases"] = aliases
    return merged


def validate_service_map(service_map: dict, source: Path | str) -> None:
    if not isinstance(service_map.get("services", {}), dict):
        raise SystemExit(f"{source} must contain a services object.")
    for service_name, service in service_map.get("services", {}).items():
        if not isinstance(service.get("objects", {}), dict):
            raise SystemExit(f"{source} service '{service_name}' must contain an objects object.")
        for object_name, config in service.get("objects", {}).items():
            endpoint = config.get("endpoint")
            if not endpoint:
                raise SystemExit(f"{source} object '{object_name}' is missing endpoint.")
            parsed = urlparse(endpoint)
            if parsed.scheme != "https" or not parsed.netloc:
                raise SystemExit(f"{source} object '{object_name}' endpoint must be HTTPS.")


def load_service_map() -> dict:
    with SERVICE_MAP_PATH.open("r", encoding="utf-8") as handle:
        service_map = json.load(handle)
    validate_service_map(service_map, SERVICE_MAP_PATH)
    if LOCAL_SERVICE_MAP_PATH.exists():
        with LOCAL_SERVICE_MAP_PATH.open("r", encoding="utf-8") as handle:
            overlay = json.load(handle)
        validate_service_map(overlay, LOCAL_SERVICE_MAP_PATH)
        service_map = merge_service_maps(service_map, overlay)
        validate_service_map(service_map, "merged service map")
    return service_map


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


def known_url_prefixes(service_map: dict) -> list[str]:
    prefixes: list[str] = []
    for service in service_map.get("services", {}).values():
        endpoint_base = service.get("endpoint_base")
        if endpoint_base:
            prefixes.append(endpoint_base.rstrip("/") + "/")
        for config in service.get("objects", {}).values():
            endpoint = config.get("endpoint")
            if endpoint:
                prefixes.append(endpoint.rstrip("/"))
                prefixes.append(endpoint.rstrip("/") + "/")
    return sorted(set(prefixes))


def resolve_object(service_map: dict, object_name: str) -> dict:
    aliases = service_map.get("aliases", {})
    canonical = aliases.get(object_name, object_name)
    canonical = aliases.get(canonical.lower(), canonical)
    for _service_name, candidate, endpoint in iter_objects(service_map):
        if candidate.lower() == canonical.lower():
            return {"name": candidate, "endpoint": endpoint}
    known = ", ".join(sorted({name for _svc, name, _url in iter_objects(service_map)}))
    for planned_name, note in sorted(PLANNED_OBJECTS.items()):
        if planned_name.lower() == object_name.lower() or planned_name.lower() == canonical.lower():
            raise SystemExit(
                f"Known but not live-configured object '{planned_name}'. {note} "
                "See references/endpoints.md#known-but-not-yet-live-configured."
            )
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


def redact_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if SENSITIVE_JSON_KEY_RE.search(str(key)):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_json_value(item)
        return redacted
    if isinstance(value, list):
        return [redact_json_value(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive(value)
    return value


def safe_response_text(body: str, allow_raw_response: bool, max_bytes: int) -> tuple[str, bool]:
    if allow_raw_response:
        text = body
    else:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            text = redact_sensitive(body)
        else:
            text = json.dumps(redact_json_value(parsed), indent=2)
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text, False
    truncated = encoded[:max_bytes].decode("utf-8", errors="replace")
    return truncated, True


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


def runtime_env_auth_vars_present() -> list[str]:
    return [name for name in RUNTIME_AUTH_ENV_VARS if os.environ.get(name)]


def headers_from_runtime(args: argparse.Namespace) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    authorization = os.environ.get("CVP_AUTHORIZATION")
    bearer = os.environ.get("CVP_BEARER_TOKEN")
    cookie = os.environ.get("CVP_COOKIE")
    env_auth = runtime_env_auth_vars_present()
    if len(env_auth) > 1:
        names = ", ".join(env_auth)
        raise SystemExit(f"Refusing multiple environment auth sources. Set only one of {names}.")
    if args.use_keychain:
        if env_auth:
            names = ", ".join(env_auth)
            raise SystemExit(f"Refusing mixed auth sources. Unset {names} before using --use-keychain.")
        apply_keychain_header(headers, args)
    elif authorization:
        headers["Authorization"] = authorization
    elif bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    if cookie:
        headers["Cookie"] = cookie
    for key, value in args.header or []:
        if key.strip().lower() in SENSITIVE_HEADER_NAMES:
            raise SystemExit(
                f"Refusing sensitive header from CLI: {key}. "
                "Use Keychain or CVP_AUTHORIZATION/CVP_BEARER_TOKEN/CVP_COOKIE instead."
            )
        headers[key] = value
    return headers


def validate_auth_args(args: argparse.Namespace) -> None:
    env_auth = runtime_env_auth_vars_present()
    if len(env_auth) > 1:
        names = ", ".join(env_auth)
        raise SystemExit(f"Refusing multiple environment auth sources. Set only one of {names}.")
    if args.use_keychain:
        if env_auth:
            names = ", ".join(env_auth)
            raise SystemExit(f"Refusing mixed auth sources. Unset {names} before using --use-keychain.")
    for key, _value in args.header or []:
        if key.strip().lower() in SENSITIVE_HEADER_NAMES:
            raise SystemExit(
                f"Refusing sensitive header from CLI: {key}. "
                "Use Keychain or CVP_AUTHORIZATION/CVP_BEARER_TOKEN/CVP_COOKIE instead."
            )
    if args.max_bytes < 1:
        raise SystemExit("--max-bytes must be greater than zero.")


def validate_get_url(url: str, args: argparse.Namespace) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise SystemExit("Refusing non-HTTPS request. Use build-url to inspect the URL instead.")
    service_map = load_service_map()
    allowed_hosts = known_hosts(service_map)
    if parsed.netloc.lower() not in allowed_hosts:
        known = ", ".join(sorted(allowed_hosts))
        raise SystemExit(f"Refusing request to unlisted host '{parsed.netloc}'. Known hosts: {known}")
    prefixes = known_url_prefixes(service_map)
    if not any(url == prefix.rstrip("/") or url.startswith(prefix) for prefix in prefixes):
        raise SystemExit("Refusing request outside configured CVP Data Services endpoint prefixes.")


def query_params_from_url(url: str) -> dict[str, list[str]]:
    params: dict[str, list[str]] = {}
    for key, value in parse_qsl(urlparse(url).query, keep_blank_values=True):
        params.setdefault(key, []).append(value)
    return params


def has_fields_projection(args: argparse.Namespace, url: str) -> bool:
    params = query_params_from_url(url)
    return bool(args.field or params.get("fields"))


def has_filter_or_limit(args: argparse.Namespace, url: str) -> bool:
    params = query_params_from_url(url)
    if args.q or args.by_field:
        return True
    for key, values in params.items():
        if key in SAFE_QUERY_PARAMS:
            continue
        if key == "byField" and values:
            return True
        if key == "q" and values:
            return True
        if key.startswith("by") and values:
            return True
        if key in {"contentFilter", "range", "startIndex", "endIndex", "count", "limit"} and values:
            return True
    for key, _value in args.param or []:
        if key not in SAFE_QUERY_PARAMS:
            return True
    return False


def validate_get_scope(args: argparse.Namespace, url: str) -> None:
    if not has_fields_projection(args, url) and not args.allow_raw_response:
        raise SystemExit("Refusing live GET without explicit fields. Add --field values or use --allow-raw-response.")
    if not has_filter_or_limit(args, url) and not args.allow_unfiltered:
        raise SystemExit(
            "Refusing live GET without a filter or range. Add --q/--by-field/structured filters, "
            "or use --allow-unfiltered."
        )


def auth_source_label(args: argparse.Namespace) -> str:
    if args.use_keychain:
        return "Keychain"
    env_auth = runtime_env_auth_vars_present()
    if env_auth:
        return "environment:" + ",".join(env_auth)
    return "none"


def require_live_get_consent(args: argparse.Namespace, url: str) -> None:
    params = query_params_from_url(url)
    fields = args.field or params.get("fields", [])
    filter_keys = sorted(key for key in params if key not in SAFE_QUERY_PARAMS)
    warnings: list[str] = []
    if args.allow_unfiltered:
        warnings.append("unfiltered request override")
    if args.allow_raw_response:
        warnings.append("raw sensitive output override")
    prompt = [
        "About to run CVP read-only GET",
        f"  host: {urlparse(url).netloc}",
        f"  path: {urlparse(url).path}",
        f"  auth source: {auth_source_label(args)}",
        f"  fields: {','.join(fields) if fields else '[none]'}",
        f"  filters/range params: {','.join(filter_keys) if filter_keys else '[none]'}",
        f"  max console bytes: {args.max_bytes}",
    ]
    if warnings:
        prompt.append(f"  warnings: {', '.join(warnings)}")
    prompt.append("Type 'RUN' to continue: ")
    if input("\n".join(prompt)).strip() != "RUN":
        raise SystemExit("Cancelled before live GET.")


def get_url(args: argparse.Namespace) -> int:
    url = args.url or build_url(args)
    validate_auth_args(args)
    validate_get_url(url, args)
    validate_get_scope(args, url)
    require_live_get_consent(args, url)
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
    output, truncated = safe_response_text(body, args.allow_raw_response, args.max_bytes)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote response output to {args.output}", file=sys.stderr)
    else:
        print(output)
    if truncated:
        print(
            f"Output truncated to {args.max_bytes} bytes. Use --output with an explicit scope for a larger artifact.",
            file=sys.stderr,
        )
    return 0


def cmd_services(_args: argparse.Namespace) -> int:
    service_map = load_service_map()
    for service_name, service in sorted(service_map.get("services", {}).items()):
        print(f"{service_name}\t{service.get('display_name', service_name)}\t{service.get('endpoint_base', '')}")
    return 0


def cmd_objects(_args: argparse.Namespace) -> int:
    for service_name, object_name, endpoint in iter_objects(load_service_map()):
        print(f"{service_name}\t{object_name}\t{endpoint}")
    if getattr(_args, "include_planned", False):
        for object_name, note in sorted(PLANNED_OBJECTS.items()):
            print(f"planned\t{object_name}\t{note}")
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
    objects_parser = subparsers.add_parser("objects", help="List known objects and endpoints.")
    objects_parser.add_argument("--include-planned", action="store_true", help="Include known objects that need private endpoint configuration.")
    objects_parser.set_defaults(func=cmd_objects)

    build_parser = subparsers.add_parser("build-url", help="Build an encoded CVP Data Services URL.")
    add_url_args(build_parser)
    build_parser.set_defaults(func=lambda args: print(build_url(args)) or 0)

    get_parser = subparsers.add_parser("get", help="Run a read-only GET request.")
    add_url_args(get_parser)
    get_parser.add_argument("--header", action="append", type=parse_key_value, help="Non-sensitive runtime request header as KEY=VALUE.")
    get_parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds.")
    get_parser.add_argument("--use-keychain", action="store_true", help="Read the runtime credential from macOS Keychain.")
    get_parser.add_argument("--keychain-service", default=DEFAULT_KEYCHAIN_SERVICE, help="Keychain service name.")
    get_parser.add_argument("--keychain-account", default=DEFAULT_KEYCHAIN_ACCOUNT, help="Keychain account name.")
    get_parser.add_argument(
        "--keychain-auth-type",
        choices=("bearer", "authorization", "cookie"),
        default="bearer",
        help="How to apply the Keychain secret to the request.",
    )
    get_parser.add_argument("--allow-unfiltered", action="store_true", help="Allow a live GET without filters or range parameters.")
    get_parser.add_argument("--allow-raw-response", action="store_true", help="Allow unredacted raw response output.")
    get_parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="Maximum response bytes to print or write.")
    get_parser.add_argument("--output", help="Write the redacted/truncated response output to a file instead of stdout.")
    get_parser.set_defaults(func=get_url)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
