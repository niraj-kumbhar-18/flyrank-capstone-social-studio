# Evidence

Real output from manual testing via Swagger and direct database inspection.
Every response below was actually produced by the running application, not
reconstructed from memory.

## Constraint enforcement (length, hashtags)

Created a `mock_x` variant with content over the 280-character limit.

Request: `POST /posts/1/variants`
```json
{
  "platform": "mock_x",
  "content": "<content over 280 characters>"
}
```

Response: `400 Bad Request`
```json
{
  "detail": [
    "Content exceeds the 280 character limit"
  ]
}
```

The error names the specific broken rule rather than returning a generic
validation failure.

## Review workflow (draft → approved/rejected → published)

Attempted to schedule a variant still in `draft` status, before approval.

Request: `POST /variants/{id}/schedule`

Response: `400 Bad Request`
```json
{
  "detail": "Only approved variants can be scheduled"
}
```

The same variant was then approved and scheduled successfully, returning
`201`. This confirms an unapproved schedule attempt is blocked with a 4xx
status and a message naming the reason.

## Adapter layer / adapter swap

Created two fresh variants targeting different platforms, approved and
scheduled both in the past, then ran the worker.

Variant 19 (`mock_x`) — `PublishAttempt id: 19`
```json
{
  "id": 19,
  "schedule_slot_id": 18,
  "variant_id": 19,
  "platform": "mock_x",
  "attempted_at": "2026-09-14T08:32:40.915580",
  "success": true,
  "detail": "Mock X post published",
  "external_post_id": "mock-x-19"
}
```

Variant 20 (`telegram`) — `PublishAttempt id: 20`
```json
{
  "id": 20,
  "schedule_slot_id": 19,
  "variant_id": 20,
  "platform": "telegram",
  "attempted_at": "2026-09-14T08:32:42.452340",
  "success": true,
  "detail": "Telegram post published",
  "external_post_id": "10"
}
```

Both attempts went through the identical `worker.py` code path
(`process_due_slots` → `get_publisher(variant.platform)` →
`publisher.publish(variant, idempotency_key)`). The only difference between
a mock publish and a real Telegram publish is the `platform` value on the
`Variant` row — swapping target platform is a data change, not a code
change. The Telegram message was also confirmed to have actually arrived
in the target Telegram channel.

## Idempotent publish

**Primary evidence — mid-batch interruption (variants 16, 17, 18):**

Three `mock_x` variants were approved and scheduled in the past
(slot 14 → variant 16, slot 15 → variant 17, slot 16 → variant 18).

The worker was started and processed slot 14 to completion (committed),
then was manually interrupted with `Ctrl+C` before starting slot 15.

`/publish-history` immediately after the interruption:
- Variant 16 → 1 successful attempt (`id: 16`)
- Variant 17 → 0 attempts
- Variant 18 → 0 attempts

The worker was restarted. It checked slot 14, found an existing successful
`PublishAttempt` for `idempotency_key = variant-16-schedule`, and skipped
it without republishing. It then processed slots 15 and 16 normally.

`/publish-history` after restart:
- Variant 16 → 1 successful attempt (`id: 16`) — unchanged, no duplicate
- Variant 17 → 1 successful attempt (`id: 17`)
- Variant 18 → 1 successful attempt (`id: 18`)

No duplicate attempt was created for the slot that had already completed
before the interruption.

**Secondary confirmation — re-running after a completed run (variants 19, 20):**

After variants 19 and 20 were already published successfully (see Adapter
layer section above), the worker was run again with no new due slots
requiring action for them. `/publish-history` still showed exactly one
successful attempt for each — `id: 19` and `id: 20` — confirming the
worker does not create a second attempt for a variant whose idempotency
key already has a recorded success.

## Durable scheduling (worker restart mid-batch)

Same test as the primary idempotency evidence above: the worker was
interrupted between processing slot 14 and slot 15 — i.e. after one
slot's `PublishAttempt` was committed and before the next slot's publish
call began. On restart, the completed slot was correctly skipped and the
remaining two slots were processed with zero duplicates.

This confirms interruption **between worker iterations**. `db.commit()`
runs inside the per-slot loop in `worker.py`, immediately after each
`PublishAttempt` is recorded — so a kill at any point between iterations
can never lose or duplicate a slot's result. This test does not cover
interruption in the middle of a single HTTP call to a publisher (e.g. the
Telegram API request itself); that is a narrower network-partial-failure
case outside what "mid-batch" describes in the brief.

## Publish history

`GET /publish-history` returns every attempt — success and failure —
newest first, with attempt id, schedule slot id, variant id, platform,
timestamp, success flag, detail, and external post id.

Failures are recorded, not just successes. An early real example from
before the worker's `.env` loading was fixed:
```json
{
  "success": false,
  "detail": "Telegram credentials are not configured",
  "external_post_id": null
}
```

This attempt remains in history as a genuine record of a failed publish,
confirming the endpoint reflects real outcomes rather than only
successful ones.

## Secrets clean

```bash
$ git check-ignore .env
.env

$ git log --all -- .env
(no output)
```

`.env` is ignored by Git and has never been committed to history.
`.env.example` contains placeholder values only:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_channel_or_chat_id_here
GEMINI_API_KEY=your_gemini_api_key_here
```