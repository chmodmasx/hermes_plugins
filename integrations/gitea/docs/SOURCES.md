# Primary sources

Research baseline: 2026-08-28.

## Hermes Agent

- Native plugin guide: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins
- Adding tools: https://hermes-agent.nousresearch.com/docs/developer-guide/adding-tools
- Skills system: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- Webhooks: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/webhooks
- Current plugin installer source: https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/plugins_cmd.py
- Manifest v2 installer/loader mismatch report: https://github.com/NousResearch/hermes-agent/issues/90451

## Gitea 1.27

- API 1.27.2: https://docs.gitea.com/api/
- OAuth2/scopes: https://docs.gitea.com/development/oauth2-provider/
- Repository webhooks: https://docs.gitea.com/usage/repository/webhooks/
- Create repository hook API: https://docs.gitea.com/api/operations/repo-create-hook/
- Gitea Actions documentation: https://docs.gitea.com/usage/actions/overview
- Gitea Runner documentation: https://docs.gitea.com/runner/

Runtime truth is the deployed instance's `/api/v1/version` and `/swagger.v1.json` plus observed behavior of the exact Gitea/Runner versions.

## Gitea 1.27 Actions contract

- API index (1.27.2): https://docs.gitea.com/api/
- Repository workflow runs: https://docs.gitea.com/api/operations/get-workflow-runs/
- Workflow-specific runs: https://docs.gitea.com/api/operations/actions-list-workflow-runs/
- Workflow run jobs: https://docs.gitea.com/api/operations/list-workflow-run-jobs/
- Run artifacts: https://docs.gitea.com/api/operations/get-artifacts-of-run/
- Repository runners: https://docs.gitea.com/api/operations/get-repo-runners/
