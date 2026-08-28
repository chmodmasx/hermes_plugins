# Gitea Actions Workflow Reference

Use this reference for authoring and reviewing workflow semantics. Re-check the official documentation for version-sensitive features.

## Mental Model

A workflow is a YAML document selected by an event. It expands into one or more jobs. Jobs are scheduled to compatible runners. Steps inside a job run sequentially. Jobs can run in parallel unless linked by dependencies.

Prefer `.gitea/workflows/` for Gitea-native repositories. Some installations also recognize `.github/workflows/` through `WORKFLOW_DIRS`; do not assume both directories are merged.

## Conservative Skeleton

```yaml
name: CI

on:
  push:
  pull_request:

permissions:
  code: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<PINNED_SHA>
      - run: ./ci/test.sh
```

## Events

Common documented event families include:

- `push`
- `pull_request`
- `pull_request_target`
- `pull_request_review`
- `pull_request_review_comment`
- `issues`
- `issue_comment`
- `release`
- `registry_package`
- `schedule`
- `workflow_dispatch`
- `workflow_call`
- `workflow_run`
- repository events such as `create`, `delete`, `fork`, and `gollum`

Treat `pull_request_target` as security-sensitive: it can create a trusted-context/untrusted-code combination if used incorrectly.

### PR pre-merge testing

Do not assume GitHub's synthetic merge-ref behavior. If the requirement is “test what would result after merging the PR into its base branch,” fetch the base and create a local merge explicitly before tests.

## Contexts

Prefer Gitea-native contexts in new workflows:

```yaml
${{ gitea.sha }}
${{ gitea.ref }}
${{ gitea.ref_name }}
${{ gitea.event_name }}
${{ gitea.repository }}
${{ gitea.base_ref }}
${{ gitea.head_ref }}
```

Many `${{ github.* }}` names are compatibility aliases. Use them only when dual-platform portability is a deliberate goal.

## Environment Variables

GitHub-style environment variable names such as `GITHUB_SHA`, `GITHUB_REF`, and `GITHUB_WORKSPACE` may be provided for compatibility. Do not infer that every GitHub-specific variable/API endpoint exists; GraphQL behavior is a known divergence.

## Token Permissions

Declare permissions explicitly. Favor:

```yaml
permissions:
  code: read
```

Add only the scopes the job needs. Supported Gitea scopes differ from GitHub. Current documented Gitea-oriented scopes include areas such as:

- `code` / `contents` depending on version/context
- `releases`
- `issues`
- `pull-requests`
- `actions`
- `wiki`
- `projects`
- `packages`

GitHub-specific scopes such as `id-token`, `checks`, `statuses`, `deployments`, `security-events`, and `pages` must not be assumed to work.

For fork PRs, still apply runner isolation even when the job token is read-only.

## Secrets

Secrets can exist at multiple scopes. Use `${{ secrets.NAME }}`.

Rules:

- never print secret values;
- do not interpolate secrets into URLs;
- prefer stdin for passwords/tokens;
- use a dedicated secret for registry publication or deployment rather than a general admin token;
- do not expose deployment secrets to PR jobs.

## Jobs and Dependencies

Use `needs:` for explicit DAG ordering:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: ./ci/test.sh

  deploy:
    needs: [test]
    runs-on: deploy-linux
    steps:
      - run: ./ci/deploy.sh
```

A deployment job should run on a separate, trusted runner when possible.

## Runner Labels

`runs-on` must correspond to labels actually advertised by Gitea Runner. Avoid GitHub-style complex selector expressions unless verified on the exact Gitea/Runner versions.

## Matrices

Conservative matrix pattern:

```yaml
strategy:
  fail-fast: false
  matrix:
    python: ["3.12", "3.13"]
```

Treat advanced controls such as matrix-dependent expression tricks and `max-parallel` as version-sensitive. Test them.

## Expressions

Do not use “GitHub supports it” as evidence. Functions such as `hashFiles()` and complex expression combinations need compatibility verification on the target version.

Prefer moving complex decisions into scripts where possible.

## Artifacts

Modern Gitea Runner 3.x documentation describes compatibility with current official artifact actions through runner-side adaptation. Verify the specific action version against the runner version.

Pattern:

```yaml
- uses: actions/upload-artifact@<PINNED_SHA>
  with:
    name: test-results-${{ gitea.sha }}
    path: reports/
    retention-days: 14
```

## Cache

Runner 3.x supports cache service v2 used by current `actions/cache` releases. Important operational rule: cache is commonly local to each runner unless configured as shared.

Cache keys should be deterministic and easy to invalidate. Avoid relying on advanced expression functions until verified.

## Services and Containers

When a job or service container must reach Gitea, the runner's registration URL and advertised endpoints must be resolvable from the container network. `localhost` normally refers to the container itself, not the Gitea host.

Inspect:

- Docker networks;
- DNS;
- TLS CA trust;
- published ports;
- proxy configuration;
- cache endpoint reachability.

## Timeouts, Cancellation, Retries

There are server-side defaults for stale/zombie/endless/abandoned tasks and retry limits. These are administrator-configurable. Do not hard-code defaults as universal guarantees; inspect the target installation when timeout behavior is central to the issue.

## Reusable and Scoped Workflows

Treat reusable workflows as version-sensitive.

Gitea 1.27 introduced scoped workflows for organization/instance policy. A scoped workflow can execute centrally maintained workflow logic in the context of consuming repositories. Protect the source repository as infrastructure code because compromise affects every consumer.

Do not assume every trigger is valid for scoped workflows; verify current documentation.

## Action Resolution

A `uses:` dependency may resolve from GitHub, the local Gitea instance, mirrors, or an absolute Git URL depending on configuration and syntax.

Production policy:

1. prefer an approved source;
2. pin by immutable commit SHA;
3. mirror critical actions internally when egress/reliability/supply-chain control matters;
4. validate that required action runtime/tooling works under Gitea Runner.

## Workflow Directory Trap

Gitea installations can configure multiple workflow directories. If both `.gitea/workflows` and `.github/workflows` exist, determine actual server configuration and behavior rather than assuming both sets run.
