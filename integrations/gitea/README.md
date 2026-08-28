# Gitea ↔ Hermes Integration 1.0.0

A native Hermes integration bundle for **Gitea 1.27.x**, designed and tested against the Gitea **1.27.2 API contract**.

This bundle installs two cooperating components:

- `gitea-hermes` — a native Hermes plugin with typed Gitea tools (`gitea_read` / `gitea_write`).
- `gitea-professional` — the policy/knowledge skill that teaches Hermes how to use Gitea safely and professionally.

Git itself remains Git: clone/fetch/commit/push should use SSH and the normal Hermes terminal/file workflow. The Gitea plugin handles the Gitea control plane: repository metadata, issues, PRs, Actions, runners, releases, and related API state.

## Why the package is split internally

Hermes can bundle skills inside plugins, but plugin skills are namespaced and are not listed in the normal `<available_skills>` index. For automatic skill discovery, this bundle intentionally installs `gitea-professional` as a normal local skill while installing `gitea-hermes` under the native plugin directory.

## Compatibility choices

- Gitea target: `>=1.27.0,<1.28`; recommended/test baseline: `1.27.2`.
- Hermes plugin contract: native `plugin.yaml` + `register(ctx)`.
- Manifest: conservative **v1** (no `manifest_version` field). Current Hermes documentation describes manifest v2, but current installer builds have had a known v1/v2 installer/loader mismatch. A v1 manifest uses only the long-supported additive runtime contract and avoids that deployment bug.
- Python dependencies: standard library only. No package installation is required at plugin registration time.
- `register(ctx)` performs no network requests. This is compatible with `hermes plugins doctor --ci`, which blocks direct sockets during registration.

## Native tools

The plugin exposes 33 semantic tools: 24 read/diagnostic tools and 9 routine mutation tools.

Read examples: connection/capability status, repositories, contents/files, branches/commits/status, issues, PR metadata/files/commits/reviews, Actions runs/jobs/logs/artifacts, runners, releases, webhooks, live OpenAPI search.

Write examples: branch creation, issue create/update/comment, PR create/review, Actions dispatch/rerun, release creation.

### Deliberately not exposed in v1

- repository/branch/tag/issue/release/webhook deletion
- instance administration
- Actions secret writes
- runner registration-token/reset/delete operations
- arbitrary generic REST writes
- PR merge
- REST-based source-file editing as a substitute for Git

The bundled skill contains guarded procedures for advanced work, but absence from the native plugin is an intentional safety boundary.

## Recommended Gitea identity

Create a dedicated normal Gitea account such as `hermes-bot` and grant it access only to repositories/organizations Hermes should reach. Create a scoped PAT for API work; a practical baseline is `read:user`, `write:repository`, and `write:issue`, reduced further if your workflow permits. Do not use an administrator PAT for routine operation.

Configure a separate SSH key for `hermes-bot` and use the repository's SSH clone URL for Git operations.

## Install

From the monorepo root:

```bash
./install.sh gitea
```

Or directly from this directory:

```bash
./install.sh
```

The installer:

1. installs the plugin to `${HERMES_HOME:-~/.hermes}/plugins/gitea-hermes`;
2. installs the skill to `${HERMES_HOME:-~/.hermes}/skills/gitea-professional`;
3. securely configures `GITEA_BASE_URL` and `GITEA_TOKEN` when run interactively;
4. runs `hermes plugins doctor ... --ci` when the Hermes CLI is available;
5. enables the plugin after successful configuration/doctor.

The installer never accepts a token on the command line. Existing installations are not overwritten unless `--force` is supplied; forced replacements are backed up first.

For file-only installation without credentials:

```bash
./install.sh --no-config --no-enable
```

## Verify

```bash
./verify.sh
```

With `GITEA_BASE_URL` and `GITEA_TOKEN` exported, verification also runs the live Gitea doctor. In a Hermes session, ask for a Gitea connection check; Hermes should call `gitea_connection_status`.

## Webhooks

Gitea 1.27 sends GitHub-compatible `X-GitHub-Event`, `X-GitHub-Delivery`, and `X-Hub-Signature-256` headers in addition to its native Gitea headers. Hermes' webhook adapter accepts the GitHub-compatible event/signature path, so a Gitea repository hook can target a Hermes route without a custom signature bridge.

Do not grant terminal/write toolsets to untrusted webhook routes. Hermes' webhook routes default to constrained tools specifically because PR titles, issue bodies, and comments are attacker-controlled input.

Provisioning is intentionally explicit. First create the Hermes route with `hermes webhook subscribe`, then run `scripts/setup_gitea_webhook.py` with the generated secret supplied through `HERMES_GITEA_WEBHOOK_SECRET`. The script does not accept webhook secrets in command-line arguments.

See `docs/WEBHOOKS.md`.

## Source of truth

See `docs/SOURCES.md` and `docs/COMPATIBILITY.md` for the specific Hermes/Gitea contracts used to build this package.
