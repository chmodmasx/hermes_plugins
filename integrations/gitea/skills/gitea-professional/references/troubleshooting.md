# Troubleshooting Gitea Operations

## 401 / E_AUTH_INVALID

Token missing, invalid, expired, or otherwise rejected. Stop. Do not display the token and do not replace it automatically.

## 403 / E_FORBIDDEN

Possible causes include PAT scope, repository permission, organization/team ACL, disabled repository unit, protected branch, instance policy, or admin-only endpoint. Inspect effective permissions and protection before changing credentials.

## 404 / E_NOT_FOUND

Verify owner, repo, index/name, visibility, and API path. A private resource can appear missing when authentication is insufficient. Do not infer deletion without a prior successful delete plus postcondition check.

## 409 / 412

The server state conflicts with the requested operation or a precondition changed. Re-read the resource and compare expected SHA/version/state.

## 422 / E_VALIDATION

First suspect payload/schema mismatch. Search the live `/swagger.v1.json` for that method/path and compare fields, enum values, and required body shape.

## 429

Honor `Retry-After` when present. Reads can retry with backoff. Mutations require reconciliation before a retry.

## 5xx / transport timeout

Reads may retry. Writes are ambiguous: inspect server state before repeating.

## Redirect refused

Use the canonical external Gitea URL. Do not disable the redirect guard to work around an HTTP→HTTPS or host-name redirect.

## TLS failure

Fix hostname, trust chain, proxy certificate, or CA bundle. Use `--ca-bundle` for a trusted custom CA. Use `--insecure` only after explicit user authorization.

## Actions run stuck/pending

Check runner online state, scope, labels versus `runs-on`, capacity/concurrency, network reachability to Gitea, and whether the workflow event/ref actually matched. For deep workflow diagnosis load `references/actions/troubleshooting.md`.

## Unexpected API absence

The skill targets Gitea 1.27.x but installations can differ by patch/configuration. Run `doctor.py`, then `schema --search` for the capability. If the endpoint is absent from the live schema, do not invent it.
