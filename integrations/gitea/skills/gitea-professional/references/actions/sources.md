# Primary Sources

Use exact-version documentation where available. These links are intentionally primary-source heavy.

## Hermes Agent Skill System

- Skills System:
  https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md
- Creating Skills:
  https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/creating-skills.md
- Hermes Agent Skill Authoring:
  https://github.com/NousResearch/hermes-agent/blob/main/skills/software-development/hermes-agent-skill-authoring/SKILL.md
- Skill implementation:
  https://github.com/NousResearch/hermes-agent/blob/main/tools/skills_tool.py

## Gitea Actions

- Overview:
  https://docs.gitea.com/usage/actions/overview/
- Quick Start:
  https://docs.gitea.com/usage/actions/quickstart/
- Compared to GitHub Actions:
  https://docs.gitea.com/usage/actions/comparison/
- Actions variables/contexts:
  https://docs.gitea.com/usage/actions/actions-variables/
- Token permissions:
  https://docs.gitea.com/usage/actions/token-permissions/
- Secrets:
  https://docs.gitea.com/usage/actions/secrets/
- FAQ/events:
  https://docs.gitea.com/usage/actions/faq/
- Design:
  https://docs.gitea.com/usage/actions/design/
- Scoped workflows:
  https://docs.gitea.com/usage/actions/scoped-workflows/
- Administration configuration:
  https://docs.gitea.com/administration/config-cheat-sheet/

## Gitea Runner

- Runner documentation:
  https://docs.gitea.com/runner/
- Registration:
  https://docs.gitea.com/runner/registration/
- Configuration:
  https://docs.gitea.com/runner/configuration
- Cache:
  https://docs.gitea.com/runner/cache/
- Monitoring:
  https://docs.gitea.com/runner/monitoring
- Kubernetes:
  https://docs.gitea.com/runner/installation/kubernetes

## Packages / OCI

- Container Registry:
  https://docs.gitea.com/usage/packages/container/
- Package Registry overview:
  https://docs.gitea.com/usage/packages/overview/
- Helm:
  https://docs.gitea.com/usage/packages/helm/

## Release Notes

- Gitea release blog:
  https://blog.gitea.com/
- Gitea Runner releases:
  https://gitea.com/gitea/runner/releases

## Compatibility Reference Only

Use GitHub documentation to understand the upstream dialect, not to prove Gitea support:

- GitHub Actions workflow syntax:
  https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- Secure use:
  https://docs.github.com/en/actions/reference/security/secure-use
- Limits:
  https://docs.github.com/en/actions/reference/limits

## Evidence Rule

If official docs, source code, and runtime behavior conflict:

1. capture exact versions;
2. produce a minimal reproducer;
3. trust observed target-version behavior for immediate operations;
4. document the discrepancy;
5. check upstream issues/release notes before generalizing.
