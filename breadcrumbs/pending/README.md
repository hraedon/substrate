# Pending breadcrumbs

Draft breadcrumbs awaiting numbering and triage. Items here are not yet part of the open backlog — they are insights captured before they are lost, to be promoted into numbered breadcrumbs when reviewed.

When promoting:
1. Assign next number from the main `breadcrumbs/README.md` index.
2. Set `status: proposed` and remove the `origin:` annotation if no longer relevant.
3. Move the file to `breadcrumbs/` and add to the Open table.

Drafts here use the same frontmatter as numbered breadcrumbs, with `number: "pending"` and an `origin:` field naming the source conversation/review.

## Open

| # | Title | Severity | Notes |
|---|---|---|---|
| 100 | HMAC key material held in plaintext Python memory | critical | security |
| 101 | actor_metadata role claim is self-attested without independent verification | critical | security/auth |
| 102 | No rate limiting on any public API endpoint | critical | denial-of-service |
| 103 | Client-supplied event_id not validated as UUIDv4; no entropy guarantees | critical | idempotency |
| 104 | expected_event_seq missing from create_link and remove_link — TOCTOU race | high | concurrency |
| 105 | Replay skip of revoked-key events with continue_on_revoked=True leaves bad events in log | high | security/replay |
| 106 | Unbounded not_before allows permanent work-item DOS | high | denial-of-service |
| 107 | validate_work_item_refs propagates unhandled ValueError from uuid.UUID() | medium | custom-fields |
| 108 | synchronous_commit set per-session, not per-transaction | medium | durability (review: likely false positive) |
| 109 | synchronous_commit configure callback raises silently on connection failure | medium | durability |
| 110 | custom_fields merge in append_transition_event is shallow, not deep | medium | custom-fields |
| 111 | JSON Schema permits additionalProperties:true everywhere — workflow isolation unclear | medium | workflow |
