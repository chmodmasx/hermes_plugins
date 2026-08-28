---
name: gitea-professional
description: Operate Gitea 1.27 repositories, PRs and Actions.
version: 2.0.0
author: Hermes Gitea Integration
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [gitea, git, devops, code-review, actions, ci-cd, workflows, runners, security, self-hosted]
    category: devops
required_environment_variables:
  - name: GITEA_BASE_URL
    prompt: Canonical Gitea base URL
    help: Example https://git.example.com. Use the canonical non-redirecting URL.
    required_for: Native Gitea plugin and API helper operations
  - name: GITEA_TOKEN
    prompt: Gitea personal access token for the dedicated Hermes bot
    help: Use a least-privilege token; do not use an administrator token for routine work.
    required_for: Authenticated/private or mutating Gitea operations
---
# Gitea Professional — 1.27

Operate Gitea 1.27.x end to end: repositories, Git, issues, pull requests, releases, webhooks, Actions workflows/runs/runners, security and CI/CD troubleshooting.

This skill is the policy and knowledge layer for the `gitea-hermes` native plugin. Prefer typed `gitea_*` tools for Gitea control-plane work, normal `git` over SSH for working-tree/history operations, and bundled scripts only as a fallback or for advanced operations intentionally not exposed by the plugin.

Use progressive disclosure. Keep this file as policy/router and load only the smallest relevant file from `references/`.

## When to Use

Use for Gitea repositories, branches, contents, commits, issues, pull requests, reviews, releases, webhooks, Actions API, `.gitea/workflows`, GitHub→Gitea workflow migration, runners, CI/CD design, audit and debugging.

Do not use as authority for GitHub/GitLab-specific APIs or assume GitHub Actions parity.

## Prerequisites

- Native plugin `gitea-hermes` should provide `gitea_read` and `gitea_write` toolsets.
- `GITEA_BASE_URL` and `GITEA_TOKEN` must come from Hermes' secure environment setup, never from chat text.
- Use a dedicated least-privilege Gitea bot account. Baseline: **Gitea >=1.27.0,<1.28**, tested/recommended against **1.27.2**.
- Prefer HTTPS. Plain HTTP is only for explicitly trusted local-only deployments. Never disable TLS verification merely to silence certificate errors; use a custom CA bundle when appropriate.
- Prefer SSH for Git clone/fetch/push. Never put PATs in Git remote URLs.
- Establish exact Gitea Runner version when runner behavior is material.

## Interface Priority

1. **Native plugin tools (`gitea_*`)** for Gitea REST/control-plane operations.
2. **Normal `git` over SSH** for clone/history/working-tree/commit/push.
3. **Workflow files + scripts** for CI behavior and testing.
4. **Bundled Python CLI** only when a required operation is not exposed by the native plugin or for explicit advanced/high-risk work.
5. **Live `/swagger.v1.json` discovery** before inventing any unsupported endpoint.

The plugin deliberately does **not** expose delete/admin/secret-write/runner-reset/PR-merge tools in v1. Routine absence is a safety boundary, not a missing feature to bypass with arbitrary REST calls.

## Native Tool Map

| Goal | Preferred native path |
|---|---|
| Server/auth/capability preflight | `gitea_connection_status` |
| Accessible repos / repo metadata | `gitea_repos_list`, `gitea_repo_get` |
| Read file/directory | `gitea_file_get`, `gitea_contents_list` |
| Branches / commits / status | `gitea_branches_list`, `gitea_commits_list`, `gitea_commit_status` |
| Issues | `gitea_issues_list`, `gitea_issue_get`, create/update/comment tools |
| Pull requests | PR get/list/files/commits/reviews/create/review tools |
| Actions diagnosis | runs → run → jobs → job logs → artifacts |
| Workflow dispatch/rerun | `gitea_actions_dispatch`, `gitea_actions_rerun` |
| Runners | `gitea_runners_list` (read-only) |
| Releases | list/create tools |
| Hooks | `gitea_webhooks_list`; provision hooks only through explicit setup workflow |
| Unsupported read capability | `gitea_openapi_search` then use a supported interface; do not invent generic writes |
| Code changes | `git clone`/branch/edit/test/commit/push, then `gitea_pr_create` |

## Bundled Fallbacks

