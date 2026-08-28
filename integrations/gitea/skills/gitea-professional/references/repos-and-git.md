# Repositories, Git Transport, Branches, Tags, and Contents

## Interface selection

Use REST for repository metadata and platform operations. Use `git` for actual working-tree/history workflows.

REST is appropriate for:

- create/edit/delete/migrate/fork repositories;
- collaborators, deploy keys, topics, mirrors, templates;
- branch/tag metadata;
- small file or multi-file content commits;
- branch protection and repository settings;
- commit/status inspection.

Git is appropriate for:

- clone/fetch/pull;
- checkout/switch;
- diff/status/log/blame;
- merge/rebase/cherry-pick/revert;
- commit creation/signing;
- complex multi-file changes;
- push and ref transport.

## High-value repository endpoints

- `GET /repos/{owner}/{repo}` — repository.
- `PATCH /repos/{owner}/{repo}` — edit repository properties.
- `DELETE /repos/{owner}/{repo}` — destructive; explicit confirmation required.
- `POST /user/repos` — create repo for current user.
- `POST /orgs/{org}/repos` — create repo in org.
- `POST /repos/{owner}/{repo}/forks` — fork.
- repository migration endpoints — discover exact version schema with `schema --search migrate`.
- collaborators/permissions — discover with `schema --search collaborator`.

Do not silently change visibility, default branch, merge policy, archived state, Actions/Wiki/Issues availability, or external tracker/wiki configuration as a side effect of another task.

## Branches and refs

- `GET /repos/{owner}/{repo}/branches`
- `GET /repos/{owner}/{repo}/branches/{branch}`
- `POST /repos/{owner}/{repo}/branches`
- `DELETE /repos/{owner}/{repo}/branches/{branch}`
- `GET /repos/{owner}/{repo}/git/refs` for lower-level refs.

Branch creation supports `new_branch_name` and a source ref such as `old_ref_name`; the older `old_branch_name` field is deprecated in current docs.

Before deleting a branch, check whether it is default, protected, referenced by an open PR, or expected by deployment/CI. Never infer that a merged branch is safe to delete when another workflow may still depend on it.

## Tags

- list/create/delete tags through `/repos/{owner}/{repo}/tags...`.
- Distinguish lightweight/annotated tag semantics if the API version exposes options differently.
- Never move an existing release tag silently. A tag rewrite is a history/reference change and requires explicit authorization.

## Commits and status

Use commit SHA as the stable identity for review/CI decisions. Branch names move.

Useful operations include:

- get/list commits;
- compare refs;
- get diff/patch;
- get commit statuses and combined status;
- signing/verification information where available.

For any decision tied to CI, fetch status for the exact SHA rather than interpreting a workflow name or branch state.

## Contents API

Gitea supports individual file APIs and a multi-file change endpoint:

`POST /repos/{owner}/{repo}/contents`

Current multi-file operations can include create/update/upload/rename/delete-style file changes depending on the schema. Payloads can include branch, new branch, commit message, author/committer, signoff, and force-push behavior.

Rules:

- Use `contents change ... --json-file plan.json` for deterministic small batches.
- Keep `force_push` false by default. The helper refuses `force_push=true` without `--allow-force-push`.
- For updates/deletes, supply the expected file SHA when the endpoint requires it; this gives concurrency protection.
- Prefer a new branch + PR when the change is substantive or reviewable.

## Git push discipline

Before push:

1. Fetch the remote.
2. Inspect `git status` and the exact branch/upstream.
3. Compare local base and remote head.
4. Ensure every changed file is intended.
5. Check branch protection/required PR workflow if pushing to a protected/default branch.

Never use a PAT embedded in an HTTPS URL. Prefer SSH when configured. If HTTPS credentials are needed, use a credential helper or secure prompt mechanism rather than writing secrets into `.git/config`.

For an explicitly authorized history rewrite, use `--force-with-lease` instead of `--force`, and only after recording the expected remote SHA. Re-fetch and verify after push.

## Protected branches

Branch protection can require:

- specific users/teams for push or merge;
- approvals/reviews;
- status checks;
- branch freshness/up-to-date state;
- signed commits;
- blocked force push;
- administrators to obey the rule.

Do not bypass these controls. If an API call returns forbidden/conflict despite write permission, inspect protection rather than escalating privileges.

## Postconditions

- repo create/edit -> re-read repository fields.
- branch create -> re-read branch and commit SHA.
- branch/tag delete -> confirm not found.
- contents change -> verify commit SHA and changed paths; for critical content, re-read content or fetch via Git.
- push -> fetch remote and compare resulting SHA.

## Source links

- https://docs.gitea.com/api/
- https://docs.gitea.com/api/operations/repo-create-branch/
- https://docs.gitea.com/api/operations/repo-change-files/
- https://docs.gitea.com/api/operations/repo-list-all-git-refs/
- https://docs.gitea.com/usage/access-control/protected-branches/
