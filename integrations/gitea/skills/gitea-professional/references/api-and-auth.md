# Gitea API, Authentication, Permissions, and Compatibility

## Runtime contract

Treat the deployed instance as authoritative. Gitea exposes REST under `/api/v1` and normally serves its machine-readable API document at `/swagger.v1.json`. Run the helper's `version`, `capabilities`, and `schema` commands instead of assuming the instance exactly matches current public docs.

Current research baseline: Gitea API documentation 1.27.2, consulted 2026-08-27. Older instances can expose Swagger 2.0 while current public docs expose OpenAPI 3.0.3. Code must tolerate schema-version differences.

## Authentication methods

Preferred for a dedicated Hermes integration:

1. Dedicated Gitea bot/service user.
2. Personal access token (PAT) scoped to the minimum API families required.
3. Repository/org/team ACLs limited to the required resources.
4. Branch protection as a separate enforcement layer.

REST token header:

`Authorization: token <PAT>`

OAuth access tokens may use Bearer authorization. Gitea OAuth2 supports Authorization Code and PKCE/OIDC capabilities; use a plugin/setup flow if interactive delegation is actually required. Do not make a user-local skill persist OAuth refresh tokens in SKILL.md or config text.

Never use token/access_token query parameters in new automation. Never embed PATs in Git remote URLs or command output.

## Scope families

Gitea PAT/OAuth scopes are high-level API families. Relevant examples include:

- `read:repository` / `write:repository`
- `read:issue` / `write:issue`
- `read:organization` / `write:organization`
- `read:user` / `write:user`
- `read:package` / `write:package`
- `read:notification` / `write:notification`
- `read:misc` / `write:misc`
- administrative scope families when explicitly needed

A write scope generally includes read access in the same family, but the scope alone is never sufficient. Effective authorization is the intersection of token scope, user/bot ACL, repo unit permissions, org/team permissions, branch protection, and instance policy.

## Permissions model

Repositories can expose separate units such as Code, Issues, Pull Requests, Releases, Wiki, Packages, Actions, Projects, and Settings. Read/write/admin on one unit does not imply unrestricted access to every unit.

Organizations should normally grant access through teams instead of large numbers of individual collaborators. Before changing permissions, read the current org/team/repo relationship and show the intended delta.

## Pagination

When completeness matters, paginate until the API indicates no next page. Gitea uses `page` and `limit`, may return `Link` relations, and may return `X-Total-Count`. Instance configuration controls page-size limits; never assume 30 or 50 is globally complete.

The bundled client:

- requests explicit pages;
- follows next-page information when present;
- stops only at a short final page or explicit exhaustion;
- exposes page count and `total_count` when available.

## Error interpretation

- 400: malformed request; inspect live schema.
- 401: missing/invalid/expired credential.
- 403: scope/ACL/policy refusal; do not privilege-escalate automatically.
- 404: wrong identifier, hidden private resource, disabled unit, or absent resource.
- 409: conflict/current state incompatible with request.
- 412: precondition failure; re-read state.
- 422: validation error; version/schema mismatch is common.
- 423: resource locked/archived or otherwise unavailable for mutation.
- 429: deployment/proxy rate limit; respect `Retry-After` when present.
- 5xx/transport: transient possibility; safe reads can retry.

No universal Gitea-wide requests-per-minute quota should be hard-coded. Reverse proxies or hosting layers can impose their own limits.

## Mutation retry policy

Never blind-retry a mutation after timeout or connection loss. The server may have committed the change and only the response was lost.

Reconcile by natural identity before retrying:

- repo create -> GET `/repos/{owner}/{repo}`
- branch create -> GET branch by name
- tag create -> GET/list tag
- collaborator/team change -> read effective permission/membership
- merge -> re-read PR and exact head SHA
- release create -> search by tag/name
- Actions dispatch -> inspect returned run details when available; if response was lost, correlate by workflow/ref/time rather than dispatching blindly

Issue/comment creation is not naturally idempotent. If the response is ambiguous, search recent items carefully before deciding whether to retry.

## Live schema discovery

Use:

`python ${HERMES_SKILL_DIR}/scripts/gitea.py --base-url URL schema --search 'phrase'`

Optional filters:

- `--method GET|POST|PUT|PATCH|DELETE`
- `--tag repository|issue|organization|package|admin|...`

The helper returns path, method, operation ID, summary, tags, parameters, and request-body schema when present. For uncommon or version-specific endpoints, this is preferred over remembering a public-doc path from training data.

## GraphQL

Do not use a GitHub-style GraphQL endpoint. Gitea currently does not expose a supported native GraphQL API. If an external gateway supplies GraphQL, treat it as a separate product/integration and do not infer that Gitea semantics apply.

## Source links

- https://docs.gitea.com/api/
- https://docs.gitea.com/development/api-usage/
- https://docs.gitea.com/development/oauth2-provider/
- https://docs.gitea.com/usage/access-control/permissions/
- https://docs.gitea.com/usage/access-control/protected-branches/
- https://docs.gitea.com/help/faq/
