"""Tool schemas exposed to Hermes. Keep names/descriptions stable and semantic."""
from __future__ import annotations

from typing import Any

OWNER = {"type": "string", "description": "Gitea repository owner or organization."}
REPO = {"type": "string", "description": "Gitea repository name."}
INDEX = {"type": "integer", "minimum": 1, "description": "Issue or pull request number."}
RUN_ID = {"type": "integer", "minimum": 1, "description": "Gitea Actions run ID."}
LIMIT = {"type": "integer", "minimum": 1, "maximum": 50, "default": 30, "description": "Items per API page (1-50)."}
MAX_PAGES = {"type": "integer", "minimum": 1, "maximum": 50, "default": 10, "description": "Maximum pages to retrieve."}


def schema(name: str, description: str, properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties or {},
            "required": required or [],
            "additionalProperties": False,
        },
    }


SCHEMAS: dict[str, dict[str, Any]] = {}

def add(name: str, description: str, properties: dict[str, Any] | None = None, required: list[str] | None = None) -> None:
    SCHEMAS[name] = schema(name, description, properties, required)


# Read/control-plane tools
add("gitea_connection_status", "Check the configured Gitea connection, authenticated bot identity, server version, API settings, TLS posture, and live OpenAPI capabilities. Use before writes on a new or changed instance.")
add("gitea_repos_list", "List repositories the authenticated Gitea bot owns or contributes to, including private repositories it can access, using Gitea repository search.", {"limit": LIMIT, "max_pages": MAX_PAGES})
add("gitea_repo_get", "Get repository metadata and clone URLs. Prefer the SSH clone URL for Git working-tree operations.", {"owner": OWNER, "repo": REPO}, ["owner", "repo"])
add("gitea_contents_list", "Read repository content metadata for a file or directory at an optional ref. Does not modify repository contents.", {"owner": OWNER, "repo": REPO, "path": {"type": "string", "description": "Relative repository path; empty means root."}, "ref": {"type": "string", "description": "Branch, tag, or commit SHA."}}, ["owner", "repo"])
add("gitea_file_get", "Read and decode a text file from a Gitea repository at an optional ref. Output is size-capped; use Git for large/binary files.", {"owner": OWNER, "repo": REPO, "path": {"type": "string", "description": "Relative file path."}, "ref": {"type": "string", "description": "Branch, tag, or commit SHA."}, "max_chars": {"type": "integer", "minimum": 1000, "maximum": 500000, "default": 120000}}, ["owner", "repo", "path"])
add("gitea_branches_list", "List branches for a Gitea repository.", {"owner": OWNER, "repo": REPO, "limit": LIMIT, "max_pages": MAX_PAGES}, ["owner", "repo"])
add("gitea_commits_list", "List commits for a repository, optionally constrained to a ref/path.", {"owner": OWNER, "repo": REPO, "sha": {"type": "string", "description": "Branch, tag, or SHA to start from."}, "path": {"type": "string", "description": "Optional repository path filter."}, "limit": LIMIT, "max_pages": MAX_PAGES}, ["owner", "repo"])
add("gitea_commit_status", "Get the combined commit status for a branch, tag, or commit SHA. Use before considering a merge or release.", {"owner": OWNER, "repo": REPO, "ref": {"type": "string", "description": "Commit SHA, branch, or tag."}}, ["owner", "repo", "ref"])
add("gitea_issues_list", "List repository issues with optional state/labels/query filters.", {"owner": OWNER, "repo": REPO, "state": {"type": "string", "enum": ["open", "closed", "all"]}, "labels": {"type": "string", "description": "Comma-separated label names/IDs accepted by Gitea."}, "q": {"type": "string", "description": "Search text."}, "limit": LIMIT, "max_pages": MAX_PAGES}, ["owner", "repo"])
add("gitea_issue_get", "Get one Gitea issue by number.", {"owner": OWNER, "repo": REPO, "index": INDEX}, ["owner", "repo", "index"])
add("gitea_prs_list", "List pull requests for a repository with an optional state filter.", {"owner": OWNER, "repo": REPO, "state": {"type": "string", "enum": ["open", "closed", "all"]}, "limit": LIMIT, "max_pages": MAX_PAGES}, ["owner", "repo"])
add("gitea_pr_get", "Get one pull request including current head/base metadata. Re-read immediately before any review or other stateful action.", {"owner": OWNER, "repo": REPO, "index": INDEX}, ["owner", "repo", "index"])
add("gitea_pr_files", "List files changed by a pull request.", {"owner": OWNER, "repo": REPO, "index": INDEX, "limit": LIMIT, "max_pages": MAX_PAGES}, ["owner", "repo", "index"])
add("gitea_pr_commits", "List commits in a pull request.", {"owner": OWNER, "repo": REPO, "index": INDEX, "limit": LIMIT, "max_pages": MAX_PAGES}, ["owner", "repo", "index"])
add("gitea_pr_reviews", "List reviews for a pull request.", {"owner": OWNER, "repo": REPO, "index": INDEX, "limit": LIMIT, "max_pages": MAX_PAGES}, ["owner", "repo", "index"])
add("gitea_actions_runs", "List Gitea Actions workflow runs. If workflow_id is supplied, use Gitea's workflow-specific endpoint instead of treating it as a repository-run query parameter.", {"owner": OWNER, "repo": REPO, "status": {"type": "string", "enum": ["pending", "queued", "in_progress", "failure", "success", "skipped"]}, "event": {"type": "string"}, "branch": {"type": "string"}, "actor": {"type": "string"}, "head_sha": {"type": "string"}, "exclude_pull_requests": {"type": "boolean"}, "workflow_id": {"type": "string", "description": "Workflow file name accepted by Gitea, for example build.yml."}, "limit": LIMIT, "page": {"type": "integer", "minimum": 1, "default": 1}}, ["owner", "repo"])
add("gitea_actions_run", "Get one Gitea Actions workflow run by ID.", {"owner": OWNER, "repo": REPO, "run_id": RUN_ID}, ["owner", "repo", "run_id"])
add("gitea_actions_jobs", "Get jobs for a Gitea Actions workflow run with Gitea 1.27 status/paging/sort filters.", {"owner": OWNER, "repo": REPO, "run_id": RUN_ID, "status": {"type": "string", "enum": ["pending", "queued", "in_progress", "failure", "success", "skipped"]}, "page": {"type": "integer", "minimum": 1, "default": 1}, "limit": LIMIT, "sort": {"type": "string", "enum": ["id"], "default": "id"}, "order": {"type": "string", "enum": ["asc", "desc"], "default": "asc"}}, ["owner", "repo", "run_id"])
add("gitea_actions_job_logs", "Read size-capped logs for a Gitea Actions job. Use for failure diagnosis; secrets must never be echoed back if present in logs.", {"owner": OWNER, "repo": REPO, "job_id": {"type": "integer", "minimum": 1}, "max_chars": {"type": "integer", "minimum": 1000, "maximum": 500000, "default": 120000}}, ["owner", "repo", "job_id"])
add("gitea_actions_artifacts", "List artifacts for a Gitea Actions workflow run, optionally filtering by exact artifact name.", {"owner": OWNER, "repo": REPO, "run_id": RUN_ID, "name": {"type": "string"}}, ["owner", "repo", "run_id"])
add("gitea_runners_list", "List repository-scoped Gitea Actions runners and their status/labels. Gitea 1.27 exposes only a disabled=true/false query filter here; registration tokens are intentionally not exposed.", {"owner": OWNER, "repo": REPO, "disabled": {"type": "boolean"}}, ["owner", "repo"])
add("gitea_releases_list", "List releases for a repository.", {"owner": OWNER, "repo": REPO, "limit": LIMIT, "max_pages": MAX_PAGES}, ["owner", "repo"])
add("gitea_webhooks_list", "List repository webhooks without creating, editing, deleting, or testing them.", {"owner": OWNER, "repo": REPO, "limit": LIMIT, "max_pages": MAX_PAGES}, ["owner", "repo"])
add("gitea_openapi_search", "Search the live Gitea swagger.v1.json for endpoints/capabilities not wrapped by this plugin. This is read-only discovery, not a generic arbitrary API executor.", {"term": {"type": "string", "description": "Search term across path, operation ID, summary and tags."}, "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]}, "tag": {"type": "string"}, "max_results": {"type": "integer", "minimum": 1, "maximum": 100, "default": 30}}, ["term"])

# Mutations intentionally exclude delete/admin/secrets/runner-reset/merge.
add("gitea_branch_create", "Create a branch from an optional existing branch/tag/SHA. Idempotently returns an existing branch instead of overwriting it.", {"owner": OWNER, "repo": REPO, "name": {"type": "string"}, "old_ref": {"type": "string", "description": "Optional source branch/tag/SHA."}}, ["owner", "repo", "name"])
add("gitea_issue_create", "Create a repository issue. Use only when the user requested or clearly authorized issue creation.", {"owner": OWNER, "repo": REPO, "title": {"type": "string", "maxLength": 255}, "body": {"type": "string"}, "labels": {"type": "array", "items": {"type": "integer", "minimum": 1}}, "assignees": {"type": "array", "items": {"type": "string"}}, "milestone": {"type": "integer", "minimum": 0}}, ["owner", "repo", "title"])
add("gitea_issue_update", "Update issue title/body/state/assignees/milestone. Only supplied fields are sent. Label replacement uses a separate Gitea endpoint and is intentionally not exposed in v1.", {"owner": OWNER, "repo": REPO, "index": INDEX, "title": {"type": "string", "maxLength": 255}, "body": {"type": "string"}, "state": {"type": "string", "enum": ["open", "closed"]}, "assignees": {"type": "array", "items": {"type": "string"}}, "milestone": {"type": "integer", "minimum": 0}}, ["owner", "repo", "index"])
add("gitea_issue_comment", "Add a comment to an issue or pull request conversation through the Gitea issue comments API.", {"owner": OWNER, "repo": REPO, "index": INDEX, "body": {"type": "string", "minLength": 1}}, ["owner", "repo", "index", "body"])
add("gitea_pr_create", "Create a pull request from an already-pushed branch. Use Git/SSH for working-tree changes, commits, and pushes; do not use the REST contents API as a Git replacement.", {"owner": OWNER, "repo": REPO, "head": {"type": "string"}, "base": {"type": "string"}, "title": {"type": "string", "maxLength": 255}, "body": {"type": "string"}, "reviewers": {"type": "array", "items": {"type": "string"}}, "assignees": {"type": "array", "items": {"type": "string"}}, "labels": {"type": "array", "items": {"type": "integer", "minimum": 1}}}, ["owner", "repo", "head", "base", "title"])
add("gitea_pr_review", "Submit a review against the pull request's current head SHA. If expected_head_sha is supplied and the PR changed, the tool refuses with a stale-head error.", {"owner": OWNER, "repo": REPO, "index": INDEX, "event": {"type": "string", "enum": ["APPROVED", "REQUEST_CHANGES", "COMMENT"]}, "body": {"type": "string"}, "expected_head_sha": {"type": "string"}}, ["owner", "repo", "index", "event"])
add("gitea_actions_dispatch", "Dispatch a Gitea Actions workflow on an explicit ref. Inputs are ordinary strings; do not pass secrets in tool arguments—use Gitea Actions secrets instead.", {"owner": OWNER, "repo": REPO, "workflow": {"type": "string", "description": "Workflow ID or filename accepted by Gitea."}, "ref": {"type": "string"}, "inputs": {"type": "object", "additionalProperties": {"type": "string"}}}, ["owner", "repo", "workflow", "ref"])
add("gitea_actions_rerun", "Rerun an existing Gitea Actions workflow run once. Never blind-retry this tool after an ambiguous timeout; reconcile run state first.", {"owner": OWNER, "repo": REPO, "run_id": RUN_ID}, ["owner", "repo", "run_id"])
add("gitea_release_create", "Create a Gitea release for an existing or target tag. Use only after verifying the intended ref/status and user intent.", {"owner": OWNER, "repo": REPO, "tag": {"type": "string"}, "name": {"type": "string"}, "body": {"type": "string"}, "target": {"type": "string"}, "draft": {"type": "boolean", "default": False}, "prerelease": {"type": "boolean", "default": False}}, ["owner", "repo", "tag"])

READ_TOOLS = {
    name for name in SCHEMAS
    if name not in {
        "gitea_branch_create", "gitea_issue_create", "gitea_issue_update", "gitea_issue_comment",
        "gitea_pr_create", "gitea_pr_review", "gitea_actions_dispatch", "gitea_actions_rerun", "gitea_release_create",
    }
}
WRITE_TOOLS = set(SCHEMAS) - READ_TOOLS
