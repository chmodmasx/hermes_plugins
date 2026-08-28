"""Gitea tool handlers. Every handler accepts (args, **kwargs), catches errors, and returns JSON."""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any, Callable

from .client import GiteaClient, GiteaError
from . import policy

logger = logging.getLogger(__name__)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _error(exc: Exception) -> str:
    if isinstance(exc, GiteaError):
        payload: dict[str, Any] = {
            "ok": False,
            "error": {"code": exc.code, "message": exc.message, "retryable": exc.retryable},
        }
        if exc.status is not None:
            payload["error"]["status"] = exc.status
        if exc.details is not None:
            payload["error"]["details"] = exc.details
        return _json(payload)
    logger.exception("Unhandled Gitea plugin tool error")
    return _json({"ok": False, "error": {"code": "E_INTERNAL", "message": str(exc), "retryable": False}})


def _run(operation: str, args: dict[str, Any], fn: Callable[[GiteaClient], Any]) -> str:
    try:
        client = GiteaClient.from_environment(**policy.client_kwargs())
        data = fn(client)
        logger.info("gitea operation=%s ok=true", operation)
        return _json({"ok": True, "operation": operation, "data": data})
    except Exception as exc:  # handler contract: never raise
        logger.warning("gitea operation=%s ok=false type=%s", operation, type(exc).__name__)
        return _error(exc)


def _owner_repo(args: dict[str, Any]) -> tuple[str, str, str]:
    owner = policy.require_string(args, "owner", max_len=255)
    repo = policy.require_string(args, "repo", max_len=255)
    return owner, repo, policy.repo_path(owner, repo)


def _paginate(client: GiteaClient, path: str, args: dict[str, Any], query: dict[str, Any] | None = None) -> dict[str, Any]:
    limit, max_pages = policy.page_limit(args)
    return client.paginate(path, query=query, limit=limit, max_pages=max_pages)


