# Gitea vs GitHub Actions Compatibility

The correct model is “related dialects with substantial overlap,” not “drop-in clone.”

## Classification

For every migrated or advanced construct, assign one status:

- **verified** — documented and/or tested on the exact target versions;
- **gitea-specific** — supported but intentionally different from GitHub;
- **unsupported** — documented as ignored or unavailable;
- **needs-runtime-test** — syntax may parse, but semantic parity is uncertain/version-sensitive.

Never leave an advanced construct unclassified during migration.

## High-Value Differences

### `jobs.<job_id>.environment`

Do not assume GitHub Environment approval/protection/deployment semantics. Current Gitea comparison documentation has documented `environment` as ignored/not equivalent.

**Migration:** replace environment protection with explicit branch protection, scoped workflow gates, dedicated runner trust boundaries, or an external approval/deployment mechanism.

### Complex `runs-on`

Simple string/list label matching is the safe baseline. GitHub-style dynamic or object-like selector patterns require verification.

### Problem matchers and annotations

Do not rely on GitHub UI annotations/problem matcher behavior for correctness. Preserve machine-readable reports as artifacts and fail steps explicitly.

### Expressions/functions

Gitea's comparison documentation has historically lagged or limited expression-function support relative to GitHub. Treat functions such as `hashFiles()` and complicated expression compositions as version-sensitive.

### Permission scopes

Do not copy these GitHub scopes without redesign:

- `id-token`
- `checks`
- `statuses`
- `deployments`
- `security-events`
- `pages`

If a pipeline needs OIDC federation, GitHub Checks, Pages, or deployment-environment semantics, design a Gitea-native/external equivalent rather than silently keeping the YAML.

### PR refs

Gitea pull-request refs can represent the PR head rather than the synthetic merge commit GitHub workflows often expect.

**Migration:** if the invariant is “tests pass after merge with base,” explicitly fetch and merge/rebase the base in the test job.

### Package publishing

Do not assume the built-in job token can publish to every Gitea package/OCI endpoint. Current Gitea documentation has documented gaps requiring a dedicated PAT/token for package publication.

**Migration:** create a purpose-specific credential with the minimum package scope and expose it only to the publish job.

### Workflow directories

Gitea can recognize both `.gitea/workflows` and `.github/workflows`, but configuration may select the first existing directory rather than combine them.

### Action sources

GitHub Marketplace is not a native Gitea marketplace contract. `uses: owner/action@ref` may be resolved from GitHub by default depending on server configuration. Gitea also supports self-hosted/mirrored/absolute Git action sources.

### Scoped workflows

Gitea scoped workflows are a Gitea-specific governance mechanism and should not be mapped mentally to GitHub Environments.

## Migration Checklist

For every source workflow:

1. Record source file and trigger.
2. Record required GitHub-specific APIs/services.
3. Inventory every `${{ ... }}` expression/function.
4. Inventory every `uses:` action and pin/ref.
5. Inventory permissions and token use.
6. Inventory secrets and environment protections.
7. Inventory `runs-on`, matrices, concurrency, reusable workflows, services, artifacts, and cache.
8. Identify any expectation of GitHub-hosted runner images/tools.
9. Identify any PR merge-ref assumption.
10. Identify any package publishing via `GITHUB_TOKEN`.
11. Classify each item.
12. Replace unsupported items explicitly.
13. Run the static auditor.
14. Run `gitea-runner exec` where applicable.
15. Run server-backed smoke tests for event payloads, tokens, artifacts, branch protection, scoped workflows, and registry behavior.

## Portability Policy

When the user needs one YAML to run on both GitHub and Gitea:

- prefer shared syntax (`push`, `pull_request`, simple jobs/steps);
- use `${{ github.* }}` only where Gitea explicitly aliases it;
- avoid platform-specific permission scopes;
- avoid `environment` as a critical gate;
- keep advanced logic in portable scripts;
- pin actions to commits that are known to execute under both runners;
- test on both systems.

Do not claim “portable” until both CI systems have executed the same fixture successfully.

## Features That Demand Version Verification

Always verify target versions before relying on:

- advanced expression functions;
- reusable workflows;
- `workflow_call` edge cases;
- `workflow_run`;
- matrix `max-parallel` and complex matrix expressions;
- `concurrency`;
- modern cache/artifact action releases;
- token package-write behavior;
- scoped workflows;
- new event types;
- permission model changes.

## Evidence Priority

When sources disagree:

1. exact-version Gitea documentation;
2. exact-version Gitea/Gitea Runner source code and release notes;
3. reproducible test against the target versions;
4. open/closed upstream issues and PRs;
5. GitHub Actions docs only for the behavior being emulated;
6. third-party tutorials last.

Record uncertainty instead of filling gaps from GitHub knowledge.
