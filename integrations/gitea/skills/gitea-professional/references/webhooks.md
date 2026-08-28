# Gitea Webhooks and Event-Driven Integration

## Scope

Gitea can expose webhooks at repository, organization, user, and system/admin scopes depending on version/configuration. Webhooks are for outbound event delivery from Gitea; a Hermes skill by itself is not a persistent HTTP listener.

For a permanent receiver, use a dedicated HTTPS service/plugin/sidecar that validates Gitea and then invokes Hermes. Use the skill for creating/inspecting/testing webhook configuration and for processing already-validated event context.

## Security headers

Current Gitea webhook delivery can include headers such as:

- `X-Gitea-Delivery` — delivery identifier;
- `X-Gitea-Event` / event-type header — event category;
- `X-Gitea-Signature` — HMAC-SHA256 signature of the raw request body when a secret is configured.

Verification order:

1. preserve raw body bytes;
2. compute HMAC-SHA256 with configured secret;
3. compare using constant-time comparison;
4. reject invalid signature;
5. deduplicate by delivery ID;
6. only then parse JSON and dispatch policy.

Never compute the HMAC over re-serialized JSON; byte-for-byte raw payload matters.

## Delivery reliability

Webhook handlers must tolerate duplicate deliveries/redelivery. Store processed delivery IDs for an appropriate retention window. Event processing should be idempotent where possible.

Return an HTTP success promptly after durable acceptance; perform long work asynchronously in the receiver's own execution architecture. A Hermes skill invocation can then handle the normalized event payload.

## Event categories

Events can include repository push/create/delete, issue and comment activity, pull requests/reviews, releases, and Actions/workflow events depending on version. Do not hard-code a complete event list from memory; inspect the instance/docs when configuring a hook.

Branch filters apply to ref-oriented events according to Gitea behavior; do not assume they filter every issue/release event.

## Creating/updating hooks

Before creating a hook:

- validate destination HTTPS URL and ownership;
- choose only needed events;
- create a high-entropy secret outside model-visible text;
- do not leak Authorization headers or webhook secrets;
- prefer a target that rejects unsigned/invalid requests;
- test delivery and inspect response status.

Hook deletion or secret replacement requires explicit authorization because it can disable integrations.

Use `schema --search 'hook'` or `schema --search 'webhook'` with the appropriate tag/method to discover repository/org/admin endpoint payloads for the deployed version.

## Hermes architecture

Recommended event-driven path:

Gitea webhook -> HTTPS receiver -> HMAC verify -> delivery dedupe -> allowlist/policy -> Hermes task/session -> `gitea-professional` helper for follow-up reads/writes.

Do not expose an unrestricted Hermes conversation endpoint directly to raw webhook payloads.

## Source links

- https://docs.gitea.com/usage/repository/webhooks/
- https://docs.gitea.com/api/
- https://hermes-agent.nousresearch.com/docs/developer-guide/plugins
- https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks
