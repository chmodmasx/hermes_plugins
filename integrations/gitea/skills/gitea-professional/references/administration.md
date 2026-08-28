# Gitea Administration

## Scope

Administration includes instance-wide users, organizations, repositories, runners, hooks, authentication/integration settings, and other `/admin/*` operations exposed by the server.

Admin writes are high impact. Use the live schema for the deployed 1.27 patch and require explicit user authorization for the exact class of change.

## Rules

- Read before write.
- Never use admin privilege as an automatic fallback for a normal 403.
- Never impersonate/sudo without an explicit request.
- Do not disable authentication, branch protection, repository visibility controls, or security policy to make another task easier.
- For bulk operations, produce a target list first and require the user to authorize that list/class before execution.
- After a user/org/repo admin mutation, re-read the exact object and relevant ownership/access state.

## Capability discovery

Use live schema search, for example:

```text
... gitea.py ... schema --search user --method POST --tag admin
... gitea.py ... schema --search runner --tag admin
```

If tag naming differs on the deployed server, search without `--tag` and inspect returned paths.

## Deletion

User, organization, repository, package, runner, and other instance-wide deletions can cascade into inaccessible data or broken automation. Confirm target identity and dependencies before deletion, then verify non-existence or expected replacement state afterward.
