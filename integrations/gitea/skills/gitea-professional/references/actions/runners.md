# Gitea Runner Operations

Use this reference for runner registration, execution, labels, networking, cache, capacity, monitoring, and isolation.

## Architecture

Gitea schedules work; runners poll the server, accept compatible jobs, prepare execution environments, and return logs/status.

Validate four paths separately:

1. runner process -> Gitea;
2. job container -> Gitea;
3. runner -> action/image/dependency sources;
4. job container -> action/image/dependency sources.

A successful runner registration does not prove job-container connectivity.

## Version Discipline

Gitea Runner versioning is independent from Gitea server versioning. Major runner releases can contain incompatible changes. Capture both versions before debugging behavior that spans the protocol/runtime.

Use `terminal(command="gitea-runner --version")`.

For containerized runners, inspect the image tag/digest as well.

## Registration Scope

Runners can be registered for different scopes such as:

- repository;
- owner/organization/user;
- instance.

Choose the narrowest scope compatible with the use case.

A registration token can be reused until reset according to server policy. After registration, protect the runner identity/credential file (commonly `.runner`). Do not clone it to multiple machines/processes.

## Labels

Runner labels map workflow `runs-on` requirements to actual execution schemas.

Conceptually:

```text
label[:schema[:args]]
```

Examples may map a label to:

- a Docker image;
- host execution.

When a job is stuck queued:

1. compare workflow `runs-on`;
2. compare online runner labels;
3. check scope;
4. check capacity;
5. check runner readiness.

## Execution Modes

### Docker

Preferred general-purpose mode.

Benefits:
- per-job container isolation;
- reproducible toolchain image;
- easier cleanup.

Risks:
- shared Docker daemon can widen impact;
- socket exposure can become host-equivalent control;
- network/DNS/cache endpoints must be reachable from child containers.

### Docker-in-Docker

Provides a separate Docker daemon boundary from the host daemon but often requires privileged execution.

Use only in a dedicated trust domain. Treat privileged DinD as high impact.

### Host mode

Runs job processes directly on the machine.

Use only for trusted workloads that genuinely require host execution. It lacks container isolation between jobs and can leave persistent state.

## Capacity

`runner.capacity` controls concurrent jobs per runner process. Default values can be conservative.

Do not increase capacity until checking:

- CPU saturation;
- RAM;
- disk IOPS/space;
- Docker address pools/network count;
- registry bandwidth;
- cache server;
- Gitea server throughput;
- downstream deployment API rate limits.

Scale out dedicated runners before forcing excessive density onto one host.

## Networking

### Never assume `localhost`

If the runner registers to `http://localhost:3000`, a job container will usually interpret `localhost` as itself.

Prefer a stable URL resolvable from both:

- the runner process;
- every job/service container.

Check with targeted commands from the exact network namespace/container, not only from the host.

### TLS

For internal CAs:

- install CA trust in runner environment;
- install CA trust in job images or inject a trusted CA mechanism;
- do not disable TLS verification as a permanent fix.

### Proxies

Verify proxy settings independently for runner and job containers.

## Cache

Runner 3.x supports modern cache service behavior. By default, cache may be local to an individual runner.

For multi-runner pools, choose deliberately:

- local cache: simple, lower coordination, lower cross-runner hit rate;
- shared cache server: consistent reuse across runners;
- shared filesystem/object-backed mount: operationally heavier.

### Common Docker cache failure

Symptom: cache upload/restore times out from job containers while runner itself is healthy.

Check:

1. advertised cache host;
2. advertised cache port;
3. published port;
4. Docker network;
5. DNS;
6. firewall;
7. route from job container.

Do not diagnose this as an `actions/cache` YAML problem until endpoint reachability is proven.

## Artifacts

Artifacts flow through runner/server integration. Verify action version compatibility with the runner major version and check server-side retention/storage when uploads fail after the step starts.

## Ephemeral Runners

Prefer one-job ephemeral runners for broad organization/instance pools executing diverse or partially untrusted workloads.

Properties to target:

- fresh VM/container per runner;
- runner accepts one job;
- credential cannot be reused to fetch further work after assignment/completion;
- instance is destroyed after job;
- no persistent secrets or workspace survive.

Use webhooks or external autoscaling only when the provisioning system itself is secured.

## Privilege Controls

Safe baseline:

- privileged execution off;
- no arbitrary host volume mounts;
- no Docker socket for untrusted workloads;
- dedicated runner pools for deploy/sign/release;
- distinct network access by pool.

If a workload must use Docker socket or privileged mode, scope the runner to trusted repositories only.

## Monitoring

Current runner documentation exposes health/readiness and Prometheus-style metrics.

Protect monitoring listeners because they may not provide built-in authentication.

Useful signals:

- job capacity utilization;
- in-progress jobs;
- polling failures;
- RPC failures;
- job duration;
- log/reporting backlog;
- free disk;
- readiness.

A runner can be alive but not ready to accept new jobs.

## Health Checks

Use local runner health checks to stop admitting new jobs when prerequisites fail, for example low disk space.

Do not use health checks as a substitute for centralized alerting.

## Upgrade Procedure

1. Read target runner release notes.
2. Back up configuration and identify runner credential file.
3. Record current labels, capacity, execution mode, cache, and network config.
4. Drain or stop new job admission.
5. Upgrade one canary runner.
6. Run representative workflow fixtures: checkout, cache, artifact, container build, matrix, secrets, release API.
7. Compare logs/metrics.
8. Roll through remaining runners only after canary success.
9. Keep server and runner rollback procedures separate.

## Verification

- runner appears online in intended scope;
- intended labels are visible;
- a minimal job is scheduled to it;
- job container can reach Gitea;
- cache endpoint is reachable when enabled;
- artifacts upload/download;
- runner returns to ready state after cleanup;
- metrics/health are accessible only from trusted monitoring networks.
