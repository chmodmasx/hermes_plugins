"""Policy and validation helpers for the Gitea Hermes plugin."""
from __future__ import annotations

import os
import re
import urllib.parse
from typing import Any

from .client import GiteaError

PLUGIN_VERSION = "1.0.0"
TARGET_GITEA = ">=1.27.0,<1.28"
MAX_PAGE_LIMIT = 50
DEFAULT_MAX_PAGES = 10
DEFAULT_MAX_LOG_CHARS = 120_000
DEFAULT_MAX_FILE_CHARS = 120_000

_SEGMENT_RE = re.compile(r"^[^/\\\x00-\x1f\x7f]+$")


def bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise GiteaError("E_CONFIG", f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise GiteaError("E_CONFIG", f"{name} must be between {minimum} and {maximum}")
    return value


def require_string(args: dict[str, Any], name: str, *, max_len: int = 10000) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise GiteaError("E_VALIDATION", f"{name} is required")
    value = value.strip()
    if len(value) > max_len:
        raise GiteaError("E_VALIDATION", f"{name} exceeds maximum length {max_len}")
    return value


def optional_string(args: dict[str, Any], name: str, *, max_len: int = 100000) -> str | None:
    value = args.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise GiteaError("E_VALIDATION", f"{name} must be a string")
    if len(value) > max_len:
        raise GiteaError("E_VALIDATION", f"{name} exceeds maximum length {max_len}")
    return value


def require_int(args: dict[str, Any], name: str, *, minimum: int = 1) -> int:
    value = args.get(name)
    if isinstance(value, bool):
        raise GiteaError("E_VALIDATION", f"{name} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise GiteaError("E_VALIDATION", f"{name} must be an integer") from exc
    if result < minimum:
        raise GiteaError("E_VALIDATION", f"{name} must be >= {minimum}")
    return result




def bounded_int(args: dict[str, Any], name: str, *, default: int, minimum: int, maximum: int) -> int:
    value = args.get(name, default)
    if isinstance(value, bool):
        raise GiteaError("E_VALIDATION", f"{name} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise GiteaError("E_VALIDATION", f"{name} must be an integer") from exc
    if not minimum <= result <= maximum:
        raise GiteaError("E_VALIDATION", f"{name} must be between {minimum} and {maximum}")
    return result


def optional_bool(args: dict[str, Any], name: str) -> bool | None:
    value = args.get(name)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise GiteaError("E_VALIDATION", f"{name} must be a boolean")
    return value

def segment(value: str) -> str:
    if not _SEGMENT_RE.match(value):
        raise GiteaError("E_VALIDATION", "Invalid path segment")
    return urllib.parse.quote(value, safe="")


def repo_path(owner: str, repo: str) -> str:
    return f"/repos/{segment(owner)}/{segment(repo)}"


def content_path(path: str) -> str:
    if "\x00" in path or path.startswith("/") or "\\" in path:
        raise GiteaError("E_VALIDATION", "Repository path must be relative and use '/' separators")
    parts = [p for p in path.split("/") if p not in {"", "."}]
    if any(p == ".." for p in parts):
        raise GiteaError("E_VALIDATION", "Repository path traversal is forbidden")
    return "/".join(urllib.parse.quote(p, safe="") for p in parts)


def page_limit(args: dict[str, Any]) -> tuple[int, int]:
    try:
        limit = int(args.get("limit", 30))
        max_pages = int(args.get("max_pages", int_env("GITEA_MAX_PAGES", DEFAULT_MAX_PAGES, minimum=1, maximum=50)))
    except (TypeError, ValueError) as exc:
        raise GiteaError("E_VALIDATION", "limit and max_pages must be integers") from exc
    if not 1 <= limit <= MAX_PAGE_LIMIT:
        raise GiteaError("E_VALIDATION", f"limit must be 1..{MAX_PAGE_LIMIT}")
    if not 1 <= max_pages <= 50:
        raise GiteaError("E_VALIDATION", "max_pages must be 1..50")
    return limit, max_pages


def client_kwargs() -> dict[str, Any]:
    raw_timeout = os.environ.get("GITEA_TIMEOUT", "30")
    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        raise GiteaError("E_CONFIG", "GITEA_TIMEOUT must be a number") from exc
    if not 1 <= timeout <= 300:
        raise GiteaError("E_CONFIG", "GITEA_TIMEOUT must be between 1 and 300 seconds")
    return {
        "allow_http": bool_env("GITEA_ALLOW_HTTP"),
        "insecure": bool_env("GITEA_INSECURE_TLS"),
        "ca_bundle": os.environ.get("GITEA_CA_BUNDLE") or None,
        "timeout": timeout,
        "max_attempts": int_env("GITEA_MAX_ATTEMPTS", 3, minimum=1, maximum=6),
        "user_agent": f"hermes-gitea-plugin/{PLUGIN_VERSION}",
    }
