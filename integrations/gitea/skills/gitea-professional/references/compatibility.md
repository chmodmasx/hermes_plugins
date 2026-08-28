# Gitea 1.27 Compatibility Contract

## Target

This skill is optimized for Gitea **1.27.x**. The public research baseline was Gitea API 1.27.2 on 2026-08-27, but the deployed instance is always authoritative.

The server reports its version through `GET /api/v1/version`. The machine-readable API contract is normally available at `/swagger.v1.json`.

## Patch policy

Treat any `1.27.*` server as the intended compatibility family. Do not hard-code a single patch release. Patch releases can fix or adjust endpoint behavior, so unusual or broad operations should still be checked against the live schema.

For a server outside `1.27.x`:

1. Warn that the skill is outside its validated target family.
2. Keep read-only inspection available.
3. Before every write, search the live schema for the exact endpoint/method/payload.
4. Never infer that an endpoint from 1.27 exists unchanged.

## OpenAPI/Swagger handling

The client supports both `openapi` and older `swagger` root-version keys when summarizing a schema. Gitea's current public docs use OpenAPI 3, while older Gitea releases may expose Swagger 2.0-shaped metadata.

Do not send the API token when fetching `/swagger.v1.json`; the bundled client intentionally performs that root request unauthenticated.

## Capability-first rule

For uncommon operations use:

```text
python ${HERMES_SKILL_DIR}/scripts/gitea.py --base-url URL schema --search 'runner' --method POST
```

Use the returned exact method/path/request-body definition from the deployed server. If the endpoint is not present, report that capability as unavailable instead of inventing an alternative.

## Compatibility smoke test

Run:

```text
python ${HERMES_SKILL_DIR}/scripts/doctor.py --base-url URL
```

Expected result for the target environment:

- `compatible_1_27: true`
- schema available;
- API operation count greater than zero;
- authenticated identity present when `GITEA_TOKEN` is configured.