```text
python ${HERMES_SKILL_DIR}/scripts/gitea.py --base-url "$GITEA_BASE_URL" <command>
python ${HERMES_SKILL_DIR}/scripts/doctor.py --base-url "$GITEA_BASE_URL"
python ${HERMES_SKILL_DIR}/scripts/audit_workflow.py .gitea/workflows/ci.yml
```

Every helper emits one JSON object. Treat `"ok": false` as failure. High-risk CLI operations require exact confirmation strings and remain subject to this skill's safety policy.

## Reference Router

Load only the smallest relevant file with `skill_view("gitea-professional", "<path>")`.

### Gitea platform

- `references/hermes-integration.md` — native plugin/Git/webhook responsibility boundary.
- `references/compatibility.md` — 1.27 baseline and live capability discovery.
- `references/api-and-auth.md` — REST, PAT/OAuth, scopes, pagination, errors.
- `references/repos-and-git.md` — repos, branches, tags, contents, Git and protection.
- `references/issues-and-prs.md` — issues, reviews and PR merge discipline.
- `references/releases-wiki-packages.md` — releases/assets, wiki and packages.
- `references/webhooks.md` — hooks, HMAC and delivery semantics.
- `references/orgs-admin-security.md` — org/team/user permissions and privileged work.
- `references/administration.md` — instance-wide administration.
- `references/security.md` — global secrets, TLS, destructive operations and Git safety.
- `references/patterns.md` — read→decide→write→verify and idempotency.
- `references/troubleshooting.md` — generic REST/server failures.
- `references/endpoint-map.md` — high-value API endpoint map.
- `references/SOURCES.md` — platform primary sources.

### Gitea Actions

- `references/actions/overview.md` — Actions control-plane API, runs, dispatch, secrets/variables.
- `references/actions/workflows.md` — events, contexts, permissions, matrices, artifacts, caches.
- `references/actions/compatibility.md` — GitHub Actions migration traps.
- `references/actions/runners.md` — registration, labels, Docker/host modes, networking, cache, monitoring.
- `references/actions/security.md` — trust model, secrets, permissions, third-party actions, forks, privilege.
- `references/actions/troubleshooting.md` — workflow/runner root-cause runbook.
- `references/actions/patterns.md` — production CI/CD patterns and anti-patterns.
- `references/actions/sources.md` — Hermes/Gitea Actions/Runner primary sources.

## General Procedure

1. **Resolve target.** Establish instance, owner/org, repo, branch/ref, issue/PR/run and requested end state.
2. **Preflight.** On a new/changed instance call `gitea_connection_status`; use `doctor.py` only as fallback. Establish Runner version only when needed.
3. **Load minimal reference.** Open only the domain file required.
4. **Inspect first.** Read current state. For workflow tasks read every relevant workflow and referenced local script/action that can materially affect behavior.
5. **Choose interface.** Prefer native `gitea_*` tools for control-plane work, `git` over SSH for history/working tree, and workflow files/scripts for CI behavior. For an unwrapped capability search live OpenAPI first; do not bypass intentional safety omissions with arbitrary writes.
6. **Classify Actions assumptions.** Use `verified`, `gitea-specific`, `unsupported`, or `needs-runtime-test`; GitHub behavior is not proof.
7. **Mutate once.** Make the smallest requested change. Never blind-retry after an ambiguous mutation/dispatch timeout; reconcile state first.
8. **Verify.** Re-read the API resource, fetch the remote ref, run tests/auditor and/or execute a real Gitea run as appropriate.
9. **Report evidence.** State changed target, resulting SHA/IDs/run IDs and unresolved uncertainty. Never report secret values.

## Actions Rules

For workflow creation/modification:

1. Define trigger trust boundary, forks/untrusted contributors, required secrets and runner privilege.
2. Read all interacting workflows plus referenced `run:` scripts and local `uses: ./...` actions.
3. Use the smallest `on:` event set and an explicit job DAG.
4. Map every `runs-on` requirement to a real runner label/trust class.
5. Declare `permissions:` minimally; expose secrets only to trusted jobs/steps.
6. Prefer immutable SHA/tag identities and pin third-party executable dependencies for production.
7. Keep YAML orchestration-focused; put substantial logic in versioned scripts.
8. Audit with `audit_workflow.py`; resolve or explain relevant findings.
9. Test exact-version semantics locally/server-side when material.

