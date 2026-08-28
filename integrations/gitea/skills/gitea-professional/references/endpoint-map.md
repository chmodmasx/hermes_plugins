# High-Value Gitea Endpoint Map

This is a navigation map, not a replacement for the deployed instance's `/swagger.v1.json`. For any uncertain payload or missing operation, run `schema --search` and follow the live contract.

| Domain | Task | Method / path or interface | Typical scope family | Risk / verification |
|---|---|---|---|---|
| Instance | version | `GET /version` | misc/read | Read-only |
| Identity | current user | `GET /user` | user/read | Read-only |
| Repos | get repo | `GET /repos/{o}/{r}` | repository/read | Read-only |
| Repos | create user repo | `POST /user/repos` | user/write | Reconcile by owner/name |
| Repos | create org repo | `POST /orgs/{org}/repos` | organization/write | Reconcile by org/name |
| Repos | edit repo | `PATCH /repos/{o}/{r}` | repository/write | Verify changed fields |
| Repos | delete repo | `DELETE /repos/{o}/{r}` | repository/write | Destructive; confirm; verify 404 |
| Repos | fork | `POST /repos/{o}/{r}/forks` | repository/write | Reconcile destination |
| Git | clone/fetch/push | `git` SSH/HTTPS | Git ACL | Verify remote SHA |
| Branch | list | `GET /repos/{o}/{r}/branches` | repository/read | Paginate |
| Branch | create | `POST /repos/{o}/{r}/branches` | repository/write | Verify branch SHA |
| Branch | delete | `DELETE /repos/{o}/{r}/branches/{branch}` | repository/write | Destructive; confirm |
| Tag | list/create/delete | `/repos/{o}/{r}/tags...` | repository | Tag rewrite is sensitive |
| Refs | list refs | `GET /repos/{o}/{r}/git/refs` | repository/read | Use exact SHA |
| Contents | multi-file change | `POST /repos/{o}/{r}/contents` | repository/write | No force push by default |
| Issues | list/create | `GET/POST /repos/{o}/{r}/issues` | issue | Paginate; verify created issue |
| Issues | get/edit/delete | `/repos/{o}/{r}/issues/{i}` | issue | Delete is destructive |
| Comments | list/create | `/repos/{o}/{r}/issues/{i}/comments` | issue | Verify comment ID/body |
| Labels | repo labels | `/repos/{o}/{r}/labels...` | issue | Resolve names to IDs |
| Milestones | repo milestones | `/repos/{o}/{r}/milestones...` | issue | Avoid duplicate titles |
| PR | list/create | `GET/POST /repos/{o}/{r}/pulls` | repository | Capture head/base SHA |
| PR | get | `GET /repos/{o}/{r}/pulls/{i}` | repository/read | Read before review/merge |
| PR | review | `POST /repos/{o}/{r}/pulls/{i}/reviews` | repository/write | Bind review to commit ID |
| PR | commits/files | `/pulls/{i}/commits`, `/pulls/{i}/files` | repository/read | Paginate |
| PR | merge | `POST /repos/{o}/{r}/pulls/{i}/merge` | repository/write | Confirm; `head_commit_id`; no force |
| CI | combined status | `GET /repos/{o}/{r}/commits/{sha}/status` | repository/read | Exact SHA |
| Actions | runs | `GET /repos/{o}/{r}/actions/runs` | repository/Actions read | Inspect run/job state |
| Actions | jobs | `GET /repos/{o}/{r}/actions/runs/{run}/jobs` | repository/Actions read | Diagnose failures |
| Actions | rerun | `POST /repos/{o}/{r}/actions/runs/{run}/rerun` | write | Side effects; confirm |
| Actions | dispatch | `POST /repos/{o}/{r}/actions/workflows/{id}/dispatches` | write | Validate ref/inputs; no duplicate dispatch |
| Actions | secrets | `GET/PUT/DELETE /repos/{o}/{r}/actions/secrets...` | write | Use secret wrappers; env source; exact confirmation |
| Actions | variables | `/repos/{o}/{r}/actions/variables...` | write | Inspect sensitivity |
| Runners | repo/org/global | discover `actions runners` in schema | varies/admin | Registration token is secret |
| Releases | list/create | `GET/POST /repos/{o}/{r}/releases` | repository | Verify tag/target |
| Releases | delete | `DELETE /repos/{o}/{r}/releases/{id}` | repository | Destructive |
| Wiki | list | `GET /repos/{o}/{r}/wiki/pages` | repository | Paginate |
| Wiki | get | `GET /repos/{o}/{r}/wiki/page/{name}` | repository | Base64 content |
| Wiki | create | `POST /repos/{o}/{r}/wiki/new` | repository/write | Verify page |
| Wiki | edit/delete | `PATCH/DELETE /repos/{o}/{r}/wiki/page/{name}` | repository/write | Delete destructive |
| Packages | list owner | `GET /packages/{owner}` | package/read | Paginate/filter type |
| Packages | versions | `GET /packages/{owner}/{type}/{name}` | package/read | Paginate |
| Packages | latest | `GET /packages/{owner}/{type}/{name}/-/latest` | package/read | Read-only |
| Packages | delete/link | discover package schema | package/write | Destructive/dependency impact |
| Orgs | org CRUD | `/orgs...` | organization | Delete/visibility sensitive |
| Teams | teams/members/repos | `/orgs/{org}/teams...`, `/teams/{id}...` | organization | Permission changes sensitive |
| Hooks | repo/org hooks | discover `hook` schema | repo/org | Secret + delivery impact |
| Admin | users/runners/hooks/cron | `/admin/...` | admin | Explicit exact admin authorization |
| Notifications | threads/subscriptions | discover notification schema | notification | User-scoped state |

## Generic API method

For a version-specific operation:

1. `schema --search 'concept' --method METHOD`.
2. Inspect path and request parameters/body.
3. Read current target state.
4. Run generic read with `get` or a mutation with `request METHOD PATH --write-ok ...`.
5. DELETE/admin/merge-like generic paths also require exact `--confirm 'WRITE:METHOD:/path'`.
6. Re-read the postcondition.

Generic writes are an escape hatch. Prefer a built-in wrapper when one exists because wrappers encode stronger safety and postcondition checks.
