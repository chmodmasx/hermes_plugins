# hermes_plugins

Monorepo of native plugins, skills and integration support for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

Each integration is self-contained under `integrations/<id>/`. The repository root provides one dispatcher for installation and verification, so adding a new integration does not require changing the top-level workflow.

## Install

Install every integration in this repository:

```bash
./install.sh
```

Install only one integration:

```bash
./install.sh gitea
```

Common options:

```bash
./install.sh --hermes-home ~/.hermes --force
./install.sh gitea --no-config --no-enable
```

List available integrations:

```bash
./install.sh --list
```

Integration-specific options can be passed after `--`:

```bash
./install.sh gitea -- --allow-http
```

Use integration-specific flags only when installing that integration alone.

## Verify

```bash
./verify.sh
```

or:

```bash
./verify.sh gitea
```

## Layout contract

```text
integrations/
└── <id>/
    ├── integration.json   # metadata
    ├── install.sh         # installs this integration
    ├── uninstall.sh       # removes installed components, not secrets
    ├── verify.sh          # offline/native/live checks
    ├── plugin/            # one or more Hermes plugins
    ├── skills/            # normal local Hermes skills when discovery matters
    ├── docs/
    ├── scripts/
    └── tests/
```

A future integration may contain a plugin, a skill, MCP support, or a combination. The repo name therefore describes the primary purpose without encoding every implementation mechanism.

## Current integrations

### `gitea`

Native Gitea 1.27.x integration for Hermes:

- `gitea-hermes`: 33 typed native tools split into `gitea_read` and `gitea_write`.
- `gitea-professional`: policy/knowledge skill with deep Gitea Actions guidance.
- REST API work uses a least-privilege PAT; normal source changes use Git over SSH.
- Baseline: Gitea 1.27.2.

See [`integrations/gitea/README.md`](integrations/gitea/README.md).