For GitHub Actions migration, load `references/actions/compatibility.md`, inventory events/expressions/permissions/environments/concurrency/runners/reusable workflows/actions/cache/artifacts/publishing/PR refs/OIDC/GitHub APIs, classify each advanced feature, and never silently drop behavior.

For Runner work, load `references/actions/runners.md` and establish scope, trust level, execution mode, labels, capacity, runner/job-network reachability, Docker privilege/volumes, cache routing and monitoring exposure before changing configuration.

For debugging, load `references/actions/troubleshooting.md` and find the first failing layer before editing YAML: event, parser/semantics, runner labels/availability, capacity, network/TLS, action resolution, runtime, permissions/secrets, cache/artifacts, project code, or server/runner regression.

Templates are under `templates/actions/`. Use them as starting points, never as blind copy/paste.

## Safety Policy

Ordinary reads need no extra confirmation. User-requested routine creates/edits may proceed after target resolution. The current request must explicitly authorize:

- deletion of repos/branches/tags/issues/releases/wiki/packages/webhooks/runners/users/orgs/teams/tokens/secrets/variables;
- PR merge;
- force push/history rewrite or protection/check bypass;
- collaborator/team/ownership/visibility/access/protection changes;
- runner registration-token operations, runner credential reset, or Actions secret writes;
- production deployment state/secret rotation;
- `/admin/*` mutation, sudo/impersonation, migration overwrite or bulk destructive work.

Never set `force_merge=true`. Never use `git push --force`; if an explicitly authorized rewrite is necessary, prefer `--force-with-lease` after recording the expected remote SHA.

### Actions security gate

Before approving production workflows load `references/actions/security.md`. Block any design where untrusted code can obtain production secrets, control a privileged runner/Docker daemon, access dangerous host mounts, or reach deployment/signing infrastructure without an intentional trust boundary.

Use least privilege. Treat runner infrastructure and scoped workflow source repositories as critical infrastructure. Source Actions secret values from protected environment/input paths; never place them in visible shell arguments, assistant text, logs, JSON output or templates.

## Pull Request Merge Discipline

1. Read the PR and capture exact `head.sha`.
2. Inspect branch protection and status checks for that SHA.
3. If reviewing, review that same SHA.
4. Re-read immediately before merge; if SHA changed, stop.
5. PR merge is intentionally absent from the native plugin. Only when the user explicitly requests merge and policy permits it, use the bundled guarded CLI with `pr merge --head-sha SHA --confirm 'MERGE:OWNER/REPO#N@SHA'`.
6. Require the helper's post-read to report `merged=true`; never set `force_merge=true`.

Do not use `--allow-non-green` unless explicitly requested and permitted by server policy.

## Git Rules

- Prefer SSH when configured; otherwise HTTPS without embedding PATs in remotes.
- Before push: fetch, inspect status, branch/upstream, remote head SHA and every changed file.
- Prefer branch + PR for substantive automated changes unless direct push is explicitly desired and allowed.
- Never alter global Git identity/config as a side effect.

## Known Problems

- Gitea Actions is GitHub-Actions-like, not identical; parsing does not prove semantic compatibility.
- Server/Runner behavior is version-sensitive; exact target runtime is authoritative.
- `localhost` inside runner/job containers often does not refer to Gitea.
- Runner cache may be local rather than shared.
- PAT scopes are only one authorization layer; ACLs, units, protection and instance policy still apply.
- Pagination may be required for completeness.
- Mutation/dispatch timeout is ambiguous; reconcile before repeating.
- Assumptions are optimized for Gitea 1.27.x; deployed `/swagger.v1.json` and observed exact-version behavior are final authority.
- Redirects are intentionally blocked; configure the canonical URL.

## Verification

```text
gitea_connection_status
python -m unittest discover -s ${HERMES_SKILL_DIR}/tests -v
python ${HERMES_SKILL_DIR}/scripts/audit_workflow.py .gitea/workflows/<workflow>.yml
```

If the native plugin is unavailable, use the bundled `doctor.py` as a fallback connectivity diagnostic.

A completed task must inspect relevant source/configuration, establish versions where material, make the smallest safe change, verify resulting state, and leave no unexplained security-critical Actions finding.
