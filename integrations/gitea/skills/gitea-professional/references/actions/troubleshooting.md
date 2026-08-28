# Gitea Actions Troubleshooting Runbook

Debug from event -> scheduler -> runner -> runtime -> step -> transport. Do not begin by randomly changing YAML.

## 1. Workflow never starts

Check:

1. Actions enabled for the instance/repository.
2. Workflow file is in an active configured workflow directory.
3. YAML parses.
4. Event matches `on:`.
5. branch/tag/path/type filters match.
6. commit message does not contain a configured skip-workflow marker.
7. workflow is not shadowed by workflow-directory precedence.

Evidence to collect:

- target commit/tag;
- event type;
- workflow path;
- server version;
- relevant Actions UI/event record.

## 2. Job stays queued

Check:

1. runner online;
2. runner scope includes repository;
3. exact `runs-on` label match;
4. runner ready;
5. `capacity` not saturated;
6. runner polling errors;
7. server/runner protocol compatibility.

Do not “fix” by changing `runs-on` until real runner labels are known.

## 3. Checkout/action download fails

Separate:

- job container -> Gitea clone URL;
- runner -> action source;
- job -> internet/internal mirror;
- TLS/CA;
- DNS;
- proxy;
- credentials.

Classic failure: runner registered to `localhost`, job container cannot reach it.

## 4. Container cannot reach Gitea

From the exact job network namespace/container, test:

- DNS resolution;
- TCP reachability;
- TLS;
- HTTP endpoint.

Fix stable routing/name resolution. Do not permanently disable TLS validation.

## 5. `uses:` fails

Check:

1. source resolution policy (`DEFAULT_ACTIONS_URL` or equivalent);
2. repository exists;
3. ref/SHA exists;
4. outbound network;
5. authentication for private action;
6. action runtime compatibility;
7. Node/Docker/composite action requirements.

Prefer mirrors/pins for production.

## 6. Cache timeout/miss

If only some runners hit cache:

- cache is probably runner-local.

If cache upload/restore times out:

- inspect advertised cache host/port;
- inspect Docker port publishing;
- inspect job-container route/DNS;
- inspect firewall;
- inspect shared secret if using shared cache.

Do not blame the cache key until transport works.

## 7. Artifact upload/download fails

Check:

- runner version;
- artifact action version;
- server storage;
- size/retention limits;
- runner/server connectivity;
- logs on both sides.

## 8. Permission denied from API

Check:

1. exact API endpoint;
2. built-in token vs PAT;
3. workflow/job `permissions`;
4. repository ownership/fork status;
5. target feature scope;
6. whether the feature is supported by Gitea job-token permissions.

For package publication, verify whether a dedicated token is required.

## 9. PR tests differ from GitHub

Check whether the workflow expects a synthetic merge commit. Gitea may expose PR head semantics. If pre-merge correctness is required, fetch the base and merge it explicitly before tests.

## 10. Workflow parses but advanced expression behaves incorrectly

Classify the expression as `needs-runtime-test`. Compare with exact-version Gitea documentation/source and build a minimal reproducer.

Do not rewrite based solely on GitHub docs.

## 11. Runner is slow or unstable

Inspect:

- CPU;
- RAM;
- disk free/IO;
- Docker network/address-pool exhaustion;
- container/image pull latency;
- cache latency;
- registry latency;
- Gitea response times;
- capacity utilization;
- cleanup failures.

Scale based on the bottleneck, not solely by raising `capacity`.

## 12. Runner daemon evidence

Use runner debug/trace logging temporarily when needed. Collect:

- runner version;
- config (with secrets redacted);
- labels;
- capacity;
- execution mode;
- polling errors;
- job assignment;
- container creation;
- cleanup;
- cache/artifact transport errors.

If supported, use `gitea-runner bug-report` and `gitea-runner exec` for reproducibility.

## Minimal Reproducer Strategy

Reduce a failure to:

```yaml
name: Repro
on:
  workflow_dispatch:
jobs:
  repro:
    runs-on: <exact-label>
    steps:
      - run: <one failing behavior>
```

Add one feature at a time until the failure returns.

## Root-Cause Report

Return:

- symptom;
- first failing layer;
- direct evidence;
- root cause;
- smallest safe fix;
- compatibility/security impact;
- verification command/run;
- remaining uncertainty.

Avoid lists of speculative fixes without ranking or evidence.
