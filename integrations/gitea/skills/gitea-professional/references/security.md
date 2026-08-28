# Security and Destructive-Operation Policy

## Secrets

Treat PATs, OAuth tokens, runner registration tokens, webhook secrets, Actions secrets, SSH private keys, deploy-key private material, and package credentials as secrets.

Never:

- place a secret in a URL/query string;
- echo a secret into assistant output;
- embed a PAT in a Git remote URL;
- pass Actions secret values as ordinary visible CLI arguments;
- save secrets in `SKILL.md`, templates, README, repository files, or generated logs.

The REST helper reads `GITEA_TOKEN` from the environment. `actions secret-set` reads the target secret from a named environment variable and redacts that value from HTTP errors.

## Transport

Prefer HTTPS. The helper blocks redirects. This is deliberate: following an unexpected redirect while authenticated can create credential-forwarding risk.

Plain HTTP requires `--allow-http` and should only be used on a network the user explicitly trusts. `--insecure` disables TLS verification and must not be used as an automatic workaround for certificate problems.

## Destructive confirmation

Require explicit user authorization for destructive/high-impact action classes. The helper also requires exact confirmation strings for high-risk built-ins.

Never fabricate or infer a confirmation string merely to make the command execute. Re-read the target immediately before supplying it.

## Privilege

Do not silently switch to an admin token, use sudo/impersonation, weaken branch protection, or broaden repository/team permissions to make an operation succeed.

A 403 is a policy signal. Diagnose the permission layer instead of escalating automatically.

## Git safety

- fetch before push;
- identify remote SHA before an overwrite-capable operation;
- no `git push --force`;
- use `--force-with-lease` only after explicit history-rewrite authorization;
- avoid changing global Git config;
- verify the remote ref after push.

## Webhooks

Validate webhook HMAC against raw request bytes before JSON parsing. Use constant-time comparison and deduplicate delivery IDs. A Hermes skill is not itself a persistent webhook listener; place a validating receiver in front of Hermes.
