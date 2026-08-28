# Gitea Actions Control Plane

## Module Router

This file covers the Gitea-side Actions API/control plane. For workflow semantics use `workflows.md`; GitHub migration uses `compatibility.md`; runner infrastructure uses `runners.md`; security review uses `security.md`; runtime failures use `troubleshooting.md`; production architecture uses `patterns.md`.

## Model

Gitea Actions is GitHub-Actions-like but not identical. Workflows live in the repository and are executed by `act_runner` instances registered at repository, organization, or global scope. Never assume every GitHub event, expression, marketplace action, permission, or API exists unchanged.

Treat runners as execution infrastructure capable of running repository-controlled code. Separate them from the Gitea server and isolate untrusted workloads.

## API capabilities

Current repository APIs include operations for:

- workflow runs;
- run attempts and jobs;
- job logs;
- artifacts;
- rerun job/run/failed jobs;
- workflows and workflow dispatch;
- repository runners and registration tokens;
- Actions secrets;
- Actions variables;
- repository tasks.

Organization and admin APIs expose corresponding runner/run/secret/variable operations at broader scopes.

Use live schema discovery before broad/admin runner operations.

## Common endpoints

- `GET /repos/{owner}/{repo}/actions/runs`
- `GET /repos/{owner}/{repo}/actions/runs/{run}`
- `GET /repos/{owner}/{repo}/actions/runs/{run}/jobs`
- `POST /repos/{owner}/{repo}/actions/runs/{run}/rerun`
- `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches`
- repository Actions secrets/variables under `/repos/{owner}/{repo}/actions/...`
- repo runners under `/repos/{owner}/{repo}/actions/runners...`

Workflow dispatch body requires a `ref` and can include string inputs. Current API can optionally return workflow-run details.

## Dispatch discipline

Before dispatch:

1. Identify exact workflow ID/path and ref.
2. Check workflow supports `workflow_dispatch` and validate expected inputs.
3. Resolve whether inputs are ordinary values or secrets. Use `--input key=value` only for non-sensitive inputs; for a sensitive input use `--input-env key=ENV_VAR`. Never pass a secret as a visible command-line argument.
4. Dispatch once.
5. Capture returned run ID/URL when available and inspect the run.

A timeout after dispatch is ambiguous. Do not immediately dispatch again; search recent runs for workflow/ref/correlation first.

## Reruns

Rerunning causes code execution and can duplicate deployments or other side effects. The helper requires:

`RERUN:OWNER/REPO:RUN_ID`

Read the original run/jobs first and confirm rerun intent. Prefer rerun-failed-jobs if the user specifically wants only failures and the server exposes it.

## Secrets and variables

Actions secrets are sensitive write operations. Never list secret values, log them, place them in command history, or echo them through the model. Listing endpoints should only expose secret names/metadata.

Prefer the built-in helper for repository secrets:

```text
actions secret-list OWNER REPO
actions secret-set OWNER REPO NAME --value-env SOURCE_ENV --confirm 'SET_SECRET:OWNER/REPO:NAME'
actions secret-delete OWNER REPO NAME --confirm 'DELETE_SECRET:OWNER/REPO:NAME'
```

`secret-set` reads the value from `SOURCE_ENV`, sends it in the request body, does not place it in command arguments, and never emits it. If Hermes uses a sandboxed or remote terminal backend, `SOURCE_ENV` must be explicitly permitted for environment passthrough; `GITEA_TOKEN` is the only secret this skill declares automatically. Verify only secret name/metadata existence afterward, never attempt to read or print the secret value.

For organization/user/admin secrets or a version-specific secret operation not covered by the wrapper:

- obtain the exact endpoint with `schema --search 'secret'`;
- source the secret from an environment variable, credential file, or protected stdin mechanism;
- construct the request without printing the value;
- verify only metadata/name existence afterward, never read back/print the value.

Variables are not automatically secrets. Still inspect whether they contain sensitive material before displaying them.

## Runner security

- Avoid running untrusted public-repo code on a runner with access to the Gitea host, Docker socket, LAN secrets, or privileged host mounts.
- Separate runner registration scope: repo < org < global. Use the narrowest scope.
- Runner registration tokens are secrets; treat creation/retrieval as privileged.
- Validate runner labels against workflow `runs-on` requirements.
- A runner inside a container must reach Gitea through an address valid from that container; `localhost` frequently points to the runner container itself.

## GITEA_TOKEN inside workflows

The workflow/job token is separate from the PAT used by this Hermes skill. Its effective permissions depend on Actions/repository policy. Do not copy a job token out of a runner into Hermes persistent configuration.

## Monitoring

For a requested run diagnosis:

1. read run;
2. enumerate jobs;
3. identify failed/pending/cancelled jobs;
4. read relevant logs if API/version supports it;
5. correlate with runner labels/availability and workflow YAML;
6. distinguish workflow failure from runner/infrastructure failure.

## Source links

- https://docs.gitea.com/usage/actions/overview/
- https://docs.gitea.com/usage/actions/design/
- https://docs.gitea.com/usage/actions/comparison/
- https://docs.gitea.com/usage/actions/token-permissions/
- https://docs.gitea.com/runner/
- https://docs.gitea.com/api/operations/actions-dispatch-workflow/
