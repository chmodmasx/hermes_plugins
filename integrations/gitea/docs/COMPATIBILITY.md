# Compatibility design notes

Research baseline: 2026-08-28.

## Hermes

The package uses the documented native plugin model: a directory under `~/.hermes/plugins/`, `plugin.yaml`, and `register(ctx)`. Tools are registered with `ctx.register_tool(name=..., toolset=..., schema=..., handler=...)`.

Handlers follow the current contract: `(args: dict, **kwargs) -> str`, always returning JSON and catching errors. `register(ctx)` performs no network calls, so `hermes plugins doctor --ci` can load/inspect it with socket access blocked.

The plugin intentionally omits `manifest_version`. Hermes documents that absent means manifest v1. This avoids a currently documented ecosystem inconsistency where the runtime loader understands manifest v2 while some current installers reject `manifest_version: 2`.

The skill is installed separately under `~/.hermes/skills/gitea-professional`. Plugin-bundled skills are valid but namespaced and not listed in the normal system skill index, which is undesirable for automatic routing here.

## Gitea

The target is Gitea `>=1.27.0,<1.28`, with 1.27.2 as the recommended baseline. The plugin performs live capability discovery through `/api/v1/version`, `/api/v1/settings/api`, and `/swagger.v1.json` instead of assuming every instance exposes an identical surface.

Authentication uses `Authorization: token <PAT>` internally. Credentials embedded in base URLs are rejected. HTTPS is mandatory by default; redirects are refused; custom CA bundles are supported; plain HTTP and insecure TLS require explicit opt-in.

GET/HEAD/OPTIONS may retry transient failures. Mutations do not retry automatically: an ambiguous POST timeout must be reconciled before any repeat.

## Safety boundary

The native plugin deliberately does not expose destructive/admin/secrets/runner-reset/merge operations. There is no generic arbitrary-write API tool. Code changes should use Git over SSH, not the repository Contents API.

## Gitea 1.27 OpenAPI contract notes

The wrapped mutations were checked against the official Gitea 1.27 OpenAPI contract. Three details are intentional:

- Pull-request review approval uses `APPROVED` (not GitHub-style `APPROVE`).
- Repository discovery uses `/repos/search` with the authenticated user ID because `/user/repos` only lists repositories owned by that user; search with `uid` covers repositories the bot owns or contributes to.
- `EditIssueOption` does not accept labels. Label replacement has a separate endpoint, so `gitea_issue_update` deliberately omits labels instead of hiding a second mutation behind one tool call.

The live instance remains authoritative. `gitea_connection_status` and `gitea_openapi_search` inspect the server at runtime without exposing a generic write primitive.

### Actions endpoint details verified against 1.27.2

- Repository workflow runs use `/repos/{owner}/{repo}/actions/runs`; `workflow_id` is **not** a query parameter there. When a workflow file is specified, the plugin switches to `/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs`.
- Run filters include `event`, `branch`, `status`, `actor`, `head_sha`, `exclude_pull_requests`, `page`, and `limit`.
- Run jobs support `status`, `page`, `limit`, `sort=id`, and `order=asc|desc`.
- Run artifacts support an optional `name` filter.
- Repository-scoped runners support an optional `disabled` filter; `page` and `limit` are not valid query parameters for that endpoint in 1.27.2.
