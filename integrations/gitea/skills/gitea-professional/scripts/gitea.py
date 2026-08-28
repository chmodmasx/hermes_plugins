#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gitea_client import GiteaClient, GiteaError, parse_key_values  # noqa: E402


VERSION = "2.0.0"


def seg(value: Any) -> str:
    return urllib.parse.quote(str(value), safe="")


def emit_ok(action: str, data: Any = None, *, warnings: list[str] | None = None) -> int:
    print(json.dumps({
        "ok": True,
        "action": action,
        "data": data,
        "warnings": warnings or [],
    }, ensure_ascii=False, indent=2, sort_keys=False))
    return 0


def emit_error(action: str, exc: GiteaError) -> int:
    print(json.dumps({
        "ok": False,
        "action": action,
        "error": {
            "code": exc.code,
            "message": exc.message,
            "http_status": exc.status,
            "retryable": exc.retryable,
            "details": exc.details,
        },
    }, ensure_ascii=False, indent=2, sort_keys=False))
    return 2


def load_json_payload(args: argparse.Namespace) -> Any:
    sources = [
        bool(getattr(args, "json", None)),
        bool(getattr(args, "json_file", None)),
        bool(getattr(args, "stdin_json", False)),
    ]
    if sum(sources) > 1:
        raise GiteaError("E_VALIDATION", "Use only one of --json, --json-file, --stdin-json")
    if getattr(args, "json", None):
        try:
            return json.loads(args.json)
        except json.JSONDecodeError as exc:
            raise GiteaError("E_VALIDATION", f"Invalid JSON: {exc}") from None
    if getattr(args, "json_file", None):
        try:
            return json.loads(Path(args.json_file).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GiteaError("E_VALIDATION", f"Cannot read JSON file: {exc}") from None
    if getattr(args, "stdin_json", False):
        try:
            return json.load(sys.stdin)
        except json.JSONDecodeError as exc:
            raise GiteaError("E_VALIDATION", f"Invalid JSON on stdin: {exc}") from None
    return None


def build_client(args: argparse.Namespace) -> GiteaClient:
    return GiteaClient.from_environment(
        base_url=args.base_url,
        token_env=args.token_env,
        timeout=args.timeout,
        ca_bundle=args.ca_bundle,
        insecure=args.insecure,
        allow_http=args.allow_http,
        max_attempts=args.max_attempts,
    )


def require_token(client: GiteaClient) -> None:
    if not client.token:
        raise GiteaError("E_AUTH_REQUIRED", "This operation requires GITEA_TOKEN")


def require_confirm(actual: str | None, expected: str) -> None:
    if actual != expected:
        raise GiteaError(
            "E_CONFIRMATION_REQUIRED",
            f"Explicit confirmation required. Re-run with --confirm {json.dumps(expected)}",
            details={"expected_confirmation": expected},
        )


def bool_flag(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected true/false")


def common_repo_payload(args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": args.name,
        "private": args.private,
        "auto_init": args.auto_init,
    }
    for key in ("description", "default_branch", "gitignores", "license", "readme", "trust_model"):
        value = getattr(args, key, None)
        if value not in (None, ""):
            body[key] = value
    return body


def cmd_version(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("instance.version", client.server_version())


def cmd_whoami(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("auth.whoami", client.whoami())


def cmd_capabilities(client: GiteaClient, args: argparse.Namespace) -> int:
    data = client.capability_summary()
    if args.search:
        data["matches"] = client.search_swagger(args.search, method=args.method, tag=args.tag)
    return emit_ok("instance.capabilities", data)


def cmd_schema(client: GiteaClient, args: argparse.Namespace) -> int:
    matches = client.search_swagger(args.search, method=args.method, tag=args.tag)
    return emit_ok("schema.search", {"count": len(matches), "matches": matches[:args.limit]})


def cmd_get(client: GiteaClient, args: argparse.Namespace) -> int:
    query = parse_key_values(args.param)
    if args.paginate:
        return emit_ok("api.get.paginate", client.paginate(args.path, query=query, limit=args.limit, max_pages=args.max_pages))
    response = client.request("GET", args.path, query=query)
    return emit_ok("api.get", {"status": response.status, "data": response.data})


def generic_write_confirmation(method: str, path: str) -> str:
    return f"WRITE:{method.upper()}:{path}"


def cmd_request(client: GiteaClient, args: argparse.Namespace) -> int:
    method = args.method.upper()
    query = parse_key_values(args.param)
    body = load_json_payload(args)
    if method not in {"GET", "HEAD", "OPTIONS"}:
        require_token(client)
        if not args.write_ok:
            raise GiteaError("E_WRITE_GUARD", "Mutating generic API calls require --write-ok")
        if method == "DELETE" or args.path.startswith("/admin/") or "/merge" in args.path:
            require_confirm(args.confirm, generic_write_confirmation(method, args.path))
    response = client.request(method, args.path, query=query, body=body)
    return emit_ok("api.request", {"status": response.status, "data": response.data})


def cmd_repo_get(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("repo.get", client.get(f"/repos/{args.owner}/{args.repo}"))


def cmd_repo_create_user(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    body = common_repo_payload(args)
    identity = client.whoami()
    owner = args.owner_hint or (identity.get("login") if isinstance(identity, dict) else None)
    if not owner:
        raise GiteaError("E_SHAPE", "Could not determine authenticated user's owner name")
    repo_path = f"/repos/{seg(owner)}/{seg(args.name)}"
    existing = client.try_get(repo_path)
    if existing:
        if args.if_exists == "return":
            return emit_ok("repo.create_user", existing, warnings=["Repository already existed; no mutation performed."])
        raise GiteaError("E_CONFLICT", "Repository already exists")
    try:
        response = client.request("POST", "/user/repos", body=body)
    except GiteaError as exc:
        if exc.code not in {"E_CONFLICT", "E_TRANSIENT"}:
            raise
        reconciled = client.try_get(repo_path)
        if reconciled is None:
            raise
        return emit_ok("repo.create_user", reconciled, warnings=["Create response was ambiguous; reconciled existing repository state."])
    verified = client.get(repo_path)
    return emit_ok("repo.create_user", {"created": response.data, "verified": verified})


def cmd_repo_create_org(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    body = common_repo_payload(args)
    existing = client.try_get(f"/repos/{seg(args.org)}/{seg(args.name)}")
    if existing:
        if args.if_exists == "return":
            return emit_ok("repo.create_org", existing, warnings=["Repository already existed; no mutation performed."])
        raise GiteaError("E_CONFLICT", "Repository already exists")
    try:
        response = client.request("POST", f"/orgs/{seg(args.org)}/repos", body=body)
    except GiteaError as exc:
        if exc.code not in {"E_CONFLICT", "E_TRANSIENT"}:
            raise
        reconciled = client.try_get(f"/repos/{seg(args.org)}/{seg(args.name)}")
        if reconciled is None:
            raise
        return emit_ok("repo.create_org", reconciled, warnings=["Create response was ambiguous; reconciled existing repository state."])
    verified = client.get(f"/repos/{seg(args.org)}/{seg(args.name)}")
    return emit_ok("repo.create_org", {"created": response.data, "verified": verified})


def cmd_repo_delete(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    confirm = f"DELETE_REPO:{args.owner}/{args.repo}"
    require_confirm(args.confirm, confirm)
    client.request("DELETE", f"/repos/{args.owner}/{args.repo}")
    remains = client.try_get(f"/repos/{args.owner}/{args.repo}")
    if remains is not None:
        raise GiteaError("E_POSTCONDITION", "Repository still exists after DELETE")
    return emit_ok("repo.delete", {"deleted": f"{args.owner}/{args.repo}"})


def cmd_repo_edit(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    body = load_json_payload(args)
    if not isinstance(body, dict) or not body:
        raise GiteaError("E_VALIDATION", "repo edit requires a non-empty JSON object")
    response = client.request("PATCH", f"/repos/{args.owner}/{args.repo}", body=body)
    verified = client.get(f"/repos/{args.owner}/{args.repo}")
    return emit_ok("repo.edit", {"response": response.data, "verified": verified})


def cmd_branch_list(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("branch.list", client.paginate(f"/repos/{args.owner}/{args.repo}/branches", limit=args.limit))


def cmd_branch_create(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    body = {"new_branch_name": args.name}
    if args.old_ref:
        body["old_ref_name"] = args.old_ref
    existing = client.try_get(f"/repos/{seg(args.owner)}/{seg(args.repo)}/branches/{seg(args.name)}")
    if existing:
        if args.if_exists == "return":
            return emit_ok("branch.create", existing, warnings=["Branch already existed; no mutation performed."])
        raise GiteaError("E_CONFLICT", "Branch already exists")
    client.request("POST", f"/repos/{args.owner}/{args.repo}/branches", body=body)
    verified = client.get(f"/repos/{seg(args.owner)}/{seg(args.repo)}/branches/{seg(args.name)}")
    return emit_ok("branch.create", verified)


def cmd_branch_delete(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    confirm = f"DELETE_BRANCH:{args.owner}/{args.repo}:{args.name}"
    require_confirm(args.confirm, confirm)
    client.request("DELETE", f"/repos/{seg(args.owner)}/{seg(args.repo)}/branches/{seg(args.name)}")
    remains = client.try_get(f"/repos/{seg(args.owner)}/{seg(args.repo)}/branches/{seg(args.name)}")
    if remains is not None:
        raise GiteaError("E_POSTCONDITION", "Branch still exists after DELETE")
    return emit_ok("branch.delete", {"deleted": args.name})


def cmd_tag_list(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("tag.list", client.paginate(f"/repos/{args.owner}/{args.repo}/tags", limit=args.limit))


def cmd_tag_create(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    body: dict[str, Any] = {"tag_name": args.name}
    if args.target:
        body["target"] = args.target
    if args.message:
        body["message"] = args.message
    response = client.request("POST", f"/repos/{args.owner}/{args.repo}/tags", body=body)
    return emit_ok("tag.create", response.data)


def cmd_tag_delete(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    confirm = f"DELETE_TAG:{args.owner}/{args.repo}:{args.name}"
    require_confirm(args.confirm, confirm)
    client.request("DELETE", f"/repos/{seg(args.owner)}/{seg(args.repo)}/tags/{seg(args.name)}")
    return emit_ok("tag.delete", {"deleted": args.name})


def cmd_issue_list(client: GiteaClient, args: argparse.Namespace) -> int:
    query: dict[str, Any] = {}
    if args.state:
        query["state"] = args.state
    if args.labels:
        query["labels"] = args.labels
    if args.q:
        query["q"] = args.q
    return emit_ok("issue.list", client.paginate(f"/repos/{args.owner}/{args.repo}/issues", query=query, limit=args.limit))


def cmd_issue_get(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("issue.get", client.get(f"/repos/{args.owner}/{args.repo}/issues/{args.index}"))


def cmd_issue_create(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    body: dict[str, Any] = {"title": args.title}
    if args.body is not None:
        body["body"] = args.body
    if args.labels:
        body["labels"] = [int(x) for x in args.labels.split(",") if x.strip()]
    if args.assignees:
        body["assignees"] = [x.strip() for x in args.assignees.split(",") if x.strip()]
    if args.milestone is not None:
        body["milestone"] = args.milestone
    response = client.request("POST", f"/repos/{args.owner}/{args.repo}/issues", body=body)
    issue = response.data
    index = issue.get("number") if isinstance(issue, dict) else None
    verified = client.get(f"/repos/{args.owner}/{args.repo}/issues/{index}") if index is not None else issue
    return emit_ok("issue.create", verified)


def cmd_issue_edit(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    body = load_json_payload(args)
    if not isinstance(body, dict) or not body:
        raise GiteaError("E_VALIDATION", "issue edit requires a non-empty JSON object")
    client.request("PATCH", f"/repos/{args.owner}/{args.repo}/issues/{args.index}", body=body)
    verified = client.get(f"/repos/{args.owner}/{args.repo}/issues/{args.index}")
    return emit_ok("issue.edit", verified)


def cmd_issue_delete(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    confirm = f"DELETE_ISSUE:{args.owner}/{args.repo}#{args.index}"
    require_confirm(args.confirm, confirm)
    client.request("DELETE", f"/repos/{args.owner}/{args.repo}/issues/{args.index}")
    remains = client.try_get(f"/repos/{args.owner}/{args.repo}/issues/{args.index}")
    if remains is not None:
        raise GiteaError("E_POSTCONDITION", "Issue still exists after DELETE")
    return emit_ok("issue.delete", {"deleted": args.index})


def cmd_issue_comment(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    response = client.request(
        "POST",
        f"/repos/{args.owner}/{args.repo}/issues/{args.index}/comments",
        body={"body": args.body},
    )
    return emit_ok("issue.comment", response.data)


def cmd_pr_list(client: GiteaClient, args: argparse.Namespace) -> int:
    query = {"state": args.state} if args.state else {}
    return emit_ok("pr.list", client.paginate(f"/repos/{args.owner}/{args.repo}/pulls", query=query, limit=args.limit))


def cmd_pr_get(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("pr.get", client.get(f"/repos/{args.owner}/{args.repo}/pulls/{args.index}"))


def cmd_pr_create(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    body: dict[str, Any] = {"head": args.head, "base": args.base, "title": args.title}
    if args.body is not None:
        body["body"] = args.body
    if args.assignees:
        body["assignees"] = [x.strip() for x in args.assignees.split(",") if x.strip()]
    if args.reviewers:
        body["reviewers"] = [x.strip() for x in args.reviewers.split(",") if x.strip()]
    if args.labels:
        body["labels"] = [int(x) for x in args.labels.split(",") if x.strip()]
    response = client.request("POST", f"/repos/{args.owner}/{args.repo}/pulls", body=body)
    pr = response.data
    index = pr.get("number") or pr.get("index") if isinstance(pr, dict) else None
    verified = client.get(f"/repos/{args.owner}/{args.repo}/pulls/{index}") if index is not None else pr
    return emit_ok("pr.create", verified)


def cmd_pr_review(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    pr = client.get(f"/repos/{args.owner}/{args.repo}/pulls/{args.index}")
    current_sha = ((pr or {}).get("head") or {}).get("sha") if isinstance(pr, dict) else None
    if not current_sha:
        raise GiteaError("E_SHAPE", "Could not determine PR head SHA")
    if args.head_sha and args.head_sha != current_sha:
        raise GiteaError("E_STALE_HEAD", f"PR head changed: expected {args.head_sha}, current {current_sha}")
    body = {"event": args.event, "body": args.body or "", "commit_id": current_sha}
    response = client.request("POST", f"/repos/{args.owner}/{args.repo}/pulls/{args.index}/reviews", body=body)
    return emit_ok("pr.review", {"head_sha": current_sha, "review": response.data})


def combined_state(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    value = data.get("state") or data.get("status")
    return str(value).lower() if value is not None else None


def cmd_pr_merge(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    path = f"/repos/{args.owner}/{args.repo}/pulls/{args.index}"
    pr = client.get(path)
    if not isinstance(pr, dict):
        raise GiteaError("E_SHAPE", "Pull request response is not an object")
    if pr.get("merged"):
        return emit_ok("pr.merge", {"status": "already_merged", "pull_request": pr})
    if str(pr.get("state", "")).lower() != "open":
        raise GiteaError("E_CONFLICT", "Pull request is not open")
    current_sha = ((pr.get("head") or {}).get("sha"))
    if not current_sha:
        raise GiteaError("E_SHAPE", "Could not determine PR head SHA")
    if args.head_sha != current_sha:
        raise GiteaError("E_STALE_HEAD", f"PR head changed: expected {args.head_sha}, current {current_sha}")

    status = client.get(f"/repos/{args.owner}/{args.repo}/commits/{current_sha}/status")
    state = combined_state(status)
    if not args.allow_non_green and state not in {"success"}:
        raise GiteaError(
            "E_CI_NOT_GREEN",
            f"Combined commit status is {state!r}; merge blocked by skill policy",
            details=status,
        )

    confirm = f"MERGE:{args.owner}/{args.repo}#{args.index}@{current_sha}"
    require_confirm(args.confirm, confirm)

    body = {
        "do": args.strategy,
        "head_commit_id": current_sha,
        "delete_branch_after_merge": args.delete_branch,
        "force_merge": False,
    }
    response = client.request("POST", f"{path}/merge", body=body)
    final = client.get(path)
    if not isinstance(final, dict) or not final.get("merged"):
        raise GiteaError("E_POSTCONDITION", "Merge request completed but PR is not reported as merged", details=final)
    return emit_ok("pr.merge", {
        "status": "merged",
        "reviewed_head_sha": current_sha,
        "ci_state": state,
        "merge_response": response.data,
        "pull_request": final,
    })


def cmd_pr_commits(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("pr.commits", client.paginate(f"/repos/{args.owner}/{args.repo}/pulls/{args.index}/commits", limit=args.limit))


def cmd_pr_files(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("pr.files", client.paginate(f"/repos/{args.owner}/{args.repo}/pulls/{args.index}/files", limit=args.limit))


def cmd_actions_runs(client: GiteaClient, args: argparse.Namespace) -> int:
    query = parse_key_values(args.param)
    return emit_ok("actions.runs", client.get(f"/repos/{args.owner}/{args.repo}/actions/runs", query=query))


def cmd_actions_jobs(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("actions.jobs", client.get(f"/repos/{args.owner}/{args.repo}/actions/runs/{args.run_id}/jobs"))


def cmd_actions_dispatch(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    inputs: dict[str, str] = {}
    sensitive_values: list[str] = []
    for item in args.input:
        if "=" not in item:
            raise GiteaError("E_VALIDATION", f"Expected KEY=VALUE for --input, got {item!r}")
        key, value = item.split("=", 1)
        inputs[key] = value
    for item in args.input_env:
        if "=" not in item:
            raise GiteaError("E_VALIDATION", f"Expected KEY=ENV_VAR for --input-env, got {item!r}")
        key, env_name = item.split("=", 1)
        value = os.environ.get(env_name)
        if value is None:
            raise GiteaError("E_SECRET_INPUT", f"Environment variable {env_name!r} is not set")
        inputs[key] = value
        sensitive_values.append(value)
    body = {"ref": args.ref, "inputs": inputs}
    response = client.request(
        "POST",
        f"/repos/{seg(args.owner)}/{seg(args.repo)}/actions/workflows/{seg(args.workflow)}/dispatches",
        query={"return_run_details": "true"},
        body=body,
        sensitive_values=sensitive_values,
    )
    return emit_ok("actions.dispatch", response.data)


def cmd_actions_rerun(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    confirm = f"RERUN:{args.owner}/{args.repo}:{args.run_id}"
    require_confirm(args.confirm, confirm)
    response = client.request("POST", f"/repos/{seg(args.owner)}/{seg(args.repo)}/actions/runs/{seg(args.run_id)}/rerun")
    return emit_ok("actions.rerun", response.data)


def cmd_actions_secret_list(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    data = client.get(f"/repos/{seg(args.owner)}/{seg(args.repo)}/actions/secrets")
    return emit_ok("actions.secret_list", data)


def cmd_actions_secret_set(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    value = os.environ.get(args.value_env)
    if value is None:
        raise GiteaError("E_SECRET_INPUT", f"Environment variable {args.value_env!r} is not set")
    confirm = f"SET_SECRET:{args.owner}/{args.repo}:{args.name}"
    require_confirm(args.confirm, confirm)
    body = {"data": value}
    if args.description is not None:
        body["description"] = args.description
    client.request(
        "PUT",
        f"/repos/{seg(args.owner)}/{seg(args.repo)}/actions/secrets/{seg(args.name)}",
        body=body,
        sensitive_values=[value],
    )
    listed = client.get(f"/repos/{seg(args.owner)}/{seg(args.repo)}/actions/secrets")
    names = []
    if isinstance(listed, list):
        names = [str(x.get("name")) for x in listed if isinstance(x, dict) and x.get("name") is not None]
    elif isinstance(listed, dict):
        raw = listed.get("secrets") or listed.get("items") or []
        if isinstance(raw, list):
            names = [str(x.get("name")) for x in raw if isinstance(x, dict) and x.get("name") is not None]
    return emit_ok("actions.secret_set", {
        "name": args.name,
        "present_after_write": args.name in names if names else None,
        "value_exposed": False,
    })


def cmd_actions_secret_delete(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    confirm = f"DELETE_SECRET:{args.owner}/{args.repo}:{args.name}"
    require_confirm(args.confirm, confirm)
    client.request("DELETE", f"/repos/{seg(args.owner)}/{seg(args.repo)}/actions/secrets/{seg(args.name)}")
    return emit_ok("actions.secret_delete", {"deleted": args.name, "value_exposed": False})


def cmd_release_list(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("release.list", client.paginate(f"/repos/{args.owner}/{args.repo}/releases", limit=args.limit))


def cmd_release_create(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    body: dict[str, Any] = {
        "tag_name": args.tag,
        "name": args.name or args.tag,
        "body": args.body or "",
        "draft": args.draft,
        "prerelease": args.prerelease,
    }
    if args.target:
        body["target_commitish"] = args.target
    response = client.request("POST", f"/repos/{args.owner}/{args.repo}/releases", body=body)
    return emit_ok("release.create", response.data)


def cmd_release_delete(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    confirm = f"DELETE_RELEASE:{args.owner}/{args.repo}:{args.release_id}"
    require_confirm(args.confirm, confirm)
    client.request("DELETE", f"/repos/{args.owner}/{args.repo}/releases/{args.release_id}")
    return emit_ok("release.delete", {"deleted_release_id": args.release_id})


def wiki_payload_from_file(path: str, title: str | None, message: str | None) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    body: dict[str, Any] = {"content_base64": base64.b64encode(raw).decode("ascii")}
    if title is not None:
        body["title"] = title
    if message is not None:
        body["message"] = message
    return body


def cmd_wiki_list(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("wiki.list", client.paginate(f"/repos/{args.owner}/{args.repo}/wiki/pages", limit=args.limit))


def cmd_wiki_get(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("wiki.get", client.get(f"/repos/{seg(args.owner)}/{seg(args.repo)}/wiki/page/{seg(args.page)}"))


def cmd_wiki_create(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    body = wiki_payload_from_file(args.file, args.title, args.message)
    response = client.request("POST", f"/repos/{args.owner}/{args.repo}/wiki/new", body=body)
    return emit_ok("wiki.create", response.data)


def cmd_wiki_edit(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    body = wiki_payload_from_file(args.file, args.title, args.message)
    response = client.request("PATCH", f"/repos/{seg(args.owner)}/{seg(args.repo)}/wiki/page/{seg(args.page)}", body=body)
    return emit_ok("wiki.edit", response.data)


def cmd_wiki_delete(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    confirm = f"DELETE_WIKI:{args.owner}/{args.repo}:{args.page}"
    require_confirm(args.confirm, confirm)
    client.request("DELETE", f"/repos/{seg(args.owner)}/{seg(args.repo)}/wiki/page/{seg(args.page)}")
    return emit_ok("wiki.delete", {"deleted_page": args.page})


def cmd_package_list(client: GiteaClient, args: argparse.Namespace) -> int:
    query: dict[str, Any] = {}
    if args.type:
        query["type"] = args.type
    if args.q:
        query["q"] = args.q
    return emit_ok("package.list", client.paginate(f"/packages/{seg(args.owner)}", query=query, limit=args.limit))


def cmd_package_versions(client: GiteaClient, args: argparse.Namespace) -> int:
    return emit_ok("package.versions", client.paginate(f"/packages/{seg(args.owner)}/{seg(args.type)}/{seg(args.name)}", limit=args.limit))


def cmd_contents_change(client: GiteaClient, args: argparse.Namespace) -> int:
    require_token(client)
    body = load_json_payload(args)
    if not isinstance(body, dict):
        raise GiteaError("E_VALIDATION", "contents change requires a JSON object")
    if body.get("force_push") and not args.allow_force_push:
        raise GiteaError("E_POLICY", "force_push=true requires --allow-force-push")
    response = client.request("POST", f"/repos/{args.owner}/{args.repo}/contents", body=body)
    return emit_ok("contents.change", response.data)


def add_json_source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", help="JSON body inline")
    parser.add_argument("--json-file", help="Read JSON body from file")
    parser.add_argument("--stdin-json", action="store_true", help="Read JSON body from stdin")


def add_repo_create_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("name")
    parser.add_argument("--private", type=bool_flag, default=True)
    parser.add_argument("--auto-init", type=bool_flag, default=True)
    parser.add_argument("--description")
    parser.add_argument("--default-branch")
    parser.add_argument("--gitignores")
    parser.add_argument("--license")
    parser.add_argument("--readme")
    parser.add_argument("--trust-model")
    parser.add_argument("--if-exists", choices=["error", "return"], default="return")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Deterministic Gitea helper for Hermes Agent")
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    p.add_argument("--base-url", help="Gitea instance base URL; falls back to GITEA_BASE_URL")
    p.add_argument("--token-env", default="GITEA_TOKEN", help="Environment variable containing the API token")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--max-attempts", type=int, default=4)
    p.add_argument("--ca-bundle", help="Custom CA bundle path")
    p.add_argument("--insecure", action="store_true", help="Disable TLS verification; avoid except controlled testing")
    p.add_argument("--allow-http", action="store_true", help="Allow plain HTTP; avoid except trusted local networks")

    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("version")
    sp.set_defaults(func=cmd_version)

    sp = sub.add_parser("whoami")
    sp.set_defaults(func=cmd_whoami)

    sp = sub.add_parser("capabilities")
    sp.add_argument("--search")
    sp.add_argument("--method")
    sp.add_argument("--tag")
    sp.set_defaults(func=cmd_capabilities)

    sp = sub.add_parser("schema")
    sp.add_argument("--search", required=True)
    sp.add_argument("--method")
    sp.add_argument("--tag")
    sp.add_argument("--limit", type=int, default=50)
    sp.set_defaults(func=cmd_schema)

    sp = sub.add_parser("get")
    sp.add_argument("path")
    sp.add_argument("--param", action="append", default=[])
    sp.add_argument("--paginate", action="store_true")
    sp.add_argument("--limit", type=int, default=50)
    sp.add_argument("--max-pages", type=int, default=1000)
    sp.set_defaults(func=cmd_get)

    sp = sub.add_parser("request")
    sp.add_argument("method")
    sp.add_argument("path")
    sp.add_argument("--param", action="append", default=[])
    add_json_source_args(sp)
    sp.add_argument("--write-ok", action="store_true")
    sp.add_argument("--confirm")
    sp.set_defaults(func=cmd_request)

    repo = sub.add_parser("repo").add_subparsers(dest="repo_cmd", required=True)
    sp = repo.add_parser("get")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.set_defaults(func=cmd_repo_get)
    sp = repo.add_parser("create-user")
    add_repo_create_args(sp); sp.add_argument("--owner-hint", help="Optional expected owner for idempotency pre-check")
    sp.set_defaults(func=cmd_repo_create_user)
    sp = repo.add_parser("create-org")
    sp.add_argument("org"); add_repo_create_args(sp); sp.set_defaults(func=cmd_repo_create_org)
    sp = repo.add_parser("edit")
    sp.add_argument("owner"); sp.add_argument("repo"); add_json_source_args(sp); sp.set_defaults(func=cmd_repo_edit)
    sp = repo.add_parser("delete")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("--confirm"); sp.set_defaults(func=cmd_repo_delete)

    branch = sub.add_parser("branch").add_subparsers(dest="branch_cmd", required=True)
    sp = branch.add_parser("list")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("--limit", type=int, default=50); sp.set_defaults(func=cmd_branch_list)
    sp = branch.add_parser("create")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("name"); sp.add_argument("--old-ref"); sp.add_argument("--if-exists", choices=["error", "return"], default="return"); sp.set_defaults(func=cmd_branch_create)
    sp = branch.add_parser("delete")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("name"); sp.add_argument("--confirm"); sp.set_defaults(func=cmd_branch_delete)

    tag = sub.add_parser("tag").add_subparsers(dest="tag_cmd", required=True)
    sp = tag.add_parser("list")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("--limit", type=int, default=50); sp.set_defaults(func=cmd_tag_list)
    sp = tag.add_parser("create")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("name"); sp.add_argument("--target"); sp.add_argument("--message"); sp.set_defaults(func=cmd_tag_create)
    sp = tag.add_parser("delete")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("name"); sp.add_argument("--confirm"); sp.set_defaults(func=cmd_tag_delete)

    issue = sub.add_parser("issue").add_subparsers(dest="issue_cmd", required=True)
    sp = issue.add_parser("list")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("--state", choices=["open", "closed", "all"]); sp.add_argument("--labels"); sp.add_argument("--q"); sp.add_argument("--limit", type=int, default=50); sp.set_defaults(func=cmd_issue_list)
    sp = issue.add_parser("get")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("index", type=int); sp.set_defaults(func=cmd_issue_get)
    sp = issue.add_parser("create")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("--title", required=True); sp.add_argument("--body"); sp.add_argument("--labels", help="Comma-separated label IDs"); sp.add_argument("--assignees"); sp.add_argument("--milestone", type=int); sp.set_defaults(func=cmd_issue_create)
    sp = issue.add_parser("edit")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("index", type=int); add_json_source_args(sp); sp.set_defaults(func=cmd_issue_edit)
    sp = issue.add_parser("delete")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("index", type=int); sp.add_argument("--confirm"); sp.set_defaults(func=cmd_issue_delete)
    sp = issue.add_parser("comment")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("index", type=int); sp.add_argument("--body", required=True); sp.set_defaults(func=cmd_issue_comment)

    pr = sub.add_parser("pr").add_subparsers(dest="pr_cmd", required=True)
    sp = pr.add_parser("list")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("--state", choices=["open", "closed", "all"]); sp.add_argument("--limit", type=int, default=50); sp.set_defaults(func=cmd_pr_list)
    sp = pr.add_parser("get")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("index", type=int); sp.set_defaults(func=cmd_pr_get)
    sp = pr.add_parser("create")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("--head", required=True); sp.add_argument("--base", required=True); sp.add_argument("--title", required=True); sp.add_argument("--body"); sp.add_argument("--assignees"); sp.add_argument("--reviewers"); sp.add_argument("--labels"); sp.set_defaults(func=cmd_pr_create)
    sp = pr.add_parser("review")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("index", type=int); sp.add_argument("--event", choices=["APPROVED", "REQUEST_CHANGES", "COMMENT"], required=True); sp.add_argument("--body"); sp.add_argument("--head-sha"); sp.set_defaults(func=cmd_pr_review)
    sp = pr.add_parser("merge")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("index", type=int); sp.add_argument("--head-sha", required=True); sp.add_argument("--strategy", choices=["merge", "squash", "rebase", "rebase-merge"], default="merge"); sp.add_argument("--delete-branch", type=bool_flag, default=True); sp.add_argument("--allow-non-green", action="store_true"); sp.add_argument("--confirm"); sp.set_defaults(func=cmd_pr_merge)
    sp = pr.add_parser("commits")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("index", type=int); sp.add_argument("--limit", type=int, default=50); sp.set_defaults(func=cmd_pr_commits)
    sp = pr.add_parser("files")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("index", type=int); sp.add_argument("--limit", type=int, default=50); sp.set_defaults(func=cmd_pr_files)

    actions = sub.add_parser("actions").add_subparsers(dest="actions_cmd", required=True)
    sp = actions.add_parser("runs")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("--param", action="append", default=[]); sp.set_defaults(func=cmd_actions_runs)
    sp = actions.add_parser("jobs")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("run_id"); sp.set_defaults(func=cmd_actions_jobs)
    sp = actions.add_parser("dispatch")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("workflow"); sp.add_argument("--ref", required=True); sp.add_argument("--input", action="append", default=[]); sp.add_argument("--input-env", action="append", default=[], help="KEY=ENV_VAR; reads sensitive workflow input from environment"); sp.set_defaults(func=cmd_actions_dispatch)
    sp = actions.add_parser("rerun")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("run_id"); sp.add_argument("--confirm"); sp.set_defaults(func=cmd_actions_rerun)
    sp = actions.add_parser("secret-list")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.set_defaults(func=cmd_actions_secret_list)
    sp = actions.add_parser("secret-set")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("name"); sp.add_argument("--value-env", required=True, help="Environment variable containing the secret value"); sp.add_argument("--description"); sp.add_argument("--confirm"); sp.set_defaults(func=cmd_actions_secret_set)
    sp = actions.add_parser("secret-delete")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("name"); sp.add_argument("--confirm"); sp.set_defaults(func=cmd_actions_secret_delete)

    release = sub.add_parser("release").add_subparsers(dest="release_cmd", required=True)
    sp = release.add_parser("list")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("--limit", type=int, default=50); sp.set_defaults(func=cmd_release_list)
    sp = release.add_parser("create")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("--tag", required=True); sp.add_argument("--name"); sp.add_argument("--body"); sp.add_argument("--target"); sp.add_argument("--draft", action="store_true"); sp.add_argument("--prerelease", action="store_true"); sp.set_defaults(func=cmd_release_create)
    sp = release.add_parser("delete")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("release_id"); sp.add_argument("--confirm"); sp.set_defaults(func=cmd_release_delete)

    wiki = sub.add_parser("wiki").add_subparsers(dest="wiki_cmd", required=True)
    sp = wiki.add_parser("list")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("--limit", type=int, default=50); sp.set_defaults(func=cmd_wiki_list)
    sp = wiki.add_parser("get")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("page"); sp.set_defaults(func=cmd_wiki_get)
    sp = wiki.add_parser("create")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("--file", required=True); sp.add_argument("--title", required=True); sp.add_argument("--message"); sp.set_defaults(func=cmd_wiki_create)
    sp = wiki.add_parser("edit")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("page"); sp.add_argument("--file", required=True); sp.add_argument("--title"); sp.add_argument("--message"); sp.set_defaults(func=cmd_wiki_edit)
    sp = wiki.add_parser("delete")
    sp.add_argument("owner"); sp.add_argument("repo"); sp.add_argument("page"); sp.add_argument("--confirm"); sp.set_defaults(func=cmd_wiki_delete)

    package = sub.add_parser("package").add_subparsers(dest="package_cmd", required=True)
    sp = package.add_parser("list")
    sp.add_argument("owner"); sp.add_argument("--type"); sp.add_argument("--q"); sp.add_argument("--limit", type=int, default=50); sp.set_defaults(func=cmd_package_list)
    sp = package.add_parser("versions")
    sp.add_argument("owner"); sp.add_argument("type"); sp.add_argument("name"); sp.add_argument("--limit", type=int, default=50); sp.set_defaults(func=cmd_package_versions)

    contents = sub.add_parser("contents").add_subparsers(dest="contents_cmd", required=True)
    sp = contents.add_parser("change")
    sp.add_argument("owner"); sp.add_argument("repo"); add_json_source_args(sp); sp.add_argument("--allow-force-push", action="store_true"); sp.set_defaults(func=cmd_contents_change)

    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    action = args.command
    try:
        client = build_client(args)
        return args.func(client, args)
    except GiteaError as exc:
        return emit_error(action, exc)
    except KeyboardInterrupt:
        return emit_error(action, GiteaError("E_INTERRUPTED", "Interrupted by user"))
    except Exception as exc:
        return emit_error(action, GiteaError("E_INTERNAL", f"Unexpected helper error: {type(exc).__name__}: {exc}"))


if __name__ == "__main__":
    raise SystemExit(main())
