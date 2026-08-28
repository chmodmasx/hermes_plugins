#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gitea_client import GiteaClient, GiteaError  # noqa: E402

VERSION_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?")


def parse_version(value: Any) -> tuple[int, int, int | None] | None:
    if isinstance(value, dict):
        value = value.get("version")
    if value is None:
        return None
    match = VERSION_RE.match(str(value).strip().lstrip("v"))
    if not match:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch) if patch is not None else None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Read-only Gitea 1.27 compatibility and health check")
    p.add_argument("--base-url")
    p.add_argument("--token-env", default="GITEA_TOKEN")
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--ca-bundle")
    p.add_argument("--allow-http", action="store_true")
    p.add_argument("--insecure", action="store_true")
    p.add_argument("--strict-127", action="store_true", help="exit non-zero when server is not Gitea 1.27.x")
    args = p.parse_args(argv)

    result: dict[str, Any] = {
        "ok": False,
        "action": "doctor",
        "target_family": "Gitea 1.27.x",
        "checks": {},
        "warnings": [],
    }

    try:
        client = GiteaClient.from_environment(
            base_url=args.base_url,
            token_env=args.token_env,
            timeout=args.timeout,
            ca_bundle=args.ca_bundle,
            allow_http=args.allow_http,
            insecure=args.insecure,
        )
        raw_version = client.server_version()
        parsed = parse_version(raw_version)
        compatible = bool(parsed and parsed[0] == 1 and parsed[1] == 27)
        result["checks"]["server_version"] = raw_version
        result["checks"]["parsed_version"] = list(parsed) if parsed else None
        result["checks"]["compatible_1_27"] = compatible
        if not compatible:
            result["warnings"].append("Server is outside the skill's validated Gitea 1.27.x target family; use live schema discovery before writes.")

        capability = client.capability_summary()
        result["checks"]["swagger_available"] = capability.get("swagger_available")
        result["checks"]["api_schema_version"] = capability.get("openapi")
        result["checks"]["api_operation_count"] = capability.get("operation_count")
        if not capability.get("swagger_available"):
            result["warnings"].append("Live /swagger.v1.json was not available; uncommon operations cannot be capability-checked automatically.")

        result["checks"]["git"] = shutil.which("git")
        result["checks"]["python"] = sys.version.split()[0]

        token_present = bool(os.environ.get(args.token_env))
        result["checks"]["token_present"] = token_present
        if token_present:
            identity = client.whoami()
            result["checks"]["authenticated_identity"] = {
                "login": identity.get("login") if isinstance(identity, dict) else None,
                "id": identity.get("id") if isinstance(identity, dict) else None,
                "is_admin": identity.get("is_admin") if isinstance(identity, dict) else None,
            }
        else:
            result["checks"]["authenticated_identity"] = None
            result["warnings"].append(f"{args.token_env} is not present; authenticated/private and mutating checks were skipped.")

        result["ok"] = True
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.strict_127 and not compatible:
            return 3
        return 0
    except GiteaError as exc:
        result["error"] = {
            "code": exc.code,
            "message": exc.message,
            "http_status": exc.status,
            "retryable": exc.retryable,
            "details": exc.details,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
