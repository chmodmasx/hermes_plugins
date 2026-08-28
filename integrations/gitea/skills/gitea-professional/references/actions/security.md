# Gitea Actions Security and Hardening

A CI runner is remote code execution infrastructure. The main question is not “does the workflow run?” but “what can executed repository code reach?”

## Trust Boundaries

Separate at least these classes:

1. untrusted fork/PR validation;
2. normal trusted branch CI;
3. package/release signing and publication;
4. production deployment;
5. organization/instance policy workflows.

Do not collapse them into one privileged runner pool.

## Blocking Findings

Treat these as blocking unless the user explicitly accepts the risk:

- untrusted PR code can access production/deploy/signing secrets;
- untrusted code can control Docker socket/daemon;
- untrusted code runs privileged;
- arbitrary host paths can be mounted;
- host-mode runner serves untrusted repositories;
- instance/org runner serves unknown repositories while holding persistent privileged state;
- third-party action runs from a mutable branch/tag in a high-trust job without explicit acceptance;
- secrets are printed, embedded in URLs, committed, or passed in ways visible to process listings/logs;
- a central scoped-workflow repository is writable by actors who should not control organization-wide CI.

## Token Permissions

Start every workflow with explicit minimal permissions.

Example:

```yaml
permissions:
  code: read
```

Grant write permission only in the job that needs it if job-level permissions are supported on the target version.

Avoid `write-all` unless there is a documented reason and no narrower scope.

Do not copy unsupported GitHub permission scopes.

## Fork Pull Requests

A read-only job token does not make a privileged runner safe.

Untrusted repository code can still:

- inspect filesystem;
- probe internal network;
- attack exposed Docker daemon;
- exploit mounted credentials;
- persist through host mode;
- consume resources.

Use isolated low-privilege runners with no production network path.

## `pull_request_target`

Treat as dangerous by default when combined with checkout/execution of contributor-controlled code.

Safe principle: trusted-context jobs may inspect metadata or label/comment; do not execute untrusted PR contents with elevated secrets/permissions.

## Docker

### Socket

Mounting `/var/run/docker.sock` effectively delegates control over the Docker host. Never expose it to untrusted workflows.

### Privileged

Privileged containers can defeat normal container boundaries. Restrict to dedicated trusted pools.

### Volumes

Allow only pre-approved volumes. Arbitrary host mounts can expose SSH keys, runner credentials, service configs, package credentials, and system files.

## Host Mode

Host mode should be considered equivalent to running repository code directly as the runner OS user.

Use:

- dedicated disposable machines;
- trusted repositories;
- low-privilege service account;
- no unrelated credentials;
- filesystem cleanup;
- network segmentation.

## Secrets

Principles:

- one purpose per secret;
- smallest scope;
- shortest practical lifetime;
- do not expose to PR validation;
- rotate after suspected disclosure;
- prefer stdin over command-line token arguments;
- write temporary secret files with restrictive permissions;
- remove temporary files after use;
- never echo a secret to “verify” it.

## Package and Registry Credentials

If the built-in job token cannot publish to the target Gitea package/OCI registry, create a dedicated token limited to package publication. Do not substitute a full admin PAT.

Separate:

- registry push credential;
- deployment cluster credential;
- signing key;
- Gitea release API permission.

## Third-Party Actions

An action is executable dependency code.

Production policy:

1. prefer official/approved actions;
2. review source and transitive behavior;
3. pin full commit SHA;
4. record upstream repository;
5. mirror critical actions internally when availability or supply chain control matters;
6. periodically refresh pins after review.

A major tag such as `@v4` is convenient but mutable.

## Scoped Workflows

Scoped workflows can centralize mandatory CI/security/compliance. Their source repository becomes organization-wide control plane code.

Protect it with:

- restricted write access;
- mandatory review;
- branch protection;
- signed/reviewed changes where practical;
- no secrets in logs;
- tests against representative repositories.

Remember that workflow logic may be observable through consumer logs.

## Network Segmentation

Recommended runner pools:

- `pr-untrusted`: internet + Gitea only, no internal infra;
- `ci-trusted`: dependency mirrors/registry, no production deploy;
- `release`: package registry/signing services only;
- `deploy-prod`: production control plane only, no untrusted triggers.

Default-deny egress where feasible.

## Supply-Chain Outputs

For releases, add as appropriate:

- checksums;
- SBOM;
- signature;
- provenance/attestation;
- immutable image digest;
- reproducible build metadata.

Do not let the workflow itself overwrite previously published immutable release identifiers.

## Logging

Review logs for:

- accidental secret echo;
- shell tracing (`set -x`) around secrets;
- full HTTP Authorization headers;
- registry login commands with inline password;
- environment dumps;
- kubeconfig/private key output.

Treat log retention as part of secret exposure risk.

## Security Review Output

When auditing, classify findings:

- `CRITICAL` — likely host/production/credential compromise;
- `HIGH` — strong privilege or supply-chain risk;
- `MEDIUM` — compatibility/security weakness requiring correction;
- `LOW` — hardening/maintainability issue;
- `INFO` — version-sensitive or intentional behavior to verify.

For every finding provide: evidence, impact, fix, and verification.
