# Production Patterns and Anti-Patterns

## Pattern: Split CI and Deployment Trust

```text
PR/push -> build/test -> artifact/image -> trusted deploy job/runner
```

The build runner does not need cluster credentials. The deployment runner does not compile arbitrary PR code.

## Pattern: Immutable Release Identity

Tag images/artifacts with commit SHA and release tag. Deploy by immutable digest where practical.

## Pattern: Scripted Logic, Thin YAML

Good:

```yaml
- run: ./ci/test.sh
```

Avoid embedding large conditional Bash programs in workflow YAML. Scripts are easier to lint, test locally, and reuse.

## Pattern: Explicit Pre-Merge PR Test

For repositories where integration with the base branch matters, fetch and merge the base explicitly before tests.

## Pattern: Dedicated Runner Pools

Use labels such as:

```text
pr-untrusted
ci-linux
release-linux
deploy-prod
```

Do not encode secrets into labels. Labels describe capability/trust.

## Pattern: Central Policy with Scoped Workflows

Use scoped workflows for organization-wide lint/security/compliance gates. Protect the policy repository with strict review.

## Pattern: Shared Cache Only When It Pays

Small installations: per-runner cache is simpler.

Larger homogeneous pools: shared cache can improve hit rate, but add health/latency/eviction monitoring.

## Pattern: Canary Runner Upgrade

Upgrade one runner, execute fixture suite, compare metrics/logs, then roll out.

## Anti-Pattern: “Works on GitHub, therefore works on Gitea”

Always perform a compatibility classification.

## Anti-Pattern: One Instance Runner for Everything

An instance-wide privileged runner creates a large blast radius. Narrow scope and separate trust domains.

## Anti-Pattern: Secrets in Global `env`

Prefer step/job-level exposure. Global environment broadens accidental leakage.

## Anti-Pattern: Mutable `uses: @main`

A branch ref allows dependency code to change without workflow changes.

## Anti-Pattern: Production Docker Socket in PR CI

Docker socket access can be equivalent to host control.

## Anti-Pattern: Using `environment` as a Security Gate

Do not assume GitHub Environment approvals/protections are enforced by Gitea.

## Anti-Pattern: Increasing `capacity` as the First Scaling Fix

Measure CPU, memory, disk, Docker networks, cache, and downstream services first.

## Pattern: Failure Artifacts

When tests fail, upload machine-readable reports/log bundles where possible. Do not depend on GitHub-style annotations being rendered.

## Pattern: Purpose-Specific Credentials

Use separate credentials for:

- source read;
- package push;
- release API;
- signing;
- staging deploy;
- production deploy.

This limits blast radius and simplifies rotation.
