#!/usr/bin/env python3
"""
Heuristic static auditor for Gitea Actions workflows.

No external dependencies. This is not a YAML validator and cannot prove
compatibility or security. It flags known migration traps and risky patterns.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Finding:
    severity: str
    code: str
    line: int
    message: str
    evidence: str


PINNED_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
USES_RE = re.compile(r"^\s*(?:-\s*)?uses\s*:\s*([^\s#]+)")
PERMISSION_UNSUPPORTED_RE = re.compile(
    r"^\s*(id-token|checks|statuses|deployments|security-events|pages)\s*:"
)


def finding(severity: str, code: str, line: int, message: str, evidence: str) -> Finding:
    return Finding(severity, code, line, message, evidence.rstrip())


def audit(lines: list[str]) -> list[Finding]:
    out: list[Finding] = []
    text = "\n".join(lines)

    for idx, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        stripped = line.strip()

        m = USES_RE.match(line)
        if m:
            value = m.group(1)
            if value.startswith("./") or value.startswith("docker://"):
                pass
            elif "@" in value:
                ref = value.rsplit("@", 1)[1]
                if ref == "REPLACE_WITH_REVIEWED_COMMIT_SHA":
                    out.append(finding(
                        "INFO", "ACTION_SHA_PLACEHOLDER", idx,
                        "Template placeholder must be replaced with a reviewed 40-character commit SHA.",
                        line,
                    ))
                elif not PINNED_SHA_RE.fullmatch(ref):
                    out.append(finding(
                        "HIGH", "MUTABLE_ACTION_REF", idx,
                        "Third-party action is not pinned to a full 40-character commit SHA.",
                        line,
                    ))
            else:
                out.append(finding(
                    "HIGH", "UNPINNED_ACTION", idx,
                    "Action reference has no explicit immutable ref.",
                    line,
                ))

        if re.match(r"^\s*environment\s*:", line):
            out.append(finding(
                "MEDIUM", "ENVIRONMENT_COMPAT", idx,
                "Do not assume GitHub Environment protection/deployment semantics in Gitea.",
                line,
            ))

        if "pull_request_target" in stripped:
            out.append(finding(
                "HIGH", "PR_TARGET_TRUST", idx,
                "pull_request_target is security-sensitive; never execute untrusted PR code with trusted secrets/privilege.",
                line,
            ))

        if re.search(r"\bwrite-all\b", line):
            out.append(finding(
                "HIGH", "WRITE_ALL", idx,
                "Broad token write permissions violate least-privilege policy.",
                line,
            ))

        if PERMISSION_UNSUPPORTED_RE.match(line):
            out.append(finding(
                "MEDIUM", "GITHUB_PERMISSION_SCOPE", idx,
                "This GitHub-oriented permission scope must be verified/reworked for Gitea.",
                line,
            ))

        if re.match(r"^\s*runs-on\s*:", line) and "${{" in line:
            out.append(finding(
                "MEDIUM", "DYNAMIC_RUNS_ON", idx,
                "Dynamic/complex runs-on behavior is version-sensitive in Gitea.",
                line,
            ))

        if "hashFiles(" in line:
            out.append(finding(
                "MEDIUM", "EXPRESSION_FUNCTION", idx,
                "hashFiles() expression compatibility must be verified on the exact Gitea/Runner versions.",
                line,
            ))

        if re.search(r"(/var/run/docker\.sock|docker\.sock)", line):
            out.append(finding(
                "CRITICAL", "DOCKER_SOCKET", idx,
                "Docker socket exposure can grant host-equivalent control to workflow code.",
                line,
            ))

        if re.search(r"\bprivileged\s*:\s*true\b|--privileged\b", line, re.I):
            out.append(finding(
                "CRITICAL", "PRIVILEGED_EXECUTION", idx,
                "Privileged container execution is unsafe for untrusted workflows.",
                line,
            ))

        if re.search(r"\bset\s+-x\b|\bset\s+-o\s+xtrace\b", line):
            out.append(finding(
                "MEDIUM", "SHELL_XTRACE", idx,
                "Shell tracing can leak secrets into job logs.",
                line,
            ))

        if re.search(r"docker\s+login.*(-p|--password)\s+", line):
            out.append(finding(
                "HIGH", "INLINE_REGISTRY_PASSWORD", idx,
                "Use docker login --password-stdin instead of an inline password argument.",
                line,
            ))

        if "${{ github." in line:
            out.append(finding(
                "INFO", "GITHUB_CONTEXT_ALIAS", idx,
                "GitHub context alias detected; prefer gitea.* for Gitea-native workflows unless portability is intentional.",
                line,
            ))

        if re.search(r"actions/cache@v([0-3])(?:\D|$)", line):
            out.append(finding(
                "MEDIUM", "LEGACY_CACHE_ACTION", idx,
                "Legacy actions/cache major detected; verify against current Gitea Runner cache-service support.",
                line,
            ))

    # Cross-line heuristics
    if "pull_request_target" in text and re.search(r"uses\s*:\s*actions/checkout", text):
        out.append(finding(
            "CRITICAL", "PR_TARGET_CHECKOUT_COMBINATION", 1,
            "Workflow combines pull_request_target with checkout. Prove it never executes contributor-controlled code with trusted context.",
            "workflow-wide pattern",
        ))

    if re.search(r"permissions\s*:\s*\{\s*\}", text):
        out.append(finding(
            "INFO", "EMPTY_PERMISSIONS", 1,
            "Empty permissions may be intentional; verify required Gitea API operations still work.",
            "workflow-wide pattern",
        ))

    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("workflow", type=Path)
    args = parser.parse_args()

    if not args.workflow.is_file():
        print(f"error: not a file: {args.workflow}", file=sys.stderr)
        return 2

    lines = args.workflow.read_text(encoding="utf-8").splitlines()
    findings = audit(lines)

    if args.as_json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        if not findings:
            print("No heuristic findings.")
        else:
            for f in findings:
                print(f"{f.severity:<8} {f.code:<30} line {f.line}")
                print(f"         {f.message}")
                print(f"         {f.evidence}")

    return 1 if any(f.severity in {"CRITICAL", "HIGH"} for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
