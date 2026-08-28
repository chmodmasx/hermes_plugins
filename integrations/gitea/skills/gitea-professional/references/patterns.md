# Professional Operating Patterns

## Read → Decide → Write → Verify

Every consequential mutation follows four phases:

1. Read exact current state.
2. Decide using stable identifiers/SHAs and current policy.
3. Write once.
4. Verify observed postcondition.

This pattern is mandatory for merges, branch/tag deletion, permissions, branch protection, releases, webhooks, runner changes, and admin work.

## Idempotent create

Before creating a named resource, check whether it already exists when a safe read endpoint is available. If an equivalent resource exists, return its state rather than creating a duplicate unless the user explicitly wants another one.

## Ambiguous mutation reconciliation

If a mutation times out or the connection drops after the request may have reached Gitea:

1. do not repeat it immediately;
2. query the target resource or recent event/run list;
3. determine whether the intended state already exists;
4. retry only if the previous attempt is proven not to have taken effect.

## Stable SHA decisions

Use commit SHA, not branch name, for CI/review/merge decisions. Branch names move.

For PR merge, pin the reviewed head SHA and re-read immediately before merge.

## API versus Git

Use REST for platform state: repository settings, issues, PR metadata, reviews, releases, wiki, packages, hooks, Actions, runners, orgs/users/admin.

Use Git for repository content/history work: clone, fetch, checkout, diff, rebase, merge, cherry-pick, commit, push.

Use the contents API only for small deterministic changes where a checkout is unnecessary and the payload is fully understood.

## Least privilege

Prefer a dedicated bot/service user with the minimum PAT scopes plus minimum repository/org ACLs. Branch protection remains an independent enforcement layer.

Do not widen access as a convenience step.
