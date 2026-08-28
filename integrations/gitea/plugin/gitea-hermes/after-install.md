# Gitea Hermes integration installed

Configure `GITEA_BASE_URL` and `GITEA_TOKEN` in the Hermes environment, then enable this plugin and run:

```bash
hermes plugins doctor ~/.hermes/plugins/gitea-hermes --ci
```

Use a dedicated Gitea bot account with repository access limited to the repos Hermes should reach. Prefer a scoped PAT and SSH for Git clone/push. This plugin intentionally exposes no delete/admin/secret-write/runner-reset/merge tools.