def _query_nonempty(args: dict[str, Any], *names: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in names:
        value = args.get(name)
        if value is not None and value != "":
            out[name] = value
    return out


def _strip_content_metadata(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip_content_metadata(v) for v in value]
    if isinstance(value, dict):
        return {k: _strip_content_metadata(v) for k, v in value.items() if k != "content"}
    return value


def _sanitize_log(text: str, client: GiteaClient) -> str:
    if client.token:
        text = text.replace(client.token, "<redacted-api-token>")
    # Conservative common assignment/header redaction. Gitea also masks configured Actions secrets.
    patterns = [
        r"(?i)(authorization\s*:\s*(?:token|bearer)\s+)([^\s]+)",
        r"(?i)((?:password|passwd|token|secret|api[_-]?key|access[_-]?key)\s*[=:]\s*)([^\s'\"]+)",
    ]
    for pat in patterns:
        text = re.sub(pat, r"\1<redacted>", text)
    return text


def gitea_connection_status(args: dict, **kwargs) -> str:
    def work(c: GiteaClient) -> Any:
        version = c.server_version()
        user = c.whoami()
        api_settings = None
        try:
            api_settings = c.get("/settings/api")
        except GiteaError as exc:
            api_settings = {"unavailable": True, "code": exc.code, "status": exc.status}
        capabilities = c.capability_summary()
        username = None
        user_id = None
        if isinstance(user, dict):
            username = user.get("login") or user.get("username")
            user_id = user.get("id")
        safe_settings = {}
        if isinstance(api_settings, dict):
            for key in ("max_response_items", "default_paging_num", "default_git_trees_per_page", "default_max_blob_size"):
                if key in api_settings:
                    safe_settings[key] = api_settings[key]
            if api_settings.get("unavailable"):
                safe_settings = api_settings
        return {
            "plugin_version": policy.PLUGIN_VERSION,
            "target_gitea": policy.TARGET_GITEA,
            "base_url": c.base_url,
            "authenticated": True,
            "account": {"id": user_id, "username": username},
            "server_version": version,
            "api_settings": safe_settings,
            "capabilities": capabilities,
            "security": {
                "https": c.base_url.lower().startswith("https://"),
                "allow_http": policy.bool_env("GITEA_ALLOW_HTTP"),
                "insecure_tls": policy.bool_env("GITEA_INSECURE_TLS"),
                "custom_ca_bundle": bool(os.environ.get("GITEA_CA_BUNDLE")),
                "redirects_refused": True,
                "token_source": "environment",
            },
        }
    return _run("connection.status", args, work)


def gitea_repos_list(args: dict, **kwargs) -> str:
    def work(c: GiteaClient) -> Any:
        user = c.whoami()
        uid = user.get("id") if isinstance(user, dict) else None
        if not isinstance(uid, int):
            raise GiteaError("E_SHAPE", "Authenticated Gitea user did not include an integer id")
        limit, max_pages = policy.page_limit(args)
        items: list[Any] = []
        pages = 0
        truncated = False
        for page in range(1, max_pages + 1):
            payload = c.get("/repos/search", query={"uid": uid, "private": "true", "page": page, "limit": limit})
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise GiteaError("E_SHAPE", "Gitea repository search returned an unexpected response")
            batch = payload["data"]
            items.extend(batch)
            pages = page
            if len(batch) < limit:
                break
        else:
            truncated = True
        return {
            "items": items,
            "pages_fetched": pages,
            "truncated": truncated,
            "scope": "owned_or_contributed",
            "authenticated_user_id": uid,
        }
    return _run("repos.list", args, work)


def gitea_repo_get(args: dict, **kwargs) -> str:
    owner, repo, rp = _owner_repo(args)
    return _run("repo.get", args, lambda c: c.get(rp))


def gitea_contents_list(args: dict, **kwargs) -> str:
    owner, repo, rp = _owner_repo(args)
    raw_path = str(args.get("path") or "")
    encoded = policy.content_path(raw_path)
    path = rp + "/contents" + ("/" + encoded if encoded else "")
    query = {"ref": args.get("ref")} if args.get("ref") else None
    return _run("contents.list", args, lambda c: _strip_content_metadata(c.get(path, query=query)))


def gitea_file_get(args: dict, **kwargs) -> str:
    owner, repo, rp = _owner_repo(args)
    raw_path = policy.require_string(args, "path", max_len=4096)
    encoded = policy.content_path(raw_path)
    path = rp + "/contents/" + encoded
    query = {"ref": args.get("ref")} if args.get("ref") else None
    try:
        max_chars = int(args.get("max_chars", policy.DEFAULT_MAX_FILE_CHARS))
    except (TypeError, ValueError):
        return _error(GiteaError("E_VALIDATION", "max_chars must be an integer"))
    max_chars = max(1000, min(500000, max_chars))

    def work(c: GiteaClient) -> Any:
        data = c.get(path, query=query)
        if not isinstance(data, dict) or data.get("type") not in {None, "file"}:
            raise GiteaError("E_SHAPE", "Requested path did not return a file object")
        encoded_content = data.get("content")
        if not isinstance(encoded_content, str):
            raise GiteaError("E_SHAPE", "Gitea did not return base64 file content")
        try:
            raw = base64.b64decode(encoded_content, validate=False)
        except Exception as exc:
            raise GiteaError("E_SHAPE", "Invalid base64 file content") from exc
        text = raw.decode("utf-8", errors="replace")
        truncated = len(text) > max_chars
        text = text[:max_chars]
        return {
            "path": data.get("path") or raw_path,
            "sha": data.get("sha"),
            "size": data.get("size", len(raw)),
            "encoding": "utf-8/replacement",
            "content": text,
            "truncated": truncated,
        }
    return _run("file.get", args, work)


def gitea_branches_list(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    return _run("branches.list", args, lambda c: _paginate(c, rp + "/branches", args))


def gitea_commits_list(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    query = _query_nonempty(args, "sha", "path")
    return _run("commits.list", args, lambda c: _paginate(c, rp + "/commits", args, query))


def gitea_commit_status(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    ref = policy.require_string(args, "ref", max_len=1024)
    path = rp + "/commits/" + policy.segment(ref) + "/status"
    return _run("commit.status", args, lambda c: c.get(path))


def gitea_issues_list(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    query = _query_nonempty(args, "state", "labels", "q")
    if query.get("state") == "all": query.pop("state")
    return _run("issues.list", args, lambda c: _paginate(c, rp + "/issues", args, query))


def gitea_issue_get(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    index = policy.require_int(args, "index")
    return _run("issue.get", args, lambda c: c.get(rp + f"/issues/{index}"))


def gitea_prs_list(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    query = _query_nonempty(args, "state")
    if query.get("state") == "all": query.pop("state")
    return _run("prs.list", args, lambda c: _paginate(c, rp + "/pulls", args, query))


def gitea_pr_get(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    index = policy.require_int(args, "index")
    return _run("pr.get", args, lambda c: c.get(rp + f"/pulls/{index}"))


def _pr_paginated(operation: str, suffix: str, args: dict) -> str:
    _, _, rp = _owner_repo(args)
    index = policy.require_int(args, "index")
    return _run(operation, args, lambda c: _paginate(c, rp + f"/pulls/{index}/{suffix}", args))


def gitea_pr_files(args: dict, **kwargs) -> str: return _pr_paginated("pr.files", "files", args)
def gitea_pr_commits(args: dict, **kwargs) -> str: return _pr_paginated("pr.commits", "commits", args)
def gitea_pr_reviews(args: dict, **kwargs) -> str: return _pr_paginated("pr.reviews", "reviews", args)


def gitea_actions_runs(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    workflow_id = policy.optional_string(args, "workflow_id", max_len=255)
    query = _query_nonempty(args, "status", "event", "branch", "actor", "head_sha")
    exclude_prs = policy.optional_bool(args, "exclude_pull_requests")
    if exclude_prs is not None:
        query["exclude_pull_requests"] = exclude_prs
    query["limit"] = policy.bounded_int(args, "limit", default=30, minimum=1, maximum=50)
    query["page"] = policy.bounded_int(args, "page", default=1, minimum=1, maximum=1_000_000)
    if workflow_id:
        path = rp + "/actions/workflows/" + policy.segment(workflow_id) + "/runs"
    else:
        path = rp + "/actions/runs"
    return _run("actions.runs", args, lambda c: c.get(path, query=query))


def gitea_actions_run(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args); run_id = policy.require_int(args, "run_id")
    return _run("actions.run", args, lambda c: c.get(rp + f"/actions/runs/{run_id}"))


def gitea_actions_jobs(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args); run_id = policy.require_int(args, "run_id")
    query = _query_nonempty(args, "status", "sort", "order")
    query["limit"] = policy.bounded_int(args, "limit", default=30, minimum=1, maximum=50)
    query["page"] = policy.bounded_int(args, "page", default=1, minimum=1, maximum=1_000_000)
    query.setdefault("sort", "id")
    query.setdefault("order", "asc")
    return _run("actions.jobs", args, lambda c: c.get(rp + f"/actions/runs/{run_id}/jobs", query=query))


def gitea_actions_job_logs(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args); job_id = policy.require_int(args, "job_id")
    try:
        max_chars = int(args.get("max_chars", policy.int_env("GITEA_MAX_LOG_CHARS", policy.DEFAULT_MAX_LOG_CHARS, minimum=1000, maximum=500000)))
    except (TypeError, ValueError):
        return _error(GiteaError("E_VALIDATION", "max_chars must be an integer"))
    max_chars = max(1000, min(500000, max_chars))
    def work(c: GiteaClient) -> Any:
        response = c.request("GET", rp + f"/actions/jobs/{job_id}/logs")
        text = response.data if isinstance(response.data, str) else _json(response.data)
        text = _sanitize_log(text, c)
        return {"job_id": job_id, "logs": text[:max_chars], "truncated": len(text) > max_chars}
    return _run("actions.job_logs", args, work)


def gitea_actions_artifacts(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args); run_id = policy.require_int(args, "run_id")
    name = policy.optional_string(args, "name", max_len=255)
    query = {"name": name} if name else None
    return _run("actions.artifacts", args, lambda c: c.get(rp + f"/actions/runs/{run_id}/artifacts", query=query))


def gitea_runners_list(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    disabled = policy.optional_bool(args, "disabled")
    query = {"disabled": disabled} if disabled is not None else None
    return _run("runners.list", args, lambda c: c.get(rp + "/actions/runners", query=query))


def gitea_releases_list(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    return _run("releases.list", args, lambda c: _paginate(c, rp + "/releases", args))


def gitea_webhooks_list(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    return _run("webhooks.list", args, lambda c: _paginate(c, rp + "/hooks", args))


def gitea_openapi_search(args: dict, **kwargs) -> str:
    term = policy.require_string(args, "term", max_len=200)
    method = args.get("method")
    tag = args.get("tag")
    try: max_results = int(args.get("max_results", 30))
    except (TypeError, ValueError): return _error(GiteaError("E_VALIDATION", "max_results must be an integer"))
    max_results = max(1, min(100, max_results))
    return _run("openapi.search", args, lambda c: c.search_swagger(term, method=method, tag=tag)[:max_results])


# Mutations

def gitea_branch_create(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    name = policy.require_string(args, "name", max_len=255)
    old_ref = policy.optional_string(args, "old_ref", max_len=1024)
    path = rp + "/branches/" + policy.segment(name)
    def work(c: GiteaClient) -> Any:
        existing = c.try_get(path)
        if existing is not None:
            return {"created": False, "branch": existing, "warning": "Branch already existed; no mutation performed."}
        body: dict[str, Any] = {"new_branch_name": name}
        if old_ref: body["old_ref_name"] = old_ref
        c.request("POST", rp + "/branches", body=body)
        return {"created": True, "branch": c.get(path)}
    return _run("branch.create", args, work)


def gitea_issue_create(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    title = policy.require_string(args, "title", max_len=255)
    body: dict[str, Any] = {"title": title}
    for name in ("body", "labels", "assignees", "milestone"):
        if name in args and args[name] is not None: body[name] = args[name]
    def work(c: GiteaClient) -> Any:
        response = c.request("POST", rp + "/issues", body=body).data
        index = response.get("number") if isinstance(response, dict) else None
        return c.get(rp + f"/issues/{index}") if index else response
    return _run("issue.create", args, work)


def gitea_issue_update(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args); index = policy.require_int(args, "index")
    body = {k: args[k] for k in ("title", "body", "state", "assignees", "milestone") if k in args}
    if not body: return _error(GiteaError("E_VALIDATION", "No issue fields supplied to update"))
    def work(c: GiteaClient) -> Any:
        c.request("PATCH", rp + f"/issues/{index}", body=body)
        return c.get(rp + f"/issues/{index}")
    return _run("issue.update", args, work)


def gitea_issue_comment(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args); index = policy.require_int(args, "index")
    body = policy.require_string(args, "body", max_len=100000)
    return _run("issue.comment", args, lambda c: c.request("POST", rp + f"/issues/{index}/comments", body={"body": body}).data)


def gitea_pr_create(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    body: dict[str, Any] = {
        "head": policy.require_string(args, "head", max_len=1024),
        "base": policy.require_string(args, "base", max_len=1024),
        "title": policy.require_string(args, "title", max_len=255),
    }
    for name in ("body", "reviewers", "assignees", "labels"):
        if name in args and args[name] is not None: body[name] = args[name]
    def work(c: GiteaClient) -> Any:
        response = c.request("POST", rp + "/pulls", body=body).data
        index = (response.get("number") or response.get("index")) if isinstance(response, dict) else None
        return c.get(rp + f"/pulls/{index}") if index else response
    return _run("pr.create", args, work)


def gitea_pr_review(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args); index = policy.require_int(args, "index")
    event = policy.require_string(args, "event", max_len=32)
    if event not in {"APPROVED", "REQUEST_CHANGES", "COMMENT"}:
        return _error(GiteaError("E_VALIDATION", "Invalid review event"))
    expected = policy.optional_string(args, "expected_head_sha", max_len=128)
    review_body = policy.optional_string(args, "body", max_len=100000) or ""
    def work(c: GiteaClient) -> Any:
        pr = c.get(rp + f"/pulls/{index}")
        current_sha = ((pr or {}).get("head") or {}).get("sha") if isinstance(pr, dict) else None
        if not current_sha: raise GiteaError("E_SHAPE", "Could not determine PR head SHA")
        if expected and expected != current_sha:
            raise GiteaError("E_STALE_HEAD", f"PR head changed: expected {expected}, current {current_sha}")
        response = c.request("POST", rp + f"/pulls/{index}/reviews", body={"event": event, "body": review_body, "commit_id": current_sha}).data
        return {"head_sha": current_sha, "review": response}
    return _run("pr.review", args, work)


def gitea_actions_dispatch(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    workflow = policy.require_string(args, "workflow", max_len=255)
    ref = policy.require_string(args, "ref", max_len=1024)
    inputs = args.get("inputs") or {}
    if not isinstance(inputs, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in inputs.items()):
        return _error(GiteaError("E_VALIDATION", "inputs must be an object of string values"))
    if any(re.search(r"(?i)(secret|token|password|api[_-]?key)", k) for k in inputs):
        return _error(GiteaError("E_POLICY", "Potential secret-like workflow inputs are forbidden in tool arguments; use Gitea Actions secrets"))
    path = rp + "/actions/workflows/" + policy.segment(workflow) + "/dispatches"
    return _run("actions.dispatch", args, lambda c: c.request("POST", path, query={"return_run_details": "true"}, body={"ref": ref, "inputs": inputs}).data)


def gitea_actions_rerun(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args); run_id = policy.require_int(args, "run_id")
    return _run("actions.rerun", args, lambda c: c.request("POST", rp + f"/actions/runs/{run_id}/rerun").data)


def gitea_release_create(args: dict, **kwargs) -> str:
    _, _, rp = _owner_repo(args)
    tag = policy.require_string(args, "tag", max_len=255)
    body: dict[str, Any] = {
        "tag_name": tag,
        "name": args.get("name") or tag,
        "body": args.get("body") or "",
        "draft": bool(args.get("draft", False)),
        "prerelease": bool(args.get("prerelease", False)),
    }
    if args.get("target"): body["target_commitish"] = args["target"]
    return _run("release.create", args, lambda c: c.request("POST", rp + "/releases", body=body).data)


def _safe_handler(fn):
    def wrapper(args: dict, **kwargs) -> str:
        try:
            return fn(args, **kwargs)
        except Exception as exc:
            return _error(exc)
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


HANDLERS = {
    name: _safe_handler(fn)
    for name, fn in list(globals().items())
    if name.startswith("gitea_") and callable(fn)
}
