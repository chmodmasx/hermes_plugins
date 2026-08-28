# Organizations, Teams, Users, Administration, and Security

## Organizations and teams

Prefer team-based access in organizations. Typical API families cover:

- org CRUD/rename/avatar;
- org members/public membership/blocking;
- org repositories;
- teams CRUD/search;
- team members;
- team repositories;
- org Actions runners/runs/secrets/variables;
- org webhooks and labels.

Before permission changes, read:

1. current organization visibility/settings;
2. team permission level and units;
3. team membership;
4. repo-to-team assignment;
5. effective user permission when endpoint exists.

Do not silently grant `admin`/`owner` because `write` failed.

## Repository collaborators

Individual collaborators can have read/write/admin-style permissions. In org-owned repos, teams are usually preferable. Every permission mutation requires explicit user intent because it changes access control.

Postcondition: read effective permission after change.

## Users and authentication

User APIs include profile/search and authenticated-user resources. Admin APIs can create/edit/delete users and manage public keys or other account state.

External authentication such as LDAP does not eliminate the need to manage Gitea-side access artifacts during offboarding. SSH keys or tokens may continue to authorize access until removed/revoked according to server policy.

Never store a person's LDAP password in this skill.

## Admin API

Administrative endpoints can control users, orgs, global runners, cron jobs, system hooks, and repository adoption/migration state. Any mutating `/admin/*` operation is high risk.

Rules:

- require explicit user request for the exact administrative action;
- read target first;
- use the live schema;
- do not combine unrelated admin changes into one broad request;
- verify after change;
- do not retry ambiguous admin mutations blindly.

Generic helper admin mutations require both `--write-ok` and the exact confirmation:

`WRITE:METHOD:/admin/exact/path`

## Sudo / impersonation

Gitea APIs can allow administrators to sudo/impersonate another user. Treat this as a separate privileged action. Never add `sudo` query/header merely to make a forbidden request work. Use only when the user explicitly requests acting as another identity and the reason is legitimate.

## Visibility and destructive changes

Explicit authorization is required before:

- making a repo/org private/public/limited;
- transferring ownership;
- deleting repo/org/user/team;
- deleting all repositories in an org;
- changing branch protection or merge policy to weaken controls;
- manipulating deploy keys/authentication sources;
- rotating/revoking another user's tokens/keys unless the user asked for that admin operation.

## Least privilege

Recommended bot pattern:

- dedicated account, not a human account;
- only necessary PAT scope families;
- only necessary org/team/repo access;
- no global admin unless an actual admin workflow requires it;
- separate tokens/profiles for materially different trust zones if possible.

Never respond to 403 by automatically seeking a token with more privileges.

## Logging and secret redaction

Operational logs may include action, repo, issue/PR ID, commit SHA, HTTP status, duration, and result. They must never include:

- Authorization headers;
- PAT/OAuth tokens;
- SSH private keys;
- runner registration tokens;
- Actions/webhook secrets;
- sensitive request bodies containing those values.

## Source links

- https://docs.gitea.com/usage/access-control/permissions/
- https://docs.gitea.com/administration/authentication/
- https://docs.gitea.com/development/api-usage/
- https://docs.gitea.com/api/
