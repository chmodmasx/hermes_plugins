# Primary Sources and Research Baseline

Research baseline: 2026-08-27.

## Hermes Agent

- Creating Skills: https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills
- Skills feature: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- Security: https://hermes-agent.nousresearch.com/docs/user-guide/security
- Plugins: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins
- Hooks: https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks
- Cron: https://hermes-agent.nousresearch.com/docs/user-guide/features/cron
- Official skill-authoring skill: https://github.com/NousResearch/hermes-agent/blob/main/skills/software-development/hermes-agent-skill-authoring/SKILL.md

Key implementation facts used here:

- `SKILL.md` is required; `scripts/` and `references/` are supported.
- `metadata.hermes.requires_toolsets` can gate skills on `terminal`.
- `required_environment_variables` is the supported secure setup path for tokens.
- `${HERMES_SKILL_DIR}` is substituted with the absolute skill directory when loaded.
- non-secret skill config lives under `skills.config` and is injected into the skill message.

## Gitea

- API 1.27.2 overview: https://docs.gitea.com/api/
- API usage/pagination/schema: https://docs.gitea.com/development/api-usage/
- FAQ / Swagger location: https://docs.gitea.com/help/faq/
- OAuth2 provider: https://docs.gitea.com/development/oauth2-provider/
- Permissions: https://docs.gitea.com/usage/access-control/permissions/
- Protected branches: https://docs.gitea.com/usage/access-control/protected-branches/
- Webhooks: https://docs.gitea.com/usage/repository/webhooks/
- Actions overview/design/comparison/token permissions: https://docs.gitea.com/usage/actions/
- Runner docs: https://docs.gitea.com/runner/

Selected API pages:

- version: https://docs.gitea.com/api/operations/get-version/
- create branch: https://docs.gitea.com/api/operations/repo-create-branch/
- multi-file contents: https://docs.gitea.com/api/operations/repo-change-files/
- create PR: https://docs.gitea.com/api/operations/repo-create-pull-request/
- create review: https://docs.gitea.com/api/operations/repo-create-pull-review/
- merge PR: https://docs.gitea.com/api/operations/repo-merge-pull-request/
- combined status: https://docs.gitea.com/api/operations/repo-get-combined-status-by-ref/
- workflow dispatch: https://docs.gitea.com/api/operations/actions-dispatch-workflow/
- wiki: https://docs.gitea.com/api/operations/repo-get-wiki-pages/
- packages: https://docs.gitea.com/api/operations/list-packages/

The deployed server's `/swagger.v1.json` remains the final endpoint/payload contract because Gitea installations may run older/newer versions and OpenAPI/Swagger details can change.

## Skill package 1.1.0 specialization

- Target server family: Gitea 1.27.x.
- Hermes current skill-authoring docs confirm `scripts/`, `references/`, and `templates/` as the intended progressive-disclosure layout, with `${HERMES_SKILL_DIR}` for bundled helpers and `required_environment_variables` for secret setup.
- Deep workflow authoring, migration, runner, security, and troubleshooting sources are integrated under `references/actions/`; use `references/actions/sources.md` for that subsystem.
