# Issues, Labels, Milestones, Pull Requests, Reviews, and Merge Safety

## Issues

The issue API covers substantially more than title/body/state. Current Gitea exposes operations for:

- create/get/edit/delete issues;
- repository/global issue search;
- assignees;
- comments and attachments;
- labels and milestones;
- dependencies/blocking relationships;
- pin/unpin and lock/unlock;
- reactions;
- deadlines;
- subscriptions;
- time tracking/stopwatch;
- timeline/events.

Use `schema --search` for exact payloads instead of guessing field names for less common operations.

### Labels and milestones

Labels and milestones are under the issue permission family. Before creating a label/milestone for automation, search existing resources first to avoid duplicates by spelling/case conventions.

When attaching labels to issues, distinguish label IDs from names. The issue-create API commonly expects label IDs. Resolve names to IDs before mutation.

### Issue deletion

Current Gitea exposes issue deletion. Treat it as destructive and require exact user authorization. Closing is often semantically preferable to deletion; do not substitute one for the other without user intent.

## Pull requests

High-value operations include:

- list/get/create/edit PR;
- commits/files/diff/patch;
- reviewers/team reviewers;
- reviews and inline review comments;
- mergeability/merge operation;
- commit status/check information;
- branch protection on the base branch.

PRs are repository-scope operations even though their conversation/comments share issue concepts.

## Review discipline

A review must be tied to a concrete revision. Before approving/requesting changes:

1. GET the PR.
2. Capture `head.sha`.
3. Inspect files/commits/diff as required by the request.
4. Submit the review with that commit ID when supported.
5. If a new push occurs, treat the previous analysis as stale for merge purposes.

Allowed review event names vary by schema/version; current flows commonly include `APPROVED`, `REQUEST_CHANGES`, and `COMMENT`. Confirm with live schema if the server rejects a value.

## Merge discipline and TOCTOU defense

Never implement merge as “CI looks good -> merge branch.” Use an exact expected SHA:

1. Read PR and capture exact `head.sha`.
2. Read base-branch protection and required checks.
3. Query statuses/check state for that same SHA.
4. Perform review against that SHA when required.
5. Re-read PR immediately before merge.
6. Abort if head SHA changed.
7. Merge using `head_commit_id=<captured SHA>` and `force_merge=false`.
8. Re-read PR and require `merged=true`.

The helper's `pr merge` implements the SHA check and sends `head_commit_id`. It blocks non-green combined status by default.

Exact confirmation format:

`MERGE:OWNER/REPO#NUMBER@SHA`

Only provide it after the user has explicitly asked for the merge and the PR was re-read.

## CI interpretation

Do not infer CI health from a single workflow name, logs, or branch badge. Prefer the combined commit status and individual contexts for the exact head SHA. If branch protection requires named contexts, all required contexts must be successful for the current SHA.

If the repository has intentionally no CI, the helper's default green-status gate can be overridden only with explicit user authorization using `--allow-non-green`; server-side protection still remains authoritative.

## Merge methods

Gitea can expose merge, squash, rebase, and related strategies depending on repo/version settings. Do not choose a different strategy merely because the requested one is disabled. Report the policy/configuration conflict.

Never set `force_merge=true` as an automatic fallback.

## Postconditions

- issue create/edit -> GET issue and verify requested fields.
- comment create -> capture comment ID/body.
- labels/milestone changes -> re-read effective issue metadata.
- PR create -> re-read PR and head/base.
- review -> capture review ID and reviewed head SHA.
- merge -> `merged=true`, unchanged expected head at decision time, merge commit SHA when available.

## Source links

- https://docs.gitea.com/api/
- https://docs.gitea.com/api/operations/issue-create-issue/
- https://docs.gitea.com/api/operations/repo-create-pull-request/
- https://docs.gitea.com/api/operations/repo-create-pull-review/
- https://docs.gitea.com/api/operations/repo-merge-pull-request/
- https://docs.gitea.com/api/operations/repo-get-combined-status-by-ref/
- https://docs.gitea.com/usage/access-control/protected-branches/
